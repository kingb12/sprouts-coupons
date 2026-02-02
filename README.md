# Sprouts Coupon Clipper

Automatically log in to your Sprouts Farmers Market account and clip all available digital coupons.

## Quick Start (Docker - Recommended)

**Prerequisites:** `docker`, `docker compose`

1. Create a `.env` file:

```env
SPROUTS_USERNAME=your@email.com
SPROUTS_PASSWORD=yourpassword

# Optional: Email notifications (requires Gmail App Password)
SPROUTS_EMAIL_SENDER=your@gmail.com
SPROUTS_EMAIL_RECIPIENT=your.email@example.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASSWORD=your-16-char-app-password  # NOT YOUR GMAIL PASSWORD!

# Optional: Schedule (default: daily at midnight UTC)
CRON_SCHEDULE=0 0 * * *
```

2. Start:

```console
docker compose up -d
```

3. View logs:

```console
docker compose logs -f
# or
tail -f logs/cron.log
```

**Gmail App Password:** These are distinct 16 character codes for using a Gmail account, do not give your full account password! Get one at https://myaccount.google.com/apppasswords

## Installation from Source

**Prerequisites:** Python 3.12+, [uv](https://docs.astral.sh/uv/)

```console
git clone https://github.com/kingb12/sprouts-coupons.git
cd sprouts-coupons
uv venv
uv pip install -e .
playwright install firefox
```

### Usage

Set environment variables:

```env
SPROUTS_USERNAME=your@email.com
SPROUTS_PASSWORD=yourpassword
SPROUTS_EMAIL_SENDER=your@email.com  # Optional
SPROUTS_EMAIL_RECIPIENT=your@email.com  # Optional
```

Run:

```console
sprouts-coupons                    # Run in headless mode
sprouts-coupons --no-headless      # Show browser
sprouts-coupons --dry-run          # Preview without sending email
sprouts-coupons --skip-clip        # List coupons only
sprouts-coupons -v                 # Verbose logging
```

### Cron Setup

```cron
0 2 * * * cd /path/to/sprouts-coupons && .venv/bin/sprouts-coupons --headless >> logs/cron.log 2>&1
```

## Development

```console
uv pip install -e ".[dev]"
pre-commit install
```

**Tasks:**
- Lint: `ruff check --fix`
- Format: `ruff format`
- Test: `pytest -m unit_build`
- Type check: `mypy src/`

## How It Works

1. Authenticates via Playwright-controlled Firefox browser
2. Clips coupons using Sprouts GraphQL API
3. Sends email report via `msmtp` (Docker) or `sendmail` (local)

Logs: `logs/sprouts_coupons.log`, `logs/reports.log`

[requests]: https://requests.readthedocs.io/en/latest/

