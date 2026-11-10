"""Request/response schemas for the public API."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    full_name: str = Field(min_length=1, max_length=120)

    @field_validator("password")
    @classmethod
    def strong(cls, v: str) -> str:
        if v.isalpha() or v.isdigit():
            raise ValueError("Use a mix of letters and numbers or symbols")
        return v


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    preferred_name: str | None
    roles: list[str]
    is_demo: bool
    onboarding_complete: bool
    preferences: dict
    permissions: list[str] = []


class AuthOut(BaseModel):
    user: UserOut
    access_token: str
    token_type: str = "bearer"


class PreferencesIn(BaseModel):
    theme: str | None = Field(default=None, pattern="^(light|dark|system)$")
    reduced_motion: bool | None = None
    low_power_3d: bool | None = None
    preferred_name: str | None = Field(default=None, max_length=60)


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = None
    page: dict = Field(default_factory=dict)


class ClaimDraftIn(BaseModel):
    category: str
    title: str = Field(min_length=3, max_length=160)
    description: str = Field(min_length=3, max_length=4000)
    incident_date: date
    amount: float | None = Field(default=None, ge=0)


class DecisionIn(BaseModel):
    category: str = "auto"
    repair_estimate: float = Field(gt=0, le=10_000_000)


class ProcedureIn(BaseModel):
    procedure: str = Field(min_length=2, max_length=200)
    provider: str = Field(default="", max_length=200)


class SimulateIn(BaseModel):
    scenario: str = Field(pattern="^(deductible|teen_driver|switch_health_plan)$")
    params: dict = Field(default_factory=dict)


class ExplainIn(BaseModel):
    kind: str = Field(pattern="^(term|coverage|exclusion|endorsement|risk|claim_event)$")
    ref: str | None = None


class DraftIn(BaseModel):
    kind: str
    claim_id: str | None = None
    policy_id: str | None = None


class SendDraftIn(BaseModel):
    to: str = Field(min_length=3, max_length=200)
    subject: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1, max_length=20000)


class ActionEditIn(BaseModel):
    payload_args: dict


class FindingDecisionIn(BaseModel):
    decision: str = Field(pattern="^(ignore|remind)$")
    days: int = Field(default=3, ge=1, le=60)


class ConsentIn(BaseModel):
    granted: bool


class TriageIn(BaseModel):
    incident_type: Literal["collision", "glass", "theft", "vandalism", "weather", "other"]
    vehicle_use: Literal["personal", "commute", "rideshare", "delivery", "racing"] = "personal"
    description: str = Field(min_length=1, max_length=1000)
    incident_date: date
    reported_date: date
    policy_start_date: date
    policy_end_date: date
    amount_claimed: float | None = Field(default=None, ge=0, le=500_000)
    vehicle_value: float = Field(gt=0, le=500_000)
    photos: int = Field(default=0, ge=0, le=50)
    police_report: bool = False
    prior_claims_12mo: int = Field(default=0, ge=0, le=20)

    @model_validator(mode="after")
    def dates_in_order(self) -> "TriageIn":
        if self.reported_date < self.incident_date:
            raise ValueError("The report date can't be before the incident date")
        if self.policy_end_date <= self.policy_start_date:
            raise ValueError("The policy end date must be after its start date")
        return self
