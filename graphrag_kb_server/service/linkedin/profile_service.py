from pathlib import Path
import json
import datetime
import random

from linkedin_api import Linkedin
from linkedin_api.cookie_repository import LinkedinSessionExpired

from graphrag_kb_server.config import linkedin_cfg
from graphrag_kb_server.model.linkedin.profile import (
    Profile,
    Experience,
    Company,
    Skill,
)
from graphrag_kb_server.logger import logger
from graphrag_kb_server.utils.cache import GenericSimpleCache


_cache = GenericSimpleCache[str, dict](timeout=60 * 60 * 1)  # 1 hour


def _extract_profile_dict(profile: str) -> dict | None:
    profile_dict = _cache.get(profile)
    if profile_dict is not None:
        return profile_dict
    cred_index = random.randint(0, len(linkedin_cfg.linkedin_credentials_list) - 1)
    user, password = linkedin_cfg.linkedin_credentials_list[cred_index]
    try:
        api = Linkedin(user, password, debug=True)
    except LinkedinSessionExpired:
        try:
            logger.warning(f"Linkedin session expired for {user}, refreshing cookies")
            api = Linkedin(user, password, refresh_cookies=True)
        except Exception as e:
            logger.error(f"Error refreshing cookies for {user}: {e}")
            return None
    except Exception as e:
        logger.error(f"Error extracting profile {profile}: {e}")
        return None
    profile_dict = api.get_profile(profile)
    if profile_dict is None:
        return None
    _cache.set(profile, profile_dict)
    return profile_dict


def profile_to_file(profile: str, target: Path) -> Path:
    profile_data = _extract_profile_dict(profile)
    target.write_text(json.dumps(profile_data), encoding="utf-8")
    return target


def extract_profile(profile: str) -> Profile | None:
    profile_data: dict = _extract_profile_dict(profile)
    if profile_data is None or len(profile_data) == 0:
        return None
    # industries: list[Industry] = []
    # companies: list[Company] = []
    skills: list[Skill] = []
    experiences: list[Experience] = []
    photo_200: str | None = None
    photo_400: str | None = None
    if "displayPictureUrl" in profile_data:
        if "img_200_200" in profile_data:
            photo_200 = (
                f"{profile_data["displayPictureUrl"]}{profile_data["img_200_200"]}"
            )
        if "img_400_400" in profile_data:
            photo_400 = (
                f"{profile_data["displayPictureUrl"]}{profile_data["img_400_400"]}"
            )
    cv = profile_data.get("summary", "")
    given_name = profile_data.get("firstName", "Unknown")
    surname = profile_data.get("lastName", "Unknown")
    email = f"{profile}@linkedin.com"
    industry_name: str = profile_data.get("industryName", "")
    geo_location: str = profile_data.get("geoLocationName", "")
    linkedin_profile_url = f"https://www.linkedin.com/in/{profile}"
    for experience in profile_data.get("experience", []):
        add_experience(experiences, experience)
    for skill in profile_data.get("skills", []):
        if "name" in skill:
            skills.append(Skill(name=skill["name"]))
    return Profile(
        given_name=given_name,
        surname=surname,
        email=email,
        cv=cv,
        industry_name=industry_name,
        geo_location=geo_location,
        linkedin_profile_url=linkedin_profile_url,
        experiences=experiences,
        skills=skills,
        photo_200=photo_200,
        photo_400=photo_400,
    )


def add_experience(experiences, experience):
    location = experience.get("locationName", "")
    if "timePeriod" in experience:
        time_period = experience["timePeriod"]
        if "startDate" in time_period:
            start_date = time_period["startDate"]
            start_date_month = int(start_date.get("month", "1"))
            start_date_year = int(start_date["year"]) if start_date["year"] else 1
            start_date = datetime.datetime(start_date_year, start_date_month, 1)
            end_date = None
            if "endDate" in time_period:
                end_date = time_period["endDate"]
                end_date_month = int(end_date.get("month", "12"))
                if "year" in end_date:
                    end_date_year = int(end_date["year"])
                    end_date = datetime.datetime(end_date_year, end_date_month, 1)
            company_name = experience["companyName"] or ""
            title = experience.get("title", "")
            company: Company = Company(name=company_name)
            experience: Experience = Experience(
                location=location,
                title=title,
                start=start_date,
                end=end_date,
                company=company,
            )
            experiences.append(experience)


if __name__ == "__main__":
    # profile_name = "alexander-polev-cto"
    profile_name = "allanschweitz"
    # profile_name = "suresh-sharma-60336159"
    # profile_name = "gil-fernandes-consultant1"
    output_file = Path(f"{profile_name}-consultant.json")
    consultant = extract_profile(profile_name)
    if consultant is not None:
        output_file.write_text(consultant.model_dump_json(), encoding="utf-8")
    else:
        logger.error(f"Error extracting profile {profile_name}")
