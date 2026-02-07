import json
import logging
import urllib.parse
import uuid
from typing import Any

import requests

from .models import Offer, SessionInfo

logger = logging.getLogger(__name__)

GRAPHQL_ENDPOINT = "https://shop.sprouts.com/graphql"

# Persisted query hashes - obtained from browser network inspection
OFFERS_QUERY_HASH = "f26ac1f27a58e191306d8fa6e15d4edd0492a625f0a8bd254310454a82596a8e"
GET_AVAILABLE_OFFER_HASH = "b839689921f13df9ad4424b4cff9820fcbf25dcc5a2f1a73bb0ce5ebf3442720"
CLIP_COUPON_HASH = "e8f419c92ab3413a7cfd9d219ad6217255479a69451177a5a8b2d0d40fe448f2"


class SproutsClient:
    """Client for interacting with Sprouts GraphQL API."""

    def __init__(self, session: SessionInfo, zone_id: str = "981", postal_code: str = "95126"):
        """
        Initialize the Sprouts client.

        Args:
            session: Authenticated session info with cookies
            zone_id: Zone ID for the store (default from example)
            postal_code: Postal code for the store (default from example)
        """
        self.session = session
        self.zone_id = zone_id
        self.postal_code = postal_code
        self._requests = requests.Session()
        # Headers required by Sprouts API - x-client-identifier is checked server-side
        self._requests.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"
                ),
                "Content-Type": "application/json",
                "Accept": "*/*",
                "x-client-identifier": "web",
            }
        )
        # Set cookies from session
        for name, value in session.cookies.items():
            self._requests.cookies.set(name, value)

    def _graphql_get(self, operation_name: str, variables: dict[str, Any], query_hash: str) -> dict[str, Any]:
        """Make a GraphQL GET request with persisted query."""
        extensions = {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": query_hash,
            }
        }

        params = {
            "operationName": operation_name,
            "variables": json.dumps(variables),
            "extensions": json.dumps(extensions),
        }

        url = f"{GRAPHQL_ENDPOINT}?{urllib.parse.urlencode(params)}"
        logger.debug(f"GraphQL request: {operation_name} -> {url[:100]}...")

        response = self._requests.get(url)
        response.raise_for_status()

        data: dict[str, Any] = response.json()

        # Check for GraphQL errors
        if "errors" in data:
            errors = data["errors"]
            logger.error(f"GraphQL errors: {errors}")
            raise RuntimeError(f"GraphQL error: {errors[0].get('message', 'Unknown error')}")

        return data

    def get_offers(self, limit: int = 500) -> list[Offer]:
        """Fetch all available coupon offers."""
        variables = {
            "shopId": self.session.shop_id,
            # ic_inmar = Inmar digital coupons - Inmar is the coupon/rebate provider for Sprouts
            "offerSources": ["ic_inmar"],
            "limit": limit,
            "filtering": [],
            "sorting": {"key": "BEST_MATCH"},
        }

        data = self._graphql_get("FindOffersForUserV2", variables, OFFERS_QUERY_HASH)
        return self._parse_offers(data)

    def _parse_offers(self, data: dict[str, Any]) -> list[Offer]:
        """Parse offers from GraphQL response."""
        offers = []
        try:
            raw_offers = data.get("data", {}).get("userOffersV2", {}).get("offers", [])
            for raw in raw_offers:
                offer = self._parse_single_offer(raw)
                if offer:
                    offers.append(offer)
        except Exception as e:
            logger.error(f"Error parsing offers: {e}")
            raise
        return offers

    def _parse_single_offer(self, raw: dict[str, Any]) -> Offer | None:
        """Parse a single offer from raw data."""
        try:
            view = raw.get("viewSection", {})

            # Extract description from details
            description = ""
            details = view.get("detailsFormattedAttributesString", {})
            sections = details.get("sections", [])
            if sections:
                description = sections[0].get("text", "").strip()

            # Extract expiration
            expires_on = view.get("endsOnString", "")

            # Extract image URL
            image = view.get("offerImage", {})
            image_url = image.get("url") if image else None

            return Offer(
                id=raw.get("id", ""),
                offer_id=raw.get("offerId", ""),
                coupon_id=raw.get("couponId", ""),
                offer_request_key=raw.get("offerRequestKey", ""),
                name=view.get("nameString", ""),
                description=description,
                expires_on=expires_on,
                is_clipped=view.get("clippedVariant") == "true",
                image_url=image_url,
            )
        except Exception as e:
            logger.warning(f"Failed to parse offer: {e}")
            return None

    def _get_available_offer(self, offer: Offer) -> dict[str, Any] | None:
        """
        Fetch detailed offer info including itemId needed for clipping.

        Returns the raw offer data from the API, or None if not found.
        """
        variables = {
            "shopId": self.session.shop_id,
            "zoneId": self.zone_id,
            "postalCode": self.postal_code,
            "legacyOfferId": offer.offer_id,
        }

        try:
            data = self._graphql_get("GetAvailableOffer", variables, GET_AVAILABLE_OFFER_HASH)
            offer_data: dict[str, Any] | None = data.get("data", {}).get("getAvailableOffer")
            if not offer_data:
                logger.warning(f"No getAvailableOffer data returned for {offer.name}")
                return None
            return offer_data
        except Exception as e:
            logger.error(f"Failed to get available offer for {offer.name}: {e}")
            return None

    def clip_coupon(self, offer: Offer) -> bool:
        """
        Clip a coupon offer.

        This makes two API calls:
        1. GetAvailableOffer - to get the itemId
        2. ClipCoupon - to actually clip the coupon

        Returns True if successful, False otherwise.
        """
        if offer.is_clipped:
            logger.info(f"Coupon already clipped: {offer.name}")
            return True

        # Step 1: Get the itemId from GetAvailableOffer
        logger.info(f"Getting offer details for: {offer.name}")
        offer_data = self._get_available_offer(offer)

        if not offer_data:
            logger.error(f"Could not get offer details for {offer.name}")
            return False

        # Extract itemId from items array - use legacyId which is the numeric ID
        items = offer_data.get("items", [])
        if not items:
            # Some offers (e.g., manufacturer coupons) don't have specific items
            # Use default itemId "000000000001" as fallback
            logger.warning(f"No items in offer data for {offer.name}, using default itemId")
            logger.debug(f"Offer data keys: {offer_data.keys()}")
            item_id = "000000000001"
        else:
            # The legacyId is the numeric item ID used for clipping
            item_id = items[0].get("legacyId")
            if not item_id:
                logger.error(f"Could not find legacyId in items for {offer.name}")
                logger.debug(f"First item keys: {items[0].keys()}")
                return False

        # Step 2: Clip the coupon
        logger.info(f"Clipping coupon: {offer.name} (itemId={item_id})")

        # Construct offerReference: {offerRequestKey}/{offerId}
        offer_reference = f"{offer.offer_request_key}/{offer.offer_id}"

        # Generate a page view ID (UUID format like the browser uses)
        page_view_id = str(uuid.uuid4())

        variables = {
            "itemId": str(item_id),
            "shopId": self.session.shop_id,
            "fetchRelatedItems": True,
            "trackingParams": {
                "pageType": None,
                "pageValue": None,
                "pageViewId": page_view_id,
                "pageViewIdV2": page_view_id,
                "sourceType": "shop_content_page",
                "sourceValue": "loyalty_offer_items",
                "rowPosition": None,
                "candidateId": None,
                "eligibleId": None,
            },
            "offerReference": offer_reference,
        }

        try:
            data = self._graphql_get("ClipCoupon", variables, CLIP_COUPON_HASH)
            # Check if clip was successful - response is under clipCouponV2
            clip_result = data.get("data", {}).get("clipCouponV2")
            if clip_result:
                logger.info(f"Successfully clipped: {offer.name}")
                return True
            else:
                logger.warning(f"Clip response did not confirm success for {offer.name}")
                logger.debug(f"Clip response: {data}")
                return False
        except Exception as e:
            logger.error(f"Failed to clip coupon {offer.name}: {e}")
            return False
