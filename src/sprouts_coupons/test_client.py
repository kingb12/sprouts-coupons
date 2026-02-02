"""
Unit tests for Sprouts client module.

These tests use mocking and don't require internet connectivity.
Run with: pytest -m unit_build
"""

from unittest.mock import Mock, patch

import pytest
import requests

from sprouts_coupons.client import SproutsClient
from sprouts_coupons.models import Offer, SessionInfo


@pytest.fixture
def mock_session() -> SessionInfo:
    """Create a mock session for testing."""
    return SessionInfo(
        cookies={"session_token": "fake_token", "user_id": "123"},
        shop_id="test_shop_123",
    )


@pytest.fixture
def client(mock_session: SessionInfo) -> SproutsClient:
    """Create a client instance with mock session."""
    return SproutsClient(
        session=mock_session,
        zone_id="981",
        postal_code="95126",
    )


@pytest.fixture
def sample_offer() -> Offer:
    """Create a sample offer for testing."""
    return Offer(
        id="offer_123",
        offer_id="off_456",
        coupon_id="cpn_789",
        offer_request_key="req_key_abc",
        name="Save $1 on Bananas",
        description="Get $1 off organic bananas",
        expires_on="2026-02-15",
        is_clipped=False,
        image_url="https://example.com/banana.jpg",
    )


@pytest.mark.unit_build
class TestSproutsClientInit:
    """Test client initialization."""

    def test_client_initializes_with_session(self, mock_session: SessionInfo) -> None:
        """Client should initialize with session info."""
        client = SproutsClient(mock_session)
        assert client.session == mock_session
        assert client.zone_id == "981"
        assert client.postal_code == "95126"

    def test_client_sets_custom_zone_and_postal(self, mock_session: SessionInfo) -> None:
        """Client should accept custom zone_id and postal_code."""
        client = SproutsClient(mock_session, zone_id="123", postal_code="12345")
        assert client.zone_id == "123"
        assert client.postal_code == "12345"

    def test_client_sets_required_headers(self, mock_session: SessionInfo) -> None:
        """Client should set required HTTP headers."""
        client = SproutsClient(mock_session)
        headers = client._requests.headers
        assert "x-client-identifier" in headers
        assert headers["x-client-identifier"] == "web"
        assert headers["Content-Type"] == "application/json"

    def test_client_sets_cookies_from_session(self, mock_session: SessionInfo) -> None:
        """Client should set cookies from session."""
        client = SproutsClient(mock_session)
        cookies = client._requests.cookies
        assert cookies.get("session_token") == "fake_token"
        assert cookies.get("user_id") == "123"


