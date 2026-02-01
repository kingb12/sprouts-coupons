import argparse
import logging
import sys

from .client import SproutsClient
from .email import send_clip_report
from .models import Offer
from .session import login_and_get_session, write_user_info

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def clip_all_coupons(client: SproutsClient, offers: list[Offer]) -> list[Offer]:
    """Clip all unclipped coupons and return list of newly clipped."""
    newly_clipped = []
    for offer in offers:
        if not offer.is_clipped:
            logger.info(f"Clipping: {offer}")
            if client.clip_coupon(offer):
                offer.is_clipped = True
                newly_clipped.append(offer)
    return newly_clipped


def main() -> int:
    parser = argparse.ArgumentParser(description="Sprouts coupon clipper")
    parser.add_argument("--headless", action="store_true", default=True, help="Run browser in headless mode")
    parser.add_argument("--no-headless", dest="headless", action="store_false", help="Run browser with visible window")
    parser.add_argument("--dry-run", action="store_true", help="Don't send email, just print report")
    parser.add_argument("--skip-clip", action="store_true", help="Don't clip coupons, just list them")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # Login and get session
        logger.info("Logging in to Sprouts...")
        session = login_and_get_session(headless=args.headless)
        logger.info(f"Logged in as: {session.user_name}")
        logger.info(f"Store: {session.store_name}")

        # Write user info
        write_user_info(session)

        # Create client and fetch offers
        client = SproutsClient(session)
        logger.info("Fetching coupons...")
        offers = client.get_offers()
        logger.info(f"Found {len(offers)} total offers")

        # Log each offer
        clipped_count = 0
        available_count = 0
        for offer in offers:
            if offer.is_clipped:
                clipped_count += 1
            else:
                available_count += 1
            logger.info(offer)

        logger.info(f"Summary: {clipped_count} clipped, {available_count} available")

        # Clip coupons if not skipped
        if not args.skip_clip:
            newly_clipped = clip_all_coupons(client, offers)
            logger.info(f"Newly clipped: {len(newly_clipped)} coupons")

        # Send email report
        send_clip_report(offers, dry_run=args.dry_run)

        return 0

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
