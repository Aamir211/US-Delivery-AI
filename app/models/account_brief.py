"""Structured contracts for Task 2 TAM account briefs."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RiskFlag(BaseModel):
    model_config = ConfigDict(extra="forbid")

    flag_type: Literal["Open Support Risk", "Escalation Signal", "Churn Risk"]
    explanation: str = Field(min_length=1)
    ticket_id: str | None = None
    ticket_quote: str | None = None
    account_evidence: str | None = None

    @model_validator(mode="after")
    def ticket_evidence_is_complete(self) -> "RiskFlag":
        if (self.ticket_id is None) != (self.ticket_quote is None):
            raise ValueError("Ticket-based flags require both ticket_id and ticket_quote")
        return self


class RiskSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    statement: str = Field(min_length=1)
    flags: list[RiskFlag] = Field(default_factory=list)


class AccountBrief(BaseModel):
    """Exactly three public sections required by the Task 2 brief."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    executive_summary: list[str] = Field(min_length=3, max_length=5, serialization_alias="Executive Summary")
    open_risks_and_flagged_issues: RiskSection = Field(serialization_alias="Open Risks & Flagged Issues")
    recommended_talking_points: list[str] = Field(min_length=1, serialization_alias="Recommended Talking Points")
