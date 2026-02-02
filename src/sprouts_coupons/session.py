import logging
import os
import re
from typing import Literal

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from .models import SessionInfo

logger = logging.getLogger(__name__)

BrowserType = Literal["firefox", "chromium", "webkit"]


def get_credentials() -> tuple[str, str]:
    """Load credentials from environment."""
    load_dotenv()
    username = os.environ.get("SPROUTS_USERNAME")
    password = os.environ.get("SPROUTS_PASSWORD")
    if not username or not password:
        raise ValueError("SPROUTS_USERNAME and SPROUTS_PASSWORD must be set in .env")
    return username, password


def login_and_get_session(
    headless: bool = True,
    browser_type: BrowserType = "firefox",
) -> SessionInfo:
    """
    Login to Sprouts and extract session information.

    Args:
        headless: Run browser without UI (set False to see what's happening)
        browser_type: Browser to use - firefox (default), chromium, or webkit
    """
    username, password = get_credentials()

    with sync_playwright() as p:
        browser_launcher = getattr(p, browser_type)
        browser = browser_launcher.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()

        logger.info("Navigating to Sprouts storefront")
        page.goto("https://shop.sprouts.com/store/sprouts/storefront", timeout=60000)
        page.wait_for_load_state("networkidle", timeout=30000)

        logger.info("Dismissing cookie dialog")
        reject_cookies_btn = page.get_by_role("button", name="REJECT COOKIES")
        reject_cookies_btn.wait_for(state="visible", timeout=15000)
        reject_cookies_btn.click()

        page.wait_for_load_state("networkidle", timeout=30000)
        page.wait_for_timeout(2000)

        logger.info("Confirming shop mode")
        confirm_btn = page.get_by_role("button", name="Confirm")
        confirm_btn.wait_for(state="visible", timeout=15000)
        confirm_btn.click()

        page.wait_for_load_state("networkidle", timeout=30000)
        page.wait_for_timeout(2000)

        logger.info("Clicking Sign In link")
        sign_in_link = page.get_by_role("link", name="Sign In / Register")
        sign_in_link.wait_for(state="visible", timeout=15000)
        sign_in_link.click()

        page.wait_for_load_state("networkidle", timeout=30000)
        page.wait_for_timeout(2000)

        logger.info("Filling login form")
        email_input = page.get_by_role("textbox", name="Email Address")
        email_input.wait_for(state="visible", timeout=15000)
        email_input.click()
        email_input.fill(username)

        password_input = page.get_by_role("textbox", name="Password")
        password_input.click()
        password_input.fill(password)

        logger.info("Submitting login")
        login_btn = page.get_by_role("button", name="Login")
        login_btn.click()

        logger.info("Waiting for login to complete")
        page.wait_for_url("**/shop.sprouts.com/**", timeout=60000)
        page.wait_for_load_state("networkidle", timeout=30000)
        page.wait_for_timeout(3000)

        shop_id = _extract_shop_id(page)
        cookies = {c["name"]: c["value"] for c in context.cookies()}

        browser.close()

        return SessionInfo(cookies=cookies, shop_id=shop_id)


def _extract_shop_id(page) -> str:  # type: ignore
    """Extract shop ID from cookies or URL."""
    # Check cookies first
    cookies = page.context.cookies()
    for cookie in cookies:
        if "shop" in cookie["name"].lower() and "id" in cookie["name"].lower():
            return str(cookie["value"])

    # Check URL for shop ID
    url = page.url
    match = re.search(r"shopId[=:](\d+)", url)
    if match:
        return match.group(1)

    # Fallback - log warning and use default
    logger.warning("Could not extract shopId from cookies or URL, using default")
    return "473512"
