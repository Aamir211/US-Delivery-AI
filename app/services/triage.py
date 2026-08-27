"""Task 1 ticket-triage service with local retrieval and validated output."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from app.config import Settings
from app.models.triage import TicketInput, TriageResult
from app.retrieval.knowledge_base import KnowledgeBaseRetriever, RetrievalMatch


class TriageServiceError(RuntimeError):
    """A controlled failure suitable for an API response."""


CATEGORY_KEYWORDS = {
    "Data Loss": ("data loss", "lost data", "deleted", "corrupt", "missing data"),
    "Billing": ("invoice", "billing", "charge", "payment", "seat", "refund"),
    "Onboarding": ("onboarding", "provision", "invite", "setup", "scim"),
    "Integration": ("integration", "connector", "salesforce", "snowflake", "bigquery", "okta", "slack", "webhook"),
    "Performance": ("slow", "timeout", "latency", "stalled", "throughput", "performance", "loading", "load time"),
    "Feature Request": ("feature request", "would like", "add support", "enhancement"),
    "How-To": ("how do", "how to", "where can", "documentation"),
}
AREA_KEYWORDS = {
    "Authentication": ("sso", "saml", "login", "authentication", "token"),
    "Connectors": ("connector", "salesforce", "snowflake", "bigquery"),
    "Pipeline Monitoring": ("pipeline", "heartbeat", "stalled"),
    "Data Ingestion": ("ingestion", "batch", "source"),
    "Schema Management": ("schema", "schema_mismatch"),
    "Key Management": ("key", "secret", "rotation", "encryption"),
    "Scheduling": ("schedule", "cron", "scheduled"),
}
PRODUCT_AREAS = (
    "Pipeline Monitoring", "Schema Management", "Conflict Resolution", "Bandwidth Limits", "Data Ingestion",
    "Data Sources", "Key Management", "Error Handling", "Audit Logs", "Authentication", "Connectors",
    "Integrations", "Scheduling", "Templates", "Triggers", "Permissions", "Encryption", "Dashboard",
    "Reports", "Exports", "File Sync", "Actions", "Alerts", "SSO", "API",
)
TEAM_BY_CATEGORY = {
    "Billing": "Billing Support",
    "Data Loss": "Incident Response",
    "Integration": "Integrations Support",
    "Onboarding": "Onboarding Support",
    "Performance": "Technical Support",
    "Feature Request": "Product Support",
    "How-To": "Technical Support",
    "Bug": "Technical Support",
}


class TriageService:
    """Reusable triage function; no external data is ever retrieved."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._retriever = KnowledgeBaseRetriever(settings.knowledge_base_directory, settings.project_root)
        self._prompt = (settings.project_root / "prompts" / "triage_v1.txt").read_text(encoding="utf-8")

    def triage(self, ticket: TicketInput) -> TriageResult:
        matches = self._retriever.search(ticket.combined_text)
        if self._settings.openai_api_key:
            return self._triage_with_llm(ticket, matches)
        return self._triage_deterministically(ticket, matches)

    def _triage_deterministically(self, ticket: TicketInput, matches: tuple[RetrievalMatch, ...]) -> TriageResult:
        text = ticket.combined_text.lower()
        category = next((name for name, keywords in CATEGORY_KEYWORDS.items() if any(keyword in text for keyword in keywords)), "Bug")
        area = self._infer_product_area(text)
        urgency = self._infer_urgency(text)
        match = matches[0] if matches else None
        document = match.chunk.document_path if match else None
        reasoning = f"Classified as {category} from the ticket wording; urgency is {urgency} based on the stated impact."
        if match:
            reasoning += f" Retrieved {document} from overlapping ticket terms."
        else:
            reasoning += " No supplied knowledge-base section had a reliable lexical match."
        return TriageResult(
            product_area=area,
            issue_category=category,
            urgency=urgency,
            reasoning=reasoning,
            known_issue_match=match is not None,
            relevant_knowledge_base_document=document,
            recommended_responder_team=TEAM_BY_CATEGORY[category],
            draft_first_response=self._draft_response(ticket, category, document),
        )

    @staticmethod
    def _infer_urgency(text: str) -> str:
        if any(term in text for term in ("data loss", "missing records", "record discrepancy", "production is down", "complete outage", "business stopped", "all users", "business continuity", "people blocked")):
            return "P1"
        if any(term in text for term in ("production", "failing", "unable to", "critical", "urgent")):
            return "P2"
        if any(term in text for term in ("how do", "how to", "would like", "feature request", "minor")):
            return "P4"
        return "P3"

    @staticmethod
    def _infer_product_area(text: str) -> str:
        for area in PRODUCT_AREAS:
            if area.lower() in text:
                return area
        return next((name for name, keywords in AREA_KEYWORDS.items() if any(keyword in text for keyword in keywords)), "Error Handling")

    @staticmethod
    def _draft_response(ticket: TicketInput, category: str, document: str | None) -> str:
        subject = ticket.subject or "your support request"
        response = f"Thanks for contacting support about {subject}. We are routing this as a {category} request for review."
        if document:
            response += f" The supplied knowledge-base document {document} may be relevant; please review it and share any error messages, timestamps, and steps already tried."
        else:
            response += " Please share any error messages, timestamps, affected users, and steps already tried so the team can investigate."
        return response

    def _triage_with_llm(self, ticket: TicketInput, matches: tuple[RetrievalMatch, ...]) -> TriageResult:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self._settings.openai_api_key)
            evidence = [
                {"path": match.chunk.document_path, "headings": match.chunk.headings, "content": match.chunk.content}
                for match in matches
            ]
            response = client.responses.create(
                model=self._settings.openai_model,
                instructions=self._prompt,
                input=json.dumps({"ticket": ticket.model_dump(), "knowledge_base_matches": evidence}),
                temperature=0,
                store=False,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "ticket_triage",
                        "schema": TriageResult.model_json_schema(),
                        "strict": True,
                    }
                },
            )
            result = TriageResult.model_validate_json(response.output_text)
        except (ImportError, ValidationError, ValueError, json.JSONDecodeError) as error:
            raise TriageServiceError(f"LLM returned invalid structured output: {error}") from error
        except Exception as error:
            raise TriageServiceError("LLM triage request failed") from error

        allowed_documents = {match.chunk.document_path for match in matches}
        if result.relevant_knowledge_base_document not in allowed_documents:
            raise TriageServiceError("LLM returned an unverified knowledge-base document")
        if not matches and result.known_issue_match:
            raise TriageServiceError("LLM reported a knowledge-base match without retrieval evidence")
        return result


def triage_ticket(ticket: TicketInput, settings: Settings) -> TriageResult:
    """Reusable Task 1 function for scripts, tests, and the API."""
    return TriageService(settings).triage(ticket)
