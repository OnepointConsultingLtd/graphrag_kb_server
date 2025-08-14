import asyncio
import httpx

from graphrag_kb_server.config import cfg

API_KEY = cfg.bright_data_mcp_api_token
MCP_ENDPOINT = f"https://mcp.brightdata.com/mcp?token={API_KEY}"


headers = {"Content-Type": "application/json"}


async def init_browser() -> str:
    endpoint = f'{MCP_ENDPOINT}&browser={cfg.browser_zone}'
    payload = {
        "tool": "scraping_browser_navigate",
        "input": {
            "url": "https://www.linkedin.com"
        }
    }
    headers = {
        "Content-Type": "application/json"
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(endpoint, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        session_id = result.get('result', {}).get('session_id')
        return session_id

async def scrape_linkedin_profile(url: str, session_id: str):
    if not url.startswith("https://www.linkedin.com/in/"):
        url = f"https://www.linkedin.com/in/{url}"
    payload = {
        "tool": "web_data_linkedin_person_profile",
        "input": {
            "url": url,
            "session_id": session_id
        },
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(MCP_ENDPOINT, json=payload, headers=headers)
        data = response.json()
        print("Scraped LinkedIn profile data:")
        print(data)
        return data


# Run the async function
if __name__ == "__main__":
    session_id = asyncio.run(init_browser())
    asyncio.run(scrape_linkedin_profile("linda-lam-21470213", session_id))
