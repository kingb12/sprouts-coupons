import logging
import subprocess
from email.message import EmailMessage

from .models import Offer

logger = logging.getLogger(__name__)
# Separate logger for reports - can be configured with its own file handler
report_logger = logging.getLogger("sprouts_coupons.reports")


def build_report(offers: list[Offer]) -> str:
    """Build the text report of coupon status."""
    clipped = [o for o in offers if o.is_clipped]
    available = [o for o in offers if not o.is_clipped]

    lines = [
        "Sprouts Coupons Report",
        "=" * 40,
        "",
        f"Total offers: {len(offers)}",
        f"Clipped: {len(clipped)}",
        f"Available: {len(available)}",
        "",
    ]

    if clipped:
        lines.append("Clipped Coupons:")
        lines.append("-" * 20)
        for offer in clipped[:20]:
            lines.append(f"  - {offer.name}")
            if offer.description:
                lines.append(f"    {offer.description}")
        if len(clipped) > 20:
            lines.append(f"  ... and {len(clipped) - 20} more")
        lines.append("")

    if available:
        lines.append("Available Coupons:")
        lines.append("-" * 20)
        for offer in available[:20]:
            lines.append(f"  - {offer.name}")
        if len(available) > 20:
            lines.append(f"  ... and {len(available) - 20} more")

    return "\n".join(lines)


def log_report(offers: list[Offer]) -> str:
    """Log the report to the report logger and return the report text."""
    report = build_report(offers)
    report_logger.info("\n" + report)
    return report


def send_clip_report(
    offers: list[Offer],
    sender: str,
    recipient: str,
    sendmail_path: str = "/usr/sbin/sendmail",
) -> bool:
    """
    Send an email report of clipped coupons.

    Args:
        offers: List of coupon offers
        sender: Email sender address (required)
        recipient: Email recipient address (required)
        sendmail_path: Path to sendmail binary

    Returns:
        True if email was sent successfully, False otherwise
    """
    clipped = [o for o in offers if o.is_clipped]
    subject = f"Sprouts coupons: {len(clipped)} clipped"
    body = build_report(offers)

    logger.info(f"Sending email to {recipient}")
    logger.debug(f"Email body:\n{body}")

    return _send_email(sendmail_path, sender, recipient, subject, body)


def _send_email(
    sendmail_path: str,
    sender: str,
    recipient: str,
    subject: str,
    body: str,
) -> bool:
    """Send email using sendmail."""
    msg = EmailMessage()
    msg["To"] = recipient
    msg["From"] = sender
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        p = subprocess.Popen(
            [sendmail_path, "-f", sender, "-t"],
            stdin=subprocess.PIPE,
        )
        p.communicate(msg.as_bytes())
        if p.returncode != 0:
            logger.error(f"sendmail exited with code {p.returncode}")
            return False
        logger.info("Email sent successfully")
        return True
    except FileNotFoundError:
        logger.error(f"sendmail not found at {sendmail_path}")
        return False
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False
