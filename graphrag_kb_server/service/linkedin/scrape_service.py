import os
import json
from pathlib import Path

from linkedin_scraper import Person
from asyncer import asyncify

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By

from graphrag_kb_server.model.linkedin.profile import (
    Profile,
    Experience,
    Company,
    Education,
)
from graphrag_kb_server.config import linkedin_cfg, cfg
from graphrag_kb_server.service.linkedin.linkedin_functions import correct_linkedin_url
from graphrag_kb_server.service.db.db_persistence_profile import (
    select_profile,
    insert_profile,
)
from graphrag_kb_server.logger import logger
from graphrag_kb_server.utils.date_support import convert_linkedin_date
from graphrag_kb_server.utils.cache import GenericSimpleCache


# Cookie management directory
COOKIES_DIR = Path(cfg.config_dir) / "linkedin_cookies"
COOKIES_DIR.mkdir(exist_ok=True, parents=True)


_cache = GenericSimpleCache[str, Profile](timeout=60 * 60 * 4)  # 4 hours


def _get_cookies_file(user: str) -> Path:
    """Get the path to the cookies file for a specific user."""
    # Use a hash of the username to avoid issues with special characters
    import hashlib

    user_hash = hashlib.md5(user.encode()).hexdigest()
    return COOKIES_DIR / f"cookies_{user_hash}.json"


def _save_cookies(driver: webdriver.Chrome, user: str) -> None:
    """
    Save browser cookies to a file for future use.

    Args:
        driver: Selenium WebDriver instance with active session
        user: LinkedIn username/email associated with the cookies
    """
    try:
        cookies = driver.get_cookies()
        cookies_file = _get_cookies_file(user)
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
        cookies_file = _get_cookies_file(user)
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
    _save_cookies(driver, user)


