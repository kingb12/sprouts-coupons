# Sprouts Coupon Clipper

**sprouts-coupons** is a script that will log in to your Sprouts Farmers Market account,
and automatically clip all available digital coupons so they don't have to be selected manually.

## Design notes

- `sprouts-coupons` performs authentication using a headless instance of a Playwright-controlled browser, defaulting to `firefox`.
- Once a signed-in session is established, coupon clipping is performed using dirct HTTP requests via the Sprouts GraphQL API with [requests][requests].

## Installation

### Prerequisites

* Python 3.12 or higher
* Playwright browser (installed automatically)
* Optional: `sendmail` (for email support)

### Installation from source

Clone the repository and install with using [uv](https://docs.astral.sh/uv/) (recommended):

```console
git clone https://github.com/kingb12/sprouts-coupons.git
cd sprouts-coupons
uv venv
uv pip install -e .
```

### Install Playwright browsers

After installation, install the required browser:

```console
playwright install firefox
```

## Docker Usage

### Build and run with Docker

Build the Docker image:

```console
docker build -t sprouts-coupons .
```

Run the container:

```console
docker run --rm \
  -e SPROUTS_USERNAME=your@email.com \
  -e SPROUTS_PASSWORD=yourpassword \
  -v $(pwd)/logs:/app/logs \
  sprouts-coupons
```

### Using docker-compose

Create a `.env` file with your credentials:

```env
SPROUTS_USERNAME=your@email.com
SPROUTS_PASSWORD=yourpassword

# For email notifications in Docker, you need SMTP settings
# Use a Gmail App Password: https://myaccount.google.com/apppasswords
SPROUTS_EMAIL_SENDER=your@gmail.com
SPROUTS_EMAIL_RECIPIENT=your.email@example.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASSWORD=your-app-password-here
```

**Important for Gmail:** You must use an [App Password](https://myaccount.google.com/apppasswords), not your regular Gmail password. This is a 16-character password that Google generates specifically for applications.

Then run:

```console
docker-compose up --build
```

The Dockerfile uses `playwright install --with-deps firefox` which installs both the Firefox browser AND all the required system libraries. For email, it uses `msmtp` (a lightweight SMTP client) configured automatically from your environment variables.

**Cron scheduling:** The container runs a cron daemon and executes the script according to the `CRON_SCHEDULE` environment variable (default: daily at 2 AM UTC).

```env
# Run daily at 12 AM (default)
CRON_SCHEDULE=0 0 * * *

# Or run every 6 hours:
# CRON_SCHEDULE=0 */6 * * *

# Or weekly on Sunday at midnight:
# CRON_SCHEDULE=0 0 * * 0
```

Start the container in detached mode:

```console
docker-compose up -d
```

View logs:

```console
docker-compose logs -f
# Or check the cron-specific log:
tail -f logs/cron.log
```

Stop the container:

```console
docker-compose down
```

## Usage

### Basic usage

Set the following environment variables (`.env` supported):

#### Basic Configuration
```env
SPROUTS_USERNAME=<your username>
SPROUTS_PASSWORD=<your password>
# Optional: to receive email report post run
SPROUTS_EMAIL_SENDER=<email address which can support sending in `sendmail`>
SPROUTS_EMAIL_RECIPIENT=<Email address to receive report>
```

Run the coupon clipper:

```console
sprouts-coupons
```

By default, the script runs in headless mode. To see the browser window:

```console
sprouts-coupons --no-headless
```

### Command-line options

For full usage options, run:

```console
sprouts-coupons --help
```

Available options:

* `--headless/--no-headless`: Run browser in headless mode (default: headless)
* `--dry-run`: Don't send email, just print report to console
* `--skip-clip`: Don't clip coupons, just list them
* `-v, --verbose`: Enable debug logging

### Further Configuration (Environment Variables)

Configure your Sprouts account and email settings using environment variables:

* `SPROUTS_LOG_DIR`: Directory for log files (default: `logs/`)
  - Saves program logs to `sprouts_coupons.log`
  - Saves reports to `reports.log`


### Running with cron

For best results, run this program regularly with a cron daemon.

Example crontab entry to run daily at 2 AM:

```cron
0 2 * * * cd /path/to/sprouts-coupons && .venv/bin/sprouts-coupons --headless >> logs/cron.log 2>&1
```

### Email reports

If `SPROUTS_EMAIL_SENDER` and `SPROUTS_EMAIL_RECIPIENT` are configured, an email report
will be sent after each run via `sendmail`. The report includes:

* Total offers available
* Number of coupons already clipped
* Number of newly clipped coupons
* List of clipped and available coupons

Reports are also logged to `logs/reports.log`.

### Logs

The script creates detailed logs in the `logs/` directory:

* `sprouts_coupons.log`: Detailed debug information
* `reports.log`: Coupon reports from each run

## Development

### Development installation

Install with development dependencies:

```console
uv pip install -e ".[dev]"
```

### Install pre-commit hooks

```console
pre-commit install
```

### Development tasks

* Run linter: `ruff check --fix`
* Run formatter: `ruff format`
* Run all pre-commit hooks: `pre-commit run --all-files`
* Run unit tests: `pytest -m unit_build`
* Run integration tests: `pytest -m integration` (requires valid credentials)
* Run all tests: `pytest`
* Type checking: `mypy src/`