@pytest.mark.unit_build
class TestGraphQLGet:
    """Test GraphQL GET request method."""

    def test_graphql_get_constructs_correct_url(self, client: SproutsClient) -> None:
        """_graphql_get should construct proper URL with query parameters."""
        mock_response = Mock()
        mock_response.json.return_value = {"data": {"result": "success"}}
        mock_response.raise_for_status = Mock()

        with patch.object(client._requests, "get", return_value=mock_response) as mock_get:
            variables = {"shopId": "123", "limit": 10}
            client._graphql_get("TestQuery", variables, "fake_hash_abc123")

            # Verify get was called
            assert mock_get.called
            call_url = mock_get.call_args[0][0]

            # Verify URL components
            assert "operationName=TestQuery" in call_url
            assert "fake_hash_abc123" in call_url
            assert call_url.startswith("https://shop.sprouts.com/graphql?")

    def test_graphql_get_raises_on_http_error(self, client: SproutsClient) -> None:
        """_graphql_get should raise on HTTP errors."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")

        with patch.object(client._requests, "get", return_value=mock_response):
            with pytest.raises(requests.HTTPError):
                client._graphql_get("TestQuery", {}, "hash")

    def test_graphql_get_raises_on_graphql_errors(self, client: SproutsClient) -> None:
        """_graphql_get should raise on GraphQL errors."""
        mock_response = Mock()
        mock_response.json.return_value = {"errors": [{"message": "Invalid query"}]}
        mock_response.raise_for_status = Mock()

        with patch.object(client._requests, "get", return_value=mock_response):
            with pytest.raises(RuntimeError, match="Invalid query"):
                client._graphql_get("TestQuery", {}, "hash")

    def test_graphql_get_returns_data_on_success(self, client: SproutsClient) -> None:
        """_graphql_get should return data on successful request."""
        expected_data = {"data": {"offers": [{"id": "1"}]}}
        mock_response = Mock()
        mock_response.json.return_value = expected_data
        mock_response.raise_for_status = Mock()

        with patch.object(client._requests, "get", return_value=mock_response):
            result = client._graphql_get("TestQuery", {}, "hash")
            assert result == expected_data


@pytest.mark.unit_build
class TestParseSingleOffer:
    """Test offer parsing logic."""

    def test_parse_single_offer_with_complete_data(self, client: SproutsClient) -> None:
        """Should parse offer with all fields present."""
        raw_offer = {
            "id": "123",
            "offerId": "off_456",
            "couponId": "cpn_789",
            "offerRequestKey": "req_key",
            "viewSection": {
                "nameString": "Save on Apples",
                "detailsFormattedAttributesString": {"sections": [{"text": "Get $2 off apples"}]},
                "endsOnString": "2026-03-01",
                "clippedVariant": "false",
                "offerImage": {"url": "https://example.com/apple.jpg"},
            },
        }

        offer = client._parse_single_offer(raw_offer)

        assert offer is not None
        assert offer.id == "123"
        assert offer.offer_id == "off_456"
        assert offer.name == "Save on Apples"
        assert offer.description == "Get $2 off apples"
        assert offer.expires_on == "2026-03-01"
        assert offer.is_clipped is False
        assert offer.image_url == "https://example.com/apple.jpg"

    def test_parse_single_offer_with_clipped_status(self, client: SproutsClient) -> None:
        """Should correctly parse clipped status."""
        raw_offer = {
            "id": "123",
            "offerId": "off_456",
            "couponId": "cpn_789",
            "offerRequestKey": "req_key",
            "viewSection": {
                "nameString": "Clipped Offer",
                "clippedVariant": "true",
                "endsOnString": "2026-03-01",
                "detailsFormattedAttributesString": {"sections": [{"text": "desc"}]},
            },
        }

        offer = client._parse_single_offer(raw_offer)

        assert offer is not None
        assert offer.is_clipped is True

    def test_parse_single_offer_with_missing_image(self, client: SproutsClient) -> None:
        """Should handle missing image gracefully."""
        raw_offer = {
            "id": "123",
            "offerId": "off_456",
            "couponId": "cpn_789",
            "offerRequestKey": "req_key",
            "viewSection": {
                "nameString": "No Image Offer",
                "endsOnString": "2026-03-01",
                "clippedVariant": "false",
                "detailsFormattedAttributesString": {"sections": [{"text": "desc"}]},
            },
        }

        offer = client._parse_single_offer(raw_offer)

        assert offer is not None
        assert offer.image_url is None

    def test_parse_single_offer_with_empty_description(self, client: SproutsClient) -> None:
        """Should handle missing description sections."""
        raw_offer = {
            "id": "123",
            "offerId": "off_456",
            "couponId": "cpn_789",
            "offerRequestKey": "req_key",
            "viewSection": {
                "nameString": "No Description",
                "endsOnString": "2026-03-01",
                "clippedVariant": "false",
                "detailsFormattedAttributesString": {"sections": []},
            },
        }

        offer = client._parse_single_offer(raw_offer)

        assert offer is not None
        assert offer.description == ""

    def test_parse_single_offer_with_missing_fields(self, client: SproutsClient) -> None:
        """Should create offer with empty strings when data is missing."""
        raw_offer = {"invalid": "data"}

        offer = client._parse_single_offer(raw_offer)

        assert offer is not None
        assert offer.id == ""
        assert offer.name == ""
        assert offer.is_clipped is False


@pytest.mark.unit_build
class TestParseOffers:
    """Test parsing multiple offers."""

    def test_parse_offers_with_valid_data(self, client: SproutsClient) -> None:
        """Should parse multiple offers from response."""
        graphql_response = {
            "data": {
                "userOffersV2": {
                    "offers": [
                        {
                            "id": "1",
                            "offerId": "off_1",
                            "couponId": "cpn_1",
                            "offerRequestKey": "key_1",
                            "viewSection": {
                                "nameString": "Offer 1",
                                "endsOnString": "2026-03-01",
                                "clippedVariant": "false",
                                "detailsFormattedAttributesString": {"sections": [{"text": "desc1"}]},
                            },
                        },
                        {
                            "id": "2",
                            "offerId": "off_2",
                            "couponId": "cpn_2",
                            "offerRequestKey": "key_2",
                            "viewSection": {
                                "nameString": "Offer 2",
                                "endsOnString": "2026-03-15",
                                "clippedVariant": "true",
                                "detailsFormattedAttributesString": {"sections": [{"text": "desc2"}]},
                            },
                        },
                    ]
                }
            }
        }

        offers = client._parse_offers(graphql_response)

        assert len(offers) == 2
        assert offers[0].name == "Offer 1"
        assert offers[0].is_clipped is False
        assert offers[1].name == "Offer 2"
        assert offers[1].is_clipped is True

    def test_parse_offers_includes_offers_with_missing_data(self, client: SproutsClient) -> None:
        """Should include offers even with missing data (empty strings)."""
        graphql_response = {
            "data": {
                "userOffersV2": {
                    "offers": [
                        {
                            "id": "1",
                            "offerId": "off_1",
                            "couponId": "cpn_1",
                            "offerRequestKey": "key_1",
                            "viewSection": {
                                "nameString": "Valid Offer",
                                "endsOnString": "2026-03-01",
                                "clippedVariant": "false",
                                "detailsFormattedAttributesString": {"sections": [{"text": "desc"}]},
                            },
                        },
                        {"invalid": "offer"},
                    ]
                }
            }
        }

        offers = client._parse_offers(graphql_response)

        # Both offers are parsed, second one has empty strings
        assert len(offers) == 2
        assert offers[0].name == "Valid Offer"
        assert offers[1].name == ""

    def test_parse_offers_with_empty_response(self, client: SproutsClient) -> None:
        """Should handle empty offers list."""
        graphql_response: dict = {"data": {"userOffersV2": {"offers": []}}}

        offers = client._parse_offers(graphql_response)

        assert offers == []


@pytest.mark.unit_build
class TestGetOffers:
    """Test fetching offers from API."""

    def test_get_offers_makes_correct_graphql_call(self, client: SproutsClient) -> None:
        """get_offers should call GraphQL with correct parameters."""
        mock_data: dict = {"data": {"userOffersV2": {"offers": []}}}

        with patch.object(client, "_graphql_get", return_value=mock_data) as mock_graphql:
            client.get_offers(limit=100)

            # Verify GraphQL was called correctly
            mock_graphql.assert_called_once()
            call_args = mock_graphql.call_args
            assert call_args[0][0] == "FindOffersForUserV2"
            variables = call_args[0][1]
            assert variables["shopId"] == "test_shop_123"
            assert variables["limit"] == 100
            assert "ic_inmar" in variables["offerSources"]

    def test_get_offers_returns_parsed_offers(self, client: SproutsClient) -> None:
        """get_offers should return parsed offers."""
        mock_data = {
            "data": {
                "userOffersV2": {
                    "offers": [
                        {
                            "id": "1",
                            "offerId": "off_1",
                            "couponId": "cpn_1",
                            "offerRequestKey": "key_1",
                            "viewSection": {
                                "nameString": "Test Offer",
                                "endsOnString": "2026-03-01",
                                "clippedVariant": "false",
                                "detailsFormattedAttributesString": {"sections": [{"text": "description"}]},
                            },
                        }
                    ]
                }
            }
        }

        with patch.object(client, "_graphql_get", return_value=mock_data):
            offers = client.get_offers()

            assert len(offers) == 1
            assert offers[0].name == "Test Offer"


@pytest.mark.unit_build
class TestGetAvailableOffer:
    """Test fetching detailed offer information."""

    def test_get_available_offer_makes_correct_call(self, client: SproutsClient, sample_offer: Offer) -> None:
        """_get_available_offer should call GraphQL with correct parameters."""
        mock_data = {"data": {"getAvailableOffer": {"items": [{"legacyId": "item_123"}]}}}

        with patch.object(client, "_graphql_get", return_value=mock_data) as mock_graphql:
            client._get_available_offer(sample_offer)

            # Verify call
            mock_graphql.assert_called_once()
            call_args = mock_graphql.call_args
            assert call_args[0][0] == "GetAvailableOffer"
            variables = call_args[0][1]
            assert variables["legacyOfferId"] == sample_offer.offer_id
            assert variables["shopId"] == "test_shop_123"
            assert variables["zoneId"] == "981"
            assert variables["postalCode"] == "95126"

    def test_get_available_offer_returns_data(self, client: SproutsClient, sample_offer: Offer) -> None:
        """_get_available_offer should return offer data."""
        mock_data = {"data": {"getAvailableOffer": {"items": [{"legacyId": "item_123"}]}}}

        with patch.object(client, "_graphql_get", return_value=mock_data):
            result = client._get_available_offer(sample_offer)

            assert result is not None
            assert result["items"][0]["legacyId"] == "item_123"

    def test_get_available_offer_returns_none_when_not_found(self, client: SproutsClient, sample_offer: Offer) -> None:
        """_get_available_offer should return None when offer not found."""
        mock_data = {"data": {"getAvailableOffer": None}}

        with patch.object(client, "_graphql_get", return_value=mock_data):
            result = client._get_available_offer(sample_offer)

            assert result is None

    def test_get_available_offer_returns_none_on_error(self, client: SproutsClient, sample_offer: Offer) -> None:
        """_get_available_offer should return None on exception."""
        with patch.object(client, "_graphql_get", side_effect=RuntimeError("API error")):
            result = client._get_available_offer(sample_offer)

            assert result is None


@pytest.mark.unit_build
class TestClipCoupon:
    """Test coupon clipping functionality."""

    def test_clip_coupon_returns_true_if_already_clipped(self, client: SproutsClient, sample_offer: Offer) -> None:
        """clip_coupon should return True without API call if already clipped."""
        sample_offer.is_clipped = True

        result = client.clip_coupon(sample_offer)

        assert result is True

    def test_clip_coupon_gets_offer_details_first(self, client: SproutsClient, sample_offer: Offer) -> None:
        """clip_coupon should fetch offer details before clipping."""
        mock_offer_data = {"items": [{"legacyId": "item_123"}]}
        mock_clip_data = {"data": {"clipCouponV2": {"success": True}}}

        with patch.object(client, "_get_available_offer", return_value=mock_offer_data) as mock_get_offer:
            with patch.object(client, "_graphql_get", return_value=mock_clip_data):
                result = client.clip_coupon(sample_offer)

                # Verify it tried to get offer details
                mock_get_offer.assert_called_once_with(sample_offer)
                assert result is True

    def test_clip_coupon_returns_false_when_offer_details_fail(
        self, client: SproutsClient, sample_offer: Offer
    ) -> None:
        """clip_coupon should return False if can't get offer details."""
        with patch.object(client, "_get_available_offer", return_value=None):
            result = client.clip_coupon(sample_offer)

            assert result is False

    def test_clip_coupon_returns_false_when_no_items(self, client: SproutsClient, sample_offer: Offer) -> None:
        """clip_coupon should return False if offer has no items."""
        mock_offer_data: dict = {"items": []}

        with patch.object(client, "_get_available_offer", return_value=mock_offer_data):
            result = client.clip_coupon(sample_offer)

            assert result is False

    def test_clip_coupon_returns_false_when_no_legacy_id(self, client: SproutsClient, sample_offer: Offer) -> None:
        """clip_coupon should return False if item has no legacyId."""
        mock_offer_data = {"items": [{"otherField": "value"}]}

        with patch.object(client, "_get_available_offer", return_value=mock_offer_data):
            result = client.clip_coupon(sample_offer)

            assert result is False

    def test_clip_coupon_makes_correct_clip_call(self, client: SproutsClient, sample_offer: Offer) -> None:
        """clip_coupon should call ClipCoupon with correct parameters."""
        mock_offer_data = {"items": [{"legacyId": "item_123"}]}
        mock_clip_data = {"data": {"clipCouponV2": {"success": True}}}

        with patch.object(client, "_get_available_offer", return_value=mock_offer_data):
            with patch.object(client, "_graphql_get", return_value=mock_clip_data) as mock_graphql:
                result = client.clip_coupon(sample_offer)

                # Verify clip call
                mock_graphql.assert_called_once()
                call_args = mock_graphql.call_args
                assert call_args[0][0] == "ClipCoupon"
                variables = call_args[0][1]
                assert variables["itemId"] == "item_123"
                assert variables["shopId"] == "test_shop_123"
                assert variables["offerReference"] == f"{sample_offer.offer_request_key}/{sample_offer.offer_id}"
                assert "trackingParams" in variables
                assert variables["trackingParams"]["sourceType"] == "shop_content_page"
                assert result is True

    def test_clip_coupon_returns_false_when_clip_fails(self, client: SproutsClient, sample_offer: Offer) -> None:
        """clip_coupon should return False if clipping fails."""
        mock_offer_data = {"items": [{"legacyId": "item_123"}]}
        mock_clip_data = {"data": {"clipCouponV2": None}}

        with patch.object(client, "_get_available_offer", return_value=mock_offer_data):
            with patch.object(client, "_graphql_get", return_value=mock_clip_data):
                result = client.clip_coupon(sample_offer)

                assert result is False

    def test_clip_coupon_returns_false_on_exception(self, client: SproutsClient, sample_offer: Offer) -> None:
        """clip_coupon should return False if GraphQL call raises exception."""
        mock_offer_data = {"items": [{"legacyId": "item_123"}]}

        with patch.object(client, "_get_available_offer", return_value=mock_offer_data):
            with patch.object(client, "_graphql_get", side_effect=RuntimeError("API error")):
                result = client.clip_coupon(sample_offer)

                assert result is False
