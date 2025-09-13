from typing import Optional

import aiohttp
from aiohttp import ClientTimeout
from bs4 import BeautifulSoup

SEED_URL = "https://www.linkedin.com/uas/login"
LOGIN_URL = "https://www.linkedin.com/checkpoint/lg/login-submit"
VERIFY_URL = "https://www.linkedin.com/checkpoint/challenge/verify"

DEFAULT_HEADERS = {
    # LinkedIn is picky about UA headers; a realistic UA reduces instant blocks.
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


async def fetch_text(session: aiohttp.ClientSession, url: str) -> str:
    async with session.get(url, headers=DEFAULT_HEADERS, allow_redirects=True) as resp:
        resp.raise_for_status()
        return await resp.text()


async def post_form(
    session: aiohttp.ClientSession,
    url: str,
    data: dict,
) -> str:
    async with session.post(
        url,
        data=data,
        headers=DEFAULT_HEADERS,
        allow_redirects=True,
    ) as resp:
        resp.raise_for_status()
        return await resp.text()


def extract_input_value(soup: BeautifulSoup, name: str) -> Optional[str]:
    tag = soup.find("input", {"name": name})
    return tag["value"] if tag and tag.has_attr("value") else None


async def verify_pin(soup: BeautifulSoup, session: aiohttp.ClientSession) -> None:
    """
    Placeholder: your original code calls verify_pin(soup).
    Implement whatever challenge-handling you need here:
    - find the PIN input name
    - prompt user / fetch code from email/SMS
    - POST to VERIFY_URL
    """
    pin = input("Check the PIN in your inbox and enter here:\n")
    payload = {
        "csrfToken": soup.find("input", {"name": "csrfToken"})["value"],
        "pageInstance": soup.find("input", {"name": "pageInstance"})["value"],
        "resendUrl": soup.find("input", {"name": "resendUrl"})["value"],
        "challengeId": soup.find("input", {"name": "challengeId"})["value"],
        "language": "en-US",
        "displayTime": soup.find("input", {"name": "displayTime"})["value"],
        "challengeSource": soup.find("input", {"name": "challengeSource"})["value"],
        "requestSubmissionId": soup.find("input", {"name": "requestSubmissionId"})[
            "value"
        ],
        "challengeType": soup.find("input", {"name": "challengeType"})["value"],
        "challengeData": soup.find("input", {"name": "challengeData"})["value"],
        "challengeDetails": soup.find("input", {"name": "challengeDetails"})["value"],
        "failureRedirectUri": soup.find("input", {"name": "failureRedirectUri"})[
            "value"
        ],
        "pin": pin,
    }
    await session.post(VERIFY_URL, data=payload)


async def login(email: str, password: str) -> None:
    timeout = ClientTimeout(total=30)
    # CookieJar(unsafe=True) allows non-RFC domains like '.linkedin.com' wildcards if needed.
    cookie_jar = aiohttp.CookieJar(unsafe=True)

    async with aiohttp.ClientSession(timeout=timeout, cookie_jar=cookie_jar) as session:
        # 1) Load login page to get CSRF/token values
        seed_html = await fetch_text(session, SEED_URL)
        soup = BeautifulSoup(seed_html, "html.parser")

        login_csrf = extract_input_value(soup, "loginCsrfParam")
        if not login_csrf:
            raise RuntimeError("Could not find loginCsrfParam on the login page.")

        # 2) Build payload and submit
        payload = {
            "session_key": email,
            "session_password": password,
            "loginCsrfParam": login_csrf,
        }

        login_html = await post_form(session, LOGIN_URL, data=payload)
        login_soup = BeautifulSoup(login_html, "html.parser")

        # 3) Continue to whatever verification your flow needs
        await verify_pin(login_soup, session)


# Example usage:
# asyncio.run(login("you@example.com", "your-password"))

if __name__ == "__main__":
    import asyncio

    user_name = input("Enter your LinkedIn email: ")
    password = input("Enter your LinkedIn password: ")
    asyncio.run(login(user_name, password))
