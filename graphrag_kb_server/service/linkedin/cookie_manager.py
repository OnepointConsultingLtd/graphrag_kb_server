from pathlib import Path
import json

from linkedin_scraper.person import By

from graphrag_kb_server.config import cfg
from graphrag_kb_server.logger import logger

from selenium import webdriver

# Cookie management directory
COOKIES_DIR = Path(cfg.config_dir) / "linkedin_cookies"
COOKIES_DIR.mkdir(exist_ok=True, parents=True)


def get_cookies_file(user: str) -> Path:
    """Get the path to the cookies file for a specific user."""
    # Use a hash of the username to avoid issues with special characters
    import hashlib

    user_hash = hashlib.md5(user.encode()).hexdigest()
    return COOKIES_DIR / f"cookies_{user_hash}.json"


def save_cookies(driver: webdriver.Chrome, user: str) -> None:
    """
    Save browser cookies to a file for future use.

    Args:
        driver: Selenium WebDriver instance with active session
        user: LinkedIn username/email associated with the cookies
    """
    try:
        cookies = driver.get_cookies()
        cookies_file = get_cookies_file(user)
        with open(cookies_file, "w") as f:
            json.dump(cookies, f, indent=2)
        logger.info(f"Saved {len(cookies)} cookies for user {user} to {cookies_file}")
    except Exception as e:
        logger.error(f"Failed to save cookies for user {user}: {e}")


def load_cookies(driver: webdriver.Chrome, user: str) -> bool:
    """
    Load previously saved cookies into the browser.

    Args:
        driver: Selenium WebDriver instance
        user: LinkedIn username/email to load cookies for

    Returns:
        True if cookies were loaded successfully, False otherwise
    """
    try:
        cookies_file = get_cookies_file(user)
        if not cookies_file.exists():
            logger.info(f"No saved cookies found for user {user}")
            return False

        # First navigate to LinkedIn to set the domain for cookies
        driver.get("https://www.linkedin.com")

        with open(cookies_file, "r") as f:
            cookies = json.load(f)

        for cookie in cookies:
            # Remove keys that can cause issues when adding cookies
            cookie.pop("sameSite", None)
            cookie.pop("expiry", None)
            try:
                driver.add_cookie(cookie)
            except Exception as e:
                logger.warning(
                    f"Failed to add cookie {cookie.get('name', 'unknown')}: {e}"
                )

        logger.info(f"Loaded {len(cookies)} cookies for user {user}")

        # Refresh to apply cookies
        driver.refresh()

        # Verify if we're logged in by checking for feed or profile link
        try:
            driver.implicitly_wait(5)
            # Check if we can find elements that indicate we're logged in
            driver.find_element(By.CSS_SELECTOR, "a[href*='/feed/']")
            logger.info("Successfully authenticated using saved cookies")
            return True
        except Exception as e:
            logger.warning(
                f"Cookies loaded but authentication failed, may need to login again: {e}"
            )
            return False

    except Exception as e:
        logger.error(f"Failed to load cookies for user {user}: {e}")
        return False


def login_with_cookies(
    driver: webdriver.Chrome, user: str, password: str, force_login: bool = False
) -> None:
    """
    Login to LinkedIn, using saved cookies if available.

    Args:
        driver: Selenium WebDriver instance
        user: LinkedIn username/email
        password: LinkedIn password
        force_login: If True, skip cookie loading and force a fresh login
    """
    if not force_login:
        # Try to use saved cookies first
        if load_cookies(driver, user):
            logger.info("Logged in using saved cookies")
            return
        logger.info(
            "Cookie authentication failed, proceeding with username/password login"
        )

    from linkedin_scraper import actions

    # Fall back to regular login
    actions.login(driver, user, password)
    logger.info("Logged in using username and password")

    # Save cookies for next time
    save_cookies(driver, user)
