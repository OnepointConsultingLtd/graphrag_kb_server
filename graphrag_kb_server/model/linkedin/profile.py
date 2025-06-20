import datetime

from typing import Optional

from pydantic import BaseModel, Field


class Skill(BaseModel):
    name: str = Field(..., description="The name of the skill")


class Industry(BaseModel):
    name: str = Field(..., description="The name of the industry")


class Company(BaseModel):
    name: str = Field(..., description="The name of the company")
    industries: Optional[list[Industry]] = Field(
        None, description="The industries of the company"
    )


class Experience(BaseModel):
    location: str = Field(..., description="The name of the location")
    title: str = Field(..., description="The job title")
    start: Optional[datetime.datetime] = Field(
        None, description="The start of the employment"
    )
    end: Optional[datetime.datetime] = Field(
        None, description="The end of the employment"
    )
    company: Company = Field(
        ..., description="The company in which the consultant worked"
    )

    def __str__(self) -> str:
        return f"""Company: {self.title}
Location: {self.location}
Company: {self.company.name if self.company.name else "No company found"} ({", ".join([industry.name for industry in self.company.industries]) if self.company.industries else "No industries found"})
Start: {self.start}
End: {self.end}

"""


class Profile(BaseModel):
    given_name: str = Field(..., description="The given name of the consultant")
    surname: str = Field(..., description="The surname of the consultant")
    email: str = Field(..., description="The email of the consultant")
    cv: str = Field(..., description="The curriculum vitae of the consultant")
    summary: str = Field(default="", description="The summary of the consultant")
    industry_name: str = Field(
        ..., description="The industry in which the consultant is working"
    )
    geo_location: str = Field(
        ..., description="The geographical location of the consultant"
    )
    linkedin_profile_url: str = Field(..., description="The linkedin profile")
    experiences: list[Experience] = Field(
        ..., description="The experiences of this user"
    )
    skills: list[Skill] = Field(..., description="The list of skills")
    photo_200: str | None = Field(
        default=None, description="The 200x200 photo of the consultant"
    )
    photo_400: str | None = Field(
        default=None, description="The 400x400 photo of the consultant"
    )

    def __str__(self) -> str:
        return f"""{self.given_name} {self.surname}
Email: {self.email}
Industry: {self.industry_name}
Location: {self.geo_location}
LinkedIn: {self.linkedin_profile_url}

{self.cv}

Skills:
{"\n- ".join([skill.name for skill in self.skills]) if self.skills else "No skills found"}

Experiences:
{"\n- ".join([str(experience) for experience in self.experiences]) if self.experiences else "No experiences found"}
"""