class SafePerson(Person):
    def __init__(
        self,
        linkedin_url: str,
        driver: webdriver.Chrome,
        extract_educations: bool = True,
        extract_experiences_from_homepage: bool = True,
    ):
        self.headline = ""
        self.extract_educations = extract_educations
        self.extract_experiences_from_homepage = extract_experiences_from_homepage
        super().__init__(linkedin_url, driver=driver)

    def get_name_and_location(self):
        top_panel = self.driver.find_element(By.XPATH, "//*[@class='mt2 relative']")
        self.name = top_panel.find_element(By.TAG_NAME, "h1").text
        self.location = top_panel.find_element(
            By.XPATH, "//*[@class='text-body-small inline t-black--light break-words']"
        ).text
        self.headline = top_panel.find_element(
            By.CSS_SELECTOR, ".ph5 .text-body-medium.break-words"
        ).text

    def scrape_logged_in(self, close_on_complete=True):
        driver = self.driver

        self.focus()
        self.wait(5)

        # get name and location
        self.get_name_and_location()

        # get about
        self.get_about()
        driver.execute_script(
            "window.scrollTo(0, Math.ceil(document.body.scrollHeight/2));"
        )

        # get experience
        if self.extract_experiences_from_homepage:
            self.get_homepage_experiences()
        else:
            self.get_experiences()

        # get education
        if self.extract_educations:
            self.get_educations()

        driver.get(self.linkedin_url)

        if close_on_complete:
            driver.quit()

    def _extract_multiple_positions(self, position: WebElement) -> list[WebElement]:
        position_elements = position.find_elements(By.XPATH, "*")
        company_logo_elem = position_elements[0] if len(position_elements) > 0 else None
        position_details = position_elements[1] if len(position_elements) > 1 else None
        return company_logo_elem, position_details

    def _extract_experience(self, position: WebElement) -> Experience | None:
        try:
            position = position.find_element(
                By.CSS_SELECTOR, "div[data-view-name='profile-component-entity']"
            )
            company_logo_elem, position_details = self._extract_multiple_positions(
                position
            )
            if not company_logo_elem or not position_details:
                return None

            # company elem
            company_linkedin_url = company_logo_elem.find_element(
                By.XPATH, "*"
            ).get_attribute("href")
            if not company_linkedin_url:
                return None

            # position details
            position_details_list = position_details.find_elements(By.XPATH, "*")
            position_summary_details = (
                position_details_list[0] if len(position_details_list) > 0 else None
            )
            position_summary_text = (
                position_details_list[1] if len(position_details_list) > 1 else None
            )
            outer_positions = position_summary_details.find_element(
                By.XPATH, "*"
            ).find_elements(By.XPATH, "*")

            if len(outer_positions) == 4:
                position_title = (
                    outer_positions[0].find_element(By.TAG_NAME, "span").text
                )
                company = outer_positions[1].find_element(By.TAG_NAME, "span").text
                work_times = outer_positions[2].find_element(By.TAG_NAME, "span").text
                location = outer_positions[3].find_element(By.TAG_NAME, "span").text
            elif len(outer_positions) == 3:
                if "·" in outer_positions[2].text:
                    position_title = (
                        outer_positions[0].find_element(By.TAG_NAME, "span").text
                    )
                    company = outer_positions[1].find_element(By.TAG_NAME, "span").text
                    work_times = (
                        outer_positions[2].find_element(By.TAG_NAME, "span").text
                    )
                    location = ""
                else:
                    position_title = ""
                    company = outer_positions[0].find_element(By.TAG_NAME, "span").text
                    work_times = (
                        outer_positions[1].find_element(By.TAG_NAME, "span").text
                    )
                    location = outer_positions[2].find_element(By.TAG_NAME, "span").text
            else:
                position_title = ""
                company = outer_positions[0].find_element(By.TAG_NAME, "span").text
                work_times = ""
                location = ""

            times = work_times.split("·")[0].strip() if work_times else ""
            duration = (
                work_times.split("·")[1].strip()
                if len(work_times.split("·")) > 1
                else None
            )

            from_date = " ".join(times.split(" ")[:2]) if times else ""
            to_date = " ".join(times.split(" ")[3:]) if times else ""
            if position_summary_text and any(
                element.get_attribute("pvs-list__container")
                for element in position_summary_text.find_elements(By.TAG_NAME, "*")
            ):
                inner_positions = (
                    position_summary_text.find_element(
                        By.CLASS_NAME, "pvs-list__container"
                    )
                    .find_element(By.XPATH, "*")
                    .find_element(By.XPATH, "*")
                    .find_element(By.XPATH, "*")
                    .find_elements(By.CLASS_NAME, "pvs-list__paged-list-item")
                )
            else:
                inner_positions = []
            if len(inner_positions) > 1:
                descriptions = inner_positions
                for description in descriptions:
                    res = description.find_element(By.TAG_NAME, "a").find_elements(
                        By.XPATH, "*"
                    )
                    position_title_elem = res[0] if len(res) > 0 else None
                    work_times_elem = res[1] if len(res) > 1 else None
                    location_elem = res[2] if len(res) > 2 else None

                    location = (
                        location_elem.find_element(By.XPATH, "*").text
                        if location_elem
                        else None
                    )
                    position_title = (
                        position_title_elem.find_element(By.XPATH, "*")
                        .find_element(By.TAG_NAME, "*")
                        .text
                        if position_title_elem
                        else ""
                    )
                    work_times = (
                        work_times_elem.find_element(By.XPATH, "*").text
                        if work_times_elem
                        else ""
                    )
                    times = work_times.split("·")[0].strip() if work_times else ""
                    duration = (
                        work_times.split("·")[1].strip()
                        if len(work_times.split("·")) > 1
                        else None
                    )
                    from_date = " ".join(times.split(" ")[:2]) if times else ""
                    to_date = " ".join(times.split(" ")[3:]) if times else ""

                    experience = Experience(
                        position_title=position_title,
                        start=convert_linkedin_date(from_date),
                        end=convert_linkedin_date(to_date),
                        duration=duration,
                        location=location,
                        description=description,
                        company=Company(
                            name=company, linkedin_url=company_linkedin_url
                        ),
                    )
                    return experience
            else:
                description = (
                    position_summary_text.text if position_summary_text else ""
                )

                experience = Experience(
                    position_title=position_title,
                    start=convert_linkedin_date(from_date),
                    end=convert_linkedin_date(to_date),
                    duration=duration,
                    location=location,
                    description=description,
                    company=Company(name=company, linkedin_url=company_linkedin_url),
                )
                return experience
        except Exception as e:
            logger.error(f"Error extracting experience: {e}")
            return None

    def _extract_experiences_from_parent(
        self, parent: WebElement, loop_class_name: str = "pvs-list__paged-list-item"
    ):
        for position in parent.find_elements(By.CLASS_NAME, loop_class_name):
            experience = self._extract_experience(position)
            if experience:
                self.experiences.append(experience)

    def get_experiences(self):
        try:
            url = os.path.join(self.linkedin_url, "details/experience")
            self.driver.get(url)
            self.focus()
            main = self.wait_for_element_to_load(by=By.TAG_NAME, name="main")
            self.scroll_to_half()
            self.scroll_to_bottom()
            main_list = self.wait_for_element_to_load(
                name="pvs-list__container", base=main
            )
            self._extract_experiences_from_parent(main_list)

        except Exception as e:
            logger.error(f"Error getting experiences: {e}")
        return self.experiences

    def get_homepage_experiences(self):
        experience_main = self.wait_for_element_to_load(by=By.ID, name="experience")
        experience_siblings = experience_main.parent.find_elements(
            By.CSS_SELECTOR, "#experience ~ div"
        )
        if len(experience_siblings) > 1:
            experience_parent = experience_siblings[1]
            self._extract_experiences_from_parent(
                experience_parent, "artdeco-list__item"
            )

    def get_educations(self):
        try:
            url = os.path.join(self.linkedin_url, "details/education")
            self.driver.get(url)
            self.focus()
            main = self.wait_for_element_to_load(by=By.TAG_NAME, name="main")
            self.scroll_to_half()
            self.scroll_to_bottom()
            main_list = self.wait_for_element_to_load(
                name="pvs-list__container", base=main
            )
            for position in main_list.find_elements(
                By.CLASS_NAME, "pvs-list__paged-list-item"
            ):
                position = position.find_element(
                    By.XPATH, "//div[@data-view-name='profile-component-entity']"
                )
                institution_logo_elem, position_details = (
                    self._extract_multiple_positions(position)
                )
                if not institution_logo_elem or not position_details:
                    continue

                # company elem
                institution_linkedin_url = institution_logo_elem.find_element(
                    By.XPATH, "*"
                ).get_attribute("href")

                # position details
                position_details_list = position_details.find_elements(By.XPATH, "*")
                position_summary_details = (
                    position_details_list[0] if len(position_details_list) > 0 else None
                )
                position_summary_text = (
                    position_details_list[1] if len(position_details_list) > 1 else None
                )
                outer_positions = position_summary_details.find_element(
                    By.XPATH, "*"
                ).find_elements(By.XPATH, "*")

                institution_name = (
                    outer_positions[0].find_element(By.TAG_NAME, "span").text
                )
                if len(outer_positions) > 1:
                    degree = outer_positions[1].find_element(By.TAG_NAME, "span").text
                else:
                    degree = None

                if len(outer_positions) > 2:
                    times = outer_positions[2].find_element(By.TAG_NAME, "span").text

                    if times != "":
                        from_date = (
                            times.split(" ")[times.split(" ").index("-") - 1]
                            if len(times.split(" ")) > 3
                            else times.split(" ")[0]
                        )
                        to_date = times.split(" ")[-1]
                else:
                    from_date = None
                    to_date = None

                description = (
                    position_summary_text.text if position_summary_text else ""
                )

                education = Education(
                    start=convert_linkedin_date(from_date),
                    end=convert_linkedin_date(to_date),
                    description=description,
                    degree=degree,
                    institution_name=institution_name,
                    linkedin_url=institution_linkedin_url,
                )
                self.add_education(education)
        except Exception as e:
            logger.error(f"Error getting educations: {e}")
            return []


