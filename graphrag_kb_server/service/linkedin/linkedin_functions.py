def correct_linkedin_url(url: str) -> str:
    if not url.startswith("https://www.linkedin.com/in/"):
        url = f"https://www.linkedin.com/in/{url}"
    return url
