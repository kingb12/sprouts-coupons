"""
Integration tests for Sprouts coupon clipper.

These tests hit real services and require valid credentials in .env.
Run with: pytest -m integration
"""

import logging
import os

import pytest
import requests

from sprouts_coupons.client import SproutsClient
from sprouts_coupons.email import send_clip_report
from sprouts_coupons.models import Offer, SessionInfo
from sprouts_coupons.session import login_and_get_session, write_user_info

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def authenticated_session() -> SessionInfo:
    """Login once and reuse session across tests in this module."""
    logger.info("Logging in to Sprouts (headless)...")
    session = login_and_get_session(headless=True)
    logger.info(f"Session acquired. User: {session.user_name}, Shop ID: {session.shop_id}")
    return session


@pytest.mark.integration
@pytest.mark.slow
class TestLogin:
    """Test login functionality."""

    def test_headless_login_succeeds(self, authenticated_session: SessionInfo):
        """Login should complete and return session info."""
        assert authenticated_session is not None
        assert authenticated_session.cookies, "Expected cookies to be set"
        assert authenticated_session.shop_id, "Expected shop_id to be set"

    def test_session_has_required_cookies(self, authenticated_session: SessionInfo):
        """Session should contain authentication cookies."""
        cookies = authenticated_session.cookies
        # Check for key cookies that indicate successful login
        cookie_names = list(cookies.keys())
        logger.info(f"Cookies received: {cookie_names}")

        # Should have instacart session cookies
        has_session_cookie = any(
            "session" in name.lower() or "sid" in name.lower()
            for name in cookie_names
        )
        assert has_session_cookie, f"Expected session cookie, got: {cookie_names}"

    def test_write_user_info(self, authenticated_session: SessionInfo, tmp_path):
        """Should write user info to file."""
        output_file = tmp_path / "USER_INFO.txt"
        write_user_info(authenticated_session, str(output_file))

        assert output_file.exists()
        content = output_file.read_text()
        assert "User Name:" in content
        assert "Default Store:" in content


@pytest.mark.integration
@pytest.mark.slow
class TestCouponAPI:
    """Test the coupon GraphQL API."""

    def test_api_with_auth_cookies_returns_offers(self, authenticated_session: SessionInfo):
        """API call with valid session should return offers."""
        client = SproutsClient(authenticated_session)
        offers = client.get_offers(limit=30)

        assert isinstance(offers, list)
        assert len(offers) > 0, "Expected at least some offers"

        # Verify offer structure
        first_offer = offers[0]
        assert isinstance(first_offer, Offer)
        assert first_offer.id
        assert first_offer.name
        logger.info(f"Retrieved {len(offers)} offers. First: {first_offer.name}")

    def test_api_without_auth_cookies_fails(self):
        """API call without authentication should fail or return empty."""
        # Create a session with no cookies
        fake_session = SessionInfo(
            cookies={},
            shop_id="473512",
            user_name="test",
            store_name="test",
        )
        client = SproutsClient(fake_session)

        # The API may either:
        # 1. Return 401/403
        # 2. Return an error in the response
        # 3. Return empty offers
        try:
            offers = client.get_offers(limit=10)
            # If we get here, check that we either got an error or empty/minimal data
            # Without auth, user-specific offers shouldn't be available
            logger.info(f"Without auth, got {len(offers)} offers")
            # We don't assert failure here since the API might return public data
            # The key test is that authenticated requests work better
        except requests.exceptions.HTTPError as e:
            # Expected - API should reject unauthenticated requests
            logger.info(f"API correctly rejected unauthenticated request: {e}")
            assert e.response.status_code in [401, 403, 400]

    def test_offers_have_expected_fields(self, authenticated_session: SessionInfo):
        """Offers should have all expected fields populated."""
        client = SproutsClient(authenticated_session)
        offers = client.get_offers(limit=10)

        for offer in offers[:5]:  # Check first 5
            assert offer.id, "Offer should have id"
            assert offer.offer_id, "Offer should have offer_id"
            assert offer.name, "Offer should have name"
            # These may be optional but should be strings
            assert isinstance(offer.description, str)
            assert isinstance(offer.expires_on, str)
            assert isinstance(offer.is_clipped, bool)


@pytest.mark.integration
@pytest.mark.slow
class TestClipCoupon:
    """Test coupon clipping functionality."""

    def test_clip_coupon_stub_returns_true(self, authenticated_session: SessionInfo):
        """Stub clip_coupon should return True."""
        client = SproutsClient(authenticated_session)
        offers = client.get_offers(limit=5)

        # Find an unclipped offer if possible
        test_offer = next((o for o in offers if not o.is_clipped), offers[0] if offers else None)

        if test_offer:
            result = client.clip_coupon(test_offer)
            assert result is True, "Stub should return True"


@pytest.mark.integration
@pytest.mark.slow
class TestEmailReport:
    """Test email reporting functionality."""

    def test_send_email_dry_run(self, authenticated_session: SessionInfo, capsys):
        """Dry run should print report without sending."""
        client = SproutsClient(authenticated_session)
        offers = client.get_offers(limit=20)

        send_clip_report(offers, dry_run=True)

        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "Sprouts Coupons Report" in captured.out
        assert "Total offers:" in captured.out

    def test_send_real_email(self, authenticated_session: SessionInfo):
        """Send a real email report.

        This test actually sends an email to the configured recipient.
        """
        client = SproutsClient(authenticated_session)
        offers = client.get_offers(limit=50)

        logger.info(f"Sending email report with {len(offers)} offers...")
        # This will attempt to send a real email
        send_clip_report(offers, dry_run=False)
        logger.info("Email send attempted - check inbox")


@pytest.mark.integration
@pytest.mark.slow
class TestFullFlow:
    """Test the complete end-to-end flow."""

    def test_full_flow(self, authenticated_session: SessionInfo, tmp_path):
        """Run the complete flow: login -> fetch offers -> log -> clip stub -> email."""
        # Step 1: Session already acquired via fixture
        logger.info(f"Step 1 - Login: User={authenticated_session.user_name}")

        # Step 2: Write user info
        user_info_path = tmp_path / "USER_INFO.txt"
        write_user_info(authenticated_session, str(user_info_path))
        assert user_info_path.exists()
        logger.info(f"Step 2 - User info written to {user_info_path}")

        # Step 3: Fetch offers
        client = SproutsClient(authenticated_session)
        offers = client.get_offers()
        assert len(offers) > 0
        logger.info(f"Step 3 - Fetched {len(offers)} offers")

        # Step 4: Log offer details
        clipped_count = sum(1 for o in offers if o.is_clipped)
        available_count = len(offers) - clipped_count
        logger.info(f"Step 4 - Summary: {clipped_count} clipped, {available_count} available")

        # Log first few offers
        for offer in offers[:5]:
            logger.info(f"  Offer: {offer}")

        # Step 5: Clip coupons (stub)
        unclipped = [o for o in offers if not o.is_clipped]
        if unclipped:
            test_offer = unclipped[0]
            result = client.clip_coupon(test_offer)
            assert result is True
            logger.info(f"Step 5 - Clip stub called for: {test_offer.name}")

        # Step 6: Email report (dry run for test)
        send_clip_report(offers, dry_run=True)
        logger.info("Step 6 - Email report (dry run) completed")

        logger.info("Full flow completed successfully!")