def _convert_to_profile(person: SafePerson | None) -> Profile | None:
    if not person:
        return None
    names = person.name.split(" ")
    if len(names) == 0:
        return None
    if len(names) == 1:
        surname = ""
    else:
        surname = names[1]
    return Profile(
        given_name=names[0],
        surname=surname,
        email="",
        cv=person.about if person.about else "",
        industry_name=person.headline,
        geo_location=person.location,
        linkedin_profile_url=person.linkedin_url,
        experiences=person.experiences,
        educations=person.educations,
    )


async def aextract_profile(
    profile: str,
    force_login: bool = False,
    extract_educations: bool = False,
    extract_experiences_from_homepage: bool = False,
    project_dir: Path = None,
) -> Profile | None:
    if project_dir is not None:
        if profile_data := await select_profile(
            project_dir, correct_linkedin_url(profile)
        ):
            return profile_data
    else:
        if profile_data := _cache.get(profile):
            return profile_data
    profile_data = await asyncify(extract_profile)(
        profile, force_login, extract_educations, extract_experiences_from_homepage
    )
    if project_dir is not None and profile_data is not None:
        await insert_profile(project_dir, profile_data)
    else:
        _cache.set(profile, profile_data)
    return profile_data


def _create_driver() -> webdriver.Chrome:  #
    # Configure Chrome options
    options = Options()
    options.add_argument("--headless=new")  # 'new' mode for Chrome >= 109
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )


def extract_profile(
    profile: str,
    force_login: bool = False,
    extract_educations: bool = False,
    extract_experiences_from_homepage: bool = False,
) -> Profile | None:
    """
    Extract a LinkedIn profile using web scraping with Selenium.

    Args:
        profile: LinkedIn profile URL or username
        force_login: If True, skip cookie loading and force a fresh login
        extract_educations: If True, extract educations
        extract_experiences_from_homepage: If True, extract experiences from the homepage
    Returns:
        Profile object if successful, None otherwise
    """
    driver = _create_driver()
    logger.info(f"Extracting profile: {profile}")
    user, password = linkedin_cfg.get_random_credential()

    # Use cookie-based login (will fall back to regular login if cookies don't work)
    login_with_cookies(driver, user, password, force_login=force_login)
    logger.info("Logged in to LinkedIn")

    profile = correct_linkedin_url(profile)
    logger.info(f"Corrected LinkedIn URL: {profile}")
    person = SafePerson(
        profile,
        driver=driver,
        extract_educations=extract_educations,
        extract_experiences_from_homepage=extract_experiences_from_homepage,
    )
    logger.info(f"Extracted profile: {person}")
    return _convert_to_profile(person)
