import asyncio

import aiohttp
from aiohttp import ClientTimeout
from bs4 import BeautifulSoup

USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Mobile Safari/537.36"
)

FETCH_TIMEOUT_SECONDS = 30.0


async def fetch_page(url: str, timeout_seconds: float = FETCH_TIMEOUT_SECONDS) -> str:
    headers = {"User-Agent": USER_AGENT}
    timeout = ClientTimeout(total=timeout_seconds)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url, headers=headers) as response:
            response.raise_for_status()
            return await response.text()

def extract_text(html: str, max_links: int = 10) -> dict[str, str | list[str]]:
    soup = BeautifulSoup(html, "html.parser")

    return {
        "title": soup.title.string if soup.title else None,
        "text": soup.get_text(separator="\n", strip=True),  # all visible text
        "links": [a["href"] for a in soup.find_all("a", href=True) if a["href"] is not None and a["href"].startswith("http")][:max_links],
    }


def extract_text_md(html: str) -> str:
    data = extract_text(html)
    title = data["title"] or "Untitled"
    return f"""
# {title}
{data["text"]}

## Links
{"\n".join(data["links"])}
"""


async def fetch_and_extract_text(url: str) -> str:
    html = await fetch_page(url)
    return extract_text_md(html)


async def main():
    url = "https://edition.cnn.com/2026/05/25/world/live-news/iran-war-us-peace-deal"
    html = await fetch_and_extract_text(url)
    with open("/tmp/output.md", "w", encoding="utf-8") as f:
        f.write(html)

asyncio.run(main())