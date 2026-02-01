"""
Sprouts Coupons - Automated coupon clipper for Sprouts Farmers Market.

This package provides tools to:
- Log in to Sprouts via headless browser (Playwright/Firefox)
- Fetch available coupon offers via GraphQL API
- Clip coupons programmatically
- Send email reports of clipped coupons
"""

from .client import SproutsClient
from .models import Offer, SessionInfo
from .session import login_and_get_session

__all__ = [
    "SproutsClient",
    "Offer",
    "SessionInfo",
    "login_and_get_session",
]
