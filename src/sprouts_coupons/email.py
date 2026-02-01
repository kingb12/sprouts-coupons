import logging
import os
import subprocess
from email.message import EmailMessage

from .models import Offer

logger = logging.getLogger(__name__)

# Email config from safeway-coupons config.ini
DEFAULT_SENDER = "kingb12automation@gmail.com"
DEFAULT_RECIPIENT = "kingbrendan94@gmail.com"


def send_clip_report(
    offers: list[Offer],
    sender: str = DEFAULT_SENDER,
    recipient: str = DEFAULT_RECIPIENT,
    sendmail_path: str = "/usr/sbin/sendmail",
    dry_run: bool = False,
) -> None:
    """Send an email report of clipped coupons."""
    clipped = [o for o in offers if o.is_clipped]
    available = [o for o in offers if not o.is_clipped]

    subject = f"Sprouts coupons: {len(clipped)} clipped"

    body_lines = [
        f"Sprouts Coupons Report",
        f"=" * 40,
        f"",
        f"Total offers: {len(offers)}",
        f"Clipped: {len(clipped)}",
        f"Available: {len(available)}",
        f"",
    ]

    if clipped:
        body_lines.append("Clipped Coupons:")
        body_lines.append("-" * 20)
        for offer in clipped[:20]:  # Limit to first 20
            body_lines.append(f"  - {offer.name}")
        if len(clipped) > 20:
            body_lines.append(f"  ... and {len(clipped) - 20} more")
        body_lines.append("")

    body = os.linesep.join(body_lines)

    logger.info(f"{'Would send' if dry_run else 'Sending'} email to {recipient}")
    logger.debug(f"Email body:\n{body}")

    if dry_run:
        print(f"[DRY RUN] Email to {recipient}:")
        print("=" * 40)
        print(body)
        print("=" * 40)
        return

    _send_email(sendmail_path, sender, recipient, subject, body)


def _send_email(
    sendmail_path: str,
    sender: str,
    recipient: str,
    subject: str,
    body: str,
) -> None:
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
        else:
            logger.info("Email sent successfully")
    except FileNotFoundError:
        logger.error(f"sendmail not found at {sendmail_path}")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
