"""Read-only model for records in data/accounts.json."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.ticket import PlanTier


HealthStatus = Literal["Healthy", "At Risk", "Churning", "New"]
UsageTrend = Literal["Increasing", "Stable", "Declining", "Inactive"]


class PrimaryContact(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    title: str


class Account(BaseModel):
    """Validated source account. No fields are generated or mutated."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    account_id: str
    company: str
    tam: str
    plan_tier: PlanTier
    arr_usd: int = Field(ge=0)
    seats_licensed: int = Field(ge=0)
    seats_active: int = Field(ge=0)
    products: list[str]
    health_status: HealthStatus
    usage_trend: UsageTrend
    open_tickets: int = Field(ge=0)
    p1_tickets_last_30d: int = Field(ge=0)
    customer_since: date
    renewal_date: date
    last_qbr_date: date
    primary_contact: PrimaryContact
    escalation_notes: list[str]
    nps_score: int | None = Field(default=None, ge=1, le=10)
    last_login_days_ago: int = Field(ge=0)
    integrations_active: list[str]
    region: str
    industry: str
