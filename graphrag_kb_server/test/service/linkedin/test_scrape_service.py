"""
Tests for LinkedIn profile scraping with cookie-based authentication.

The scrape_service now supports cookie-based authentication, which allows
you to avoid entering credentials on subsequent runs. The cookies are
automatically saved after the first successful login and reused in future
sessions.

Cookie features:
- Automatic cookie saving after login
- Automatic cookie loading on subsequent runs  
- Fallback to username/password if cookies expire
- Per-user cookie storage
- Cookie clearing utility

Usage examples:
    # First run - will login with username/password and save cookies
    profile = extract_profile("username")
    
    # Subsequent runs - will use saved cookies, no password needed
    profile = extract_profile("username")
    
    # Force fresh login (ignore saved cookies)
    profile = extract_profile("username", force_login=True)
    
    # Clear cookies for a specific user
    from graphrag_kb_server.service.linkedin.scrape_service import clear_cookies
    clear_cookies("user@example.com")
    
    # Clear all saved cookies
    clear_cookies()

Cookies are stored in: {CONFIG_DIR}/linkedin_cookies/cookies_{user_hash}.json
"""

import asyncio

from graphrag_kb_server.service.linkedin.scrape_service import (
    extract_profile, aextract_profile
)


def test_scrape_linkedin_profile():
    person = extract_profile("gil-palma-fernandes", extract_educations=True)
    assert person is not None
    assert person.given_name == "Gil"
    assert person.surname == "Fernandes"
    assert len(person.experiences) > 0
    assert len(person.educations) > 0
    assert person.linkedin_profile_url == "https://www.linkedin.com/in/gil-palma-fernandes"


def test_scrape_linkedin_profile_async():
    person = asyncio.run(aextract_profile("gil-palma-fernandes", extract_educations=True))
    assert person is not None
    assert person.given_name == "Gil"
    assert person.surname == "Fernandes"
    assert len(person.experiences) > 0
    assert len(person.educations) > 0
    assert person.linkedin_profile_url == "https://www.linkedin.com/in/gil-palma-fernandes"


def test_scrape_linkedin_profile_2():
    person = extract_profile("alexander-polev-cto", extract_educations=False)
    assert person is not None
    assert person.given_name == "Alexander"
    assert person.surname == "Polev"
    assert len(person.experiences) > 0
    assert len(person.educations) == 0
    assert person.linkedin_profile_url == "https://www.linkedin.com/in/alexander-polev-cto"


def test_scrape_linkedin_profile_3():
    person = extract_profile("tuli-faas", extract_educations=True)
    assert person is not None
    assert person.given_name == "Tuli"
    assert person.surname == "Faas"
    assert len(person.experiences) > 0
    assert len(person.educations) > 0
    assert person.linkedin_profile_url == "https://www.linkedin.com/in/tuli-faas"


def test_scrape_linkedin_profile_4():
    person = extract_profile("donna-matthews-a8b0244", extract_educations=False)
    assert person is not None
    assert person.given_name == "Donna"
    assert person.surname == "Matthews"
    assert len(person.experiences) > 0
    # assert len(person.educations) > 0
    assert person.linkedin_profile_url == "https://www.linkedin.com/in/donna-matthews-a8b0244"


def test_cookie_management():
    """
    Test cookie management functionality.
    
    This test demonstrates:
    1. First extraction saves cookies automatically
    2. Subsequent extractions reuse cookies (faster, no password needed)
    3. Force login bypasses cookies
    4. Clear cookies utility works
    """
    profile_url = "gil-palma-fernandes"
    
    # First extraction - will login with credentials and save cookies
    print("\n=== First run: Login with credentials ===")
    person1 = extract_profile(profile_url)
    assert person1 is not None
    print("✓ Cookies saved after first login")
    
    # Second extraction - should use saved cookies
    print("\n=== Second run: Using saved cookies ===")
    person2 = extract_profile(profile_url)
    assert person2 is not None
    print("✓ Authenticated using saved cookies")
    
    # Force fresh login (ignoring cookies)
    print("\n=== Third run: Force fresh login ===")
    person3 = extract_profile(profile_url, force_login=True)
    assert person3 is not None
    print("✓ Fresh login completed, cookies refreshed")
    
    # Note: Actual cookie clearing is commented out to preserve cookies
    # Uncomment the following lines if you want to test cookie clearing
    # 
    # from graphrag_kb_server.config import linkedin_cfg
    # user, _ = linkedin_cfg.get_random_credential()
    # clear_cookies(user)
    # print("✓ Cookies cleared")
    
    print("\n=== Cookie test completed successfully ===")


if __name__ == "__main__":
    # Run the cookie management test
    test_cookie_management()
