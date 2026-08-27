import json
import asyncio

import httpx
import pytest
from pydantic import ValidationError

from app.config import get_settings
from app.models.triage import TicketInput, TriageResult
from app.services.triage import triage_ticket
from app.main import app


def run_triage(subject: str, body: str):
    return triage_ticket(TicketInput(subject=subject, body=body), get_settings())


def test_normal_ticket_returns_valid_structured_triage() -> None:
    ticket = json.loads(open("data/tickets.json", encoding="utf-8").read())[0]

    result = run_triage(ticket["subject"], ticket["body"])

    assert result.issue_category in {"Bug", "Feature Request", "How-To", "Performance", "Billing", "Integration", "Onboarding", "Data Loss"}
    assert result.urgency in {"P1", "P2", "P3", "P4"}
    assert result.draft_first_response


def test_urgent_ticket_is_prioritised_as_p1() -> None:
    result = run_triage("Production data loss", "Our production system has a complete outage and data loss is occurring.")

    assert result.issue_category == "Data Loss"
    assert result.urgency == "P1"
    assert result.recommended_responder_team == "Incident Response"


@pytest.mark.parametrize(
    ("body", "expected_urgency"),
    [
        ("Our production system has a complete outage and data loss is occurring.", "P1"),
        ("Our production pipeline is failing and we need urgent assistance.", "P2"),
        ("The dashboard is slow for one user.", "P3"),
        ("How do I configure this feature?", "P4"),
    ],
)
def test_urgency_is_inferred_from_ticket_content(body: str, expected_urgency: str) -> None:
    assert run_triage("Support request", body).urgency == expected_urgency


def test_known_knowledge_base_issue_returns_local_document_path() -> None:
    result = run_triage("Pipeline timeout", "Our pipeline reports ERR_CONNECTION_TIMEOUT after 30s.")

    assert result.known_issue_match is True
    assert result.relevant_knowledge_base_document == "knowledge-base/troubleshooting/performance-and-integrations.md"


def test_unknown_issue_explicitly_returns_no_match() -> None:
    result = run_triage("Orbital widget issue", "The glorpulator emits a quasarflange error after zenthos calibration.")

    assert result.known_issue_match is False
    assert result.relevant_knowledge_base_document is None


@pytest.mark.parametrize("payload", [{}, {"subject": "", "body": ""}, {"subject": "Valid", "unexpected": "field"}])
def test_malformed_or_empty_ticket_is_rejected(payload: dict[str, str]) -> None:
    with pytest.raises(ValidationError):
        TicketInput.model_validate(payload)


def test_structured_output_rejects_unsupported_category_and_urgency() -> None:
    with pytest.raises(ValidationError):
        TriageResult.model_validate(
            {
                "product_area": "API",
                "issue_category": "Other",
                "urgency": "Critical",
                "reasoning": "Unsupported values should fail validation.",
                "known_issue_match": False,
                "relevant_knowledge_base_document": None,
                "recommended_responder_team": "Technical Support",
                "draft_first_response": "Thanks for the report.",
            }
        )


def test_triage_api_accepts_json_ticket() -> None:
    async def post_ticket() -> httpx.Response:
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                return await client.post("/triage", json={"subject": "Billing help", "body": "How do I view an invoice?"})

    response = asyncio.run(post_ticket())

    assert response.status_code == 200
    assert response.json()["issue_category"] == "Billing"


def test_triage_api_accepts_plain_text_ticket() -> None:
    async def post_ticket() -> httpx.Response:
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                return await client.post("/triage", content="Pipeline reports ERR_CONNECTION_TIMEOUT after 30s.", headers={"content-type": "text/plain"})

    response = asyncio.run(post_ticket())

    assert response.status_code == 200
    assert response.json()["known_issue_match"] is True
