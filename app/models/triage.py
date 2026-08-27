"""Structured contracts for Task 1 ticket triage."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.ticket import TicketCategory, Urgency


ProductArea = Literal["API", "Actions", "Alerts", "Audit Logs", "Authentication", "Bandwidth Limits", "Conflict Resolution", "Connectors", "Dashboard", "Data Ingestion", "Data Sources", "Encryption", "Error Handling", "Exports", "File Sync", "Integrations", "Key Management", "Permissions", "Pipeline Monitoring", "Reports", "SSO", "Scheduling", "Schema Management", "Templates", "Triggers"]


class TicketInput(BaseModel):
    """A raw ticket received as JSON or normalised from plain text."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    subject: str = ""
    body: str = ""

    @model_validator(mode="after")
    def has_ticket_content(self) -> "TicketInput":
        if not self.subject and not self.body:
            raise ValueError("At least one of subject or body must be non-empty")
        return self

    @property
    def combined_text(self) -> str:
        return "\n\n".join(part for part in (self.subject, self.body) if part)


class TriageResult(BaseModel):
    """Validated public output for the Task 1 triage contract."""

    model_config = ConfigDict(extra="forbid")

    product_area: ProductArea
    issue_category: TicketCategory
    urgency: Urgency
    reasoning: str = Field(min_length=1)
    known_issue_match: bool
    relevant_knowledge_base_document: str | None = None
    recommended_responder_team: str = Field(min_length=1)
    draft_first_response: str = Field(min_length=1)

    @field_validator("relevant_knowledge_base_document")
    @classmethod
    def document_path_is_local(cls, value: str | None) -> str | None:
        if value is not None and not value.startswith("knowledge-base/"):
            raise ValueError("Knowledge-base document must use a local knowledge-base path")
        return value

    @model_validator(mode="after")
    def knowledge_base_fields_are_consistent(self) -> "TriageResult":
        if self.known_issue_match and self.relevant_knowledge_base_document is None:
            raise ValueError("A known issue match requires a local document path")
        if not self.known_issue_match and self.relevant_knowledge_base_document is not None:
            raise ValueError("No knowledge-base match must not include a document path")
        return self
