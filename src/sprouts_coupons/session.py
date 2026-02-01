import logging
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from .models import SessionInfo

logger = logging.getLogger(__name__)


def get_credentials() -> tuple[str, str]:
    """Load credentials from environment."""
    load_dotenv()
    username = os.environ.get("SPROUTS_USERNAME")
    password = os.environ.get("SPROUTS_PASSWORD")
    if not username or not password:
        raise ValueError("SPROUTS_USERNAME and SPROUTS_PASSWORD must be set in .env")
    return username, password


def login_and_get_session(headless: bool = True, debug: bool = False) -> SessionInfo:
    """
    Login to Sprouts and extract session information.

    Args:
        headless: Run browser without UI (set False to see what's happening)
        debug: If True, pause at key points for manual inspection
    """
    username, password = get_credentials()

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()

        # Navigate to storefront
        logger.info("Navigating to Sprouts storefront")
        page.goto("https://shop.sprouts.com/store/sprouts/storefront", timeout=60000)
        page.wait_for_load_state("networkidle", timeout=30000)

        # Dismiss cookie dialog - page may refresh after this
        logger.info("Dismissing cookie dialog")
        reject_cookies_btn = page.get_by_role("button", name="REJECT COOKIES")
        reject_cookies_btn.wait_for(state="visible", timeout=15000)
        reject_cookies_btn.click()

        # Wait for page to stabilize after cookie choice
        page.wait_for_load_state("networkidle", timeout=30000)
        page.wait_for_timeout(2000)

        # Confirm shop mode selection - page may refresh after this
        logger.info("Confirming shop mode")
        confirm_btn = page.get_by_role("button", name="Confirm")
        confirm_btn.wait_for(state="visible", timeout=15000)
        confirm_btn.click()

        # Wait for page to stabilize after confirmation
        page.wait_for_load_state("networkidle", timeout=30000)
        page.wait_for_timeout(2000)

        if debug:
            logger.info("PAUSED: After cookie/confirm dialogs dismissed")
            page.pause()

        # Click Sign In link
        logger.info("Clicking Sign In link")
        sign_in_link = page.get_by_role("link", name="Sign In / Register")
        sign_in_link.wait_for(state="visible", timeout=15000)
        sign_in_link.click()

        # Wait for login page to load
        page.wait_for_load_state("networkidle", timeout=30000)
        page.wait_for_timeout(2000)

        if debug:
            logger.info("PAUSED: On login page")
            page.pause()

        # Fill login form
        logger.info("Filling login form")
        email_input = page.get_by_role("textbox", name="Email Address")
        email_input.wait_for(state="visible", timeout=15000)
        email_input.click()
        email_input.fill(username)

        password_input = page.get_by_role("textbox", name="Password")
        password_input.click()
        password_input.fill(password)

        # Submit login
        logger.info("Submitting login")
        login_btn = page.get_by_role("button", name="Login")
        login_btn.click()

        # Wait for redirect back to storefront after login
        logger.info("Waiting for login to complete")
        page.wait_for_url("**/shop.sprouts.com/**", timeout=60000)
        page.wait_for_load_state("networkidle", timeout=30000)
        page.wait_for_timeout(3000)

        if debug:
            logger.info("PAUSED: Login complete")
            page.pause()

        # Extract user info
        logger.info("Extracting user info")
        user_name = _extract_user_name(page)
        store_name = _extract_store_name(page)
        shop_id = _extract_shop_id(page)

        # Get all cookies for API calls
        cookies = {c["name"]: c["value"] for c in context.cookies()}

        browser.close()

        return SessionInfo(
            cookies=cookies,
            shop_id=shop_id,
            user_name=user_name,
            store_name=store_name,
        )


def _extract_user_name(page) -> str:
    """Extract user's name from the page."""
    # Try various selectors for user name
    selectors = [
        '[data-testid="user-name"]',
        '.user-name',
        '[class*="greeting"]',
        '[class*="UserName"]',
    ]
    for selector in selectors:
        element = page.locator(selector)
        if element.count() > 0:
            text = element.first.text_content()
            if text:
                return text.strip()

    # Try to find greeting text like "Hi, Name"
    greeting = page.locator('text=/Hi,\\s+\\w+/')
    if greeting.count() > 0:
        text = greeting.first.text_content()
        if text:
            match = re.search(r"Hi,\s+(\w+)", text)
            if match:
                return match.group(1)

    return "Unknown"


def _extract_store_name(page) -> str:
    """Extract store name from the page."""
    selectors = [
        '[data-testid="store-name"]',
        '[class*="store-name"]',
        '[class*="StoreName"]',
        '[class*="location"]',
    ]
    for selector in selectors:
        element = page.locator(selector)
        if element.count() > 0:
            text = element.first.text_content()
            if text:
                return text.strip()
    return "Unknown"


def _extract_shop_id(page) -> str:
    """Extract shop ID from cookies or URL."""
    # Check cookies first
    cookies = page.context.cookies()
    for cookie in cookies:
        if "shop" in cookie["name"].lower() and "id" in cookie["name"].lower():
            return cookie["value"]

    # Check URL for shop ID
    url = page.url
    match = re.search(r"shopId[=:](\d+)", url)
    if match:
        return match.group(1)

    # Default shop ID from example (can be overridden)
    return "473512"


def write_user_info(session: SessionInfo, output_path: str = "USER_INFO.txt") -> None:
    """Write user info to a file."""
    Path(output_path).write_text(f"User Name: {session.user_name}\nDefault Store: {session.store_name}\n")
    logger.info(f"User info written to {output_path}")
