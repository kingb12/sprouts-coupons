import json
import logging
import urllib.parse

import requests

from .models import Offer, SessionInfo

logger = logging.getLogger(__name__)

GRAPHQL_ENDPOINT = "https://shop.sprouts.com/graphql"
OFFERS_QUERY_HASH = "f26ac1f27a58e191306d8fa6e15d4edd0492a625f0a8bd254310454a82596a8e"


class SproutsClient:
    """Client for interacting with Sprouts GraphQL API."""

    def __init__(self, session: SessionInfo):
        self.session = session
        self._requests = requests.Session()
        self._requests.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
                "Content-Type": "application/json",
                "Accept": "*/*",
                "x-client-identifier": "web",
            }
        )
        # Set cookies from session
        for name, value in session.cookies.items():
            self._requests.cookies.set(name, value)

    def get_offers(self, limit: int = 500) -> list[Offer]:
        """Fetch all available coupon offers."""
        variables = {
            "shopId": self.session.shop_id,
            "offerSources": ["ic_inmar"],
            "limit": limit,
            "filtering": [],
            "sorting": {"key": "BEST_MATCH"},
        }
        extensions = {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": OFFERS_QUERY_HASH,
            }
        }

        params = {
            "operationName": "FindOffersForUserV2",
            "variables": json.dumps(variables),
            "extensions": json.dumps(extensions),
        }

        url = f"{GRAPHQL_ENDPOINT}?{urllib.parse.urlencode(params)}"
        logger.debug(f"Fetching offers from: {url}")

        response = self._requests.get(url)
        response.raise_for_status()

        data = response.json()
        return self._parse_offers(data)

    def _parse_offers(self, data: dict) -> list[Offer]:
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

    def _parse_single_offer(self, raw: dict) -> Offer | None:
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

    def clip_coupon(self, offer: Offer) -> bool:
        """
        Clip a coupon offer.

        This is a stub - actual implementation TBD.
        """
        logger.info(f"[STUB] Clipping coupon: {offer.name}")
        # TODO: Implement actual clipping via GraphQL mutation
        # The mutation likely requires:
        # - offerRequestKey
        # - shopId
        # - session cookies
        return True
