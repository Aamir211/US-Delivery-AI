"""Read-only model for records in data/tickets.json."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


TicketCategory = Literal["Billing", "Bug", "Data Loss", "Feature Request", "How-To", "Integration", "Onboarding", "Performance"]
Urgency = Literal["P1", "P2", "P3", "P4"]
TicketStatus = Literal["Open", "In Progress", "Pending Customer", "Resolved", "Closed"]
PlanTier = Literal["Starter", "Professional", "Business", "Enterprise"]
Channel = Literal["email", "portal", "chat", "phone"]


class Ticket(BaseModel):
    """Validated source ticket. No fields are generated or mutated."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ticket_id: str
    account_id: str
    company: str
    subject: str
    body: str
    product: str
    product_area: str
    category: TicketCategory
    urgency: Urgency
    status: TicketStatus
    plan_tier: PlanTier
    assigned_agent: str
    created_at: datetime
    updated_at: datetime
    tags: list[str] = Field(default_factory=list)
    channel: Channel
    satisfaction_score: int | None = Field(default=None, ge=1, le=5)
