import argparse
import logging
import os
import sys
from pathlib import Path

from .client import SproutsClient
from .email import log_report, send_clip_report
from .models import Offer
from .session import login_and_get_session

# Configure root logger
logger = logging.getLogger(__name__)

# Log directory - can be overridden via SPROUTS_LOG_DIR env var
LOG_DIR = Path(os.environ.get("SPROUTS_LOG_DIR", "logs"))


def setup_logging(verbose: bool = False) -> None:
    """Configure logging with console and file handlers."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Root logger level
    root_level = logging.DEBUG if verbose else logging.INFO

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(root_level)
    console_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

    # File handler for all logs
    file_handler = logging.FileHandler(LOG_DIR / "sprouts_coupons.log")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Report logger with its own file
    report_logger = logging.getLogger("sprouts_coupons.reports")
    report_handler = logging.FileHandler(LOG_DIR / "reports.log")
    report_handler.setLevel(logging.INFO)
    report_handler.setFormatter(logging.Formatter("%(asctime)s\n%(message)s\n"))
    report_logger.addHandler(report_handler)


def clip_all_coupons(client: SproutsClient, offers: list[Offer]) -> list[Offer]:
    """Clip all unclipped coupons and return list of newly clipped."""
    newly_clipped: list[Offer] = []
    for offer in offers:
        if not offer.is_clipped:
            logger.info(f"Clipping: {offer}")
            if client.clip_coupon(offer):
                offer.is_clipped = True
                newly_clipped.append(offer)
    return newly_clipped


def main() -> int:
    parser = argparse.ArgumentParser(description="Sprouts coupon clipper")
    parser.add_argument(
        "--headless/--no-headless",
        dest="headless",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Run browser in headless mode (default: headless)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't send email, just print report",
    )
    parser.add_argument(
        "--skip-clip",
        action="store_true",
        help="Don't clip coupons, just list them",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    setup_logging(verbose=args.verbose)

    try:
        # Login and get session
        logger.info("Logging in to Sprouts...")
        session = login_and_get_session(headless=args.headless)
        logger.info(f"Logged in successfully, shop_id={session.shop_id}")

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

        # Always log the report to file
        log_report(offers)

        # Send email if configured
        sender = os.environ.get("SPROUTS_EMAIL_SENDER")
        recipient = os.environ.get("SPROUTS_EMAIL_RECIPIENT")

        if args.dry_run:
            from .email import build_report

            print("[DRY RUN] Would send email report:")
            print("=" * 40)
            print(build_report(offers))
            print("=" * 40)
        elif sender and recipient:
            send_clip_report(offers, sender=sender, recipient=recipient)
        else:
            logger.warning(
                "Email not sent: SPROUTS_EMAIL_SENDER and SPROUTS_EMAIL_RECIPIENT "
                "environment variables not set. Report logged to logs/reports.log"
            )

        return 0

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
