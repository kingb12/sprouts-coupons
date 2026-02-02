#!/bin/bash
set -e

# Install cron if not present
if ! command -v cron &> /dev/null; then
    echo "Installing cron..."
    apt-get update && apt-get install -y cron && rm -rf /var/lib/apt/lists/*
fi

# Configure msmtp if SMTP settings are provided
if [ -n "$SMTP_HOST" ] && [ -n "$SMTP_USER" ] && [ -n "$SMTP_PASSWORD" ]; then
    echo "Configuring msmtp for email..."
    
    cat > /etc/msmtprc <<EOF
# Default settings
defaults
auth           on
tls            on
tls_trust_file /etc/ssl/certs/ca-certificates.crt
logfile        /app/logs/msmtp.log

# Gmail account
account        gmail
host           ${SMTP_HOST:-smtp.gmail.com}
port           ${SMTP_PORT:-587}
from           ${SPROUTS_EMAIL_SENDER}
user           ${SMTP_USER}
password       ${SMTP_PASSWORD}

# Set default account
account default : gmail
EOF

    chmod 600 /etc/msmtprc
    echo "msmtp configured successfully"
else
    echo "SMTP settings not provided - email notifications will be disabled"
    echo "Set SMTP_HOST, SMTP_USER, and SMTP_PASSWORD to enable email"
fi

# Set up environment variables for cron
env | grep -E '^(SPROUTS_|SMTP_|PATH)' > /etc/environment

# Create crontab with the schedule
CRON_SCHEDULE=${CRON_SCHEDULE:-0 0 * * *}
echo "Setting up cron with schedule: $CRON_SCHEDULE"

# Create crontab entry
echo "$CRON_SCHEDULE cd /app && sprouts-coupons --headless >> /app/logs/cron.log 2>&1" > /etc/cron.d/sprouts-coupons
chmod 0644 /etc/cron.d/sprouts-coupons
crontab /etc/cron.d/sprouts-coupons

echo "Cron job configured. Container will run sprouts-coupons on schedule: $CRON_SCHEDULE"
echo "Logs will be written to /app/logs/cron.log"

# Run cron in foreground to keep container alive
exec cron -f
