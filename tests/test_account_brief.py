import asyncio
import json
from datetime import datetime, timedelta

import httpx
import pytest
from pydantic import ValidationError

from app.config import get_settings
from app.main import app
from app.models.account import Account
from app.models.ticket import Ticket
from app.services.account_brief import AccountBriefError, AccountNotFoundError, AccountBriefService, summarize_account
from app.services.dataset import DatasetRepository


@pytest.fixture
def repository() -> DatasetRepository:
    settings = get_settings()
    return DatasetRepository(settings.data_directory, settings.knowledge_base_directory)


def test_healthy_account_brief_uses_exactly_three_sections(repository: DatasetRepository) -> None:
    brief = summarize_account("ACC-3033", repository)

    assert len(brief.executive_summary) == 4
    assert set(brief.model_dump(by_alias=True)) == {
        "Executive Summary",
        "Open Risks & Flagged Issues",
        "Recommended Talking Points",
    }
    assert "Healthy" in brief.executive_summary[0]


def test_account_with_open_risks_uses_account_evidence(repository: DatasetRepository) -> None:
    brief = summarize_account("ACC-3336", repository)

    flags = brief.open_risks_and_flagged_issues.flags
    assert any(flag.flag_type == "Open Support Risk" for flag in flags)
    assert any(flag.account_evidence == "Inactive" for flag in flags)


def test_escalation_signals_are_grounded_in_real_account_notes(repository: DatasetRepository) -> None:
    brief = summarize_account("ACC-8113", repository)
    account = repository.accounts_by_id["ACC-8113"]

    escalation_evidence = [flag.account_evidence for flag in brief.open_risks_and_flagged_issues.flags if flag.flag_type == "Escalation Signal"]
    assert escalation_evidence
    assert set(escalation_evidence).issubset(set(account.escalation_notes))


def test_churn_risk_is_grounded_in_real_account_health(repository: DatasetRepository) -> None:
    brief = summarize_account("ACC-2944", repository)

    assert any(flag.flag_type == "Churn Risk" and flag.account_evidence == "Churning" for flag in brief.open_risks_and_flagged_issues.flags)


def test_invalid_ticket_timestamp_is_rejected_by_structured_data_model() -> None:
    ticket = json.loads(open("data/tickets.json", encoding="utf-8").read())[0]
    ticket["created_at"] = "not-a-timestamp"

    with pytest.raises(ValidationError):
        Ticket.model_validate(ticket)


def test_incomplete_account_record_is_rejected_by_structured_data_model() -> None:
    account = json.loads(open("data/accounts.json", encoding="utf-8").read())[0]
    account.pop("health_status")

    with pytest.raises(ValidationError):
        Account.model_validate(account)


def test_account_with_no_recent_exact_id_tickets_is_explicit(repository: DatasetRepository) -> None:
    brief = summarize_account("ACC-3033", repository)

    assert "0 exact-ID linked tickets" in brief.executive_summary[2]
    assert any("data-linkage gap" in point for point in brief.recommended_talking_points)


def test_90_day_filter_is_timezone_safe_and_exact(repository: DatasetRepository) -> None:
    service = AccountBriefService(repository)
    reference_time = max(ticket.created_at for ticket in repository.tickets)
    recent = service.recent_tickets("ACC-3336", reference_time)

    assert recent
    assert all(ticket.account_id == "ACC-3336" for ticket in recent)
    assert all(ticket.created_at.tzinfo is not None for ticket in recent)
    assert all(reference_time - ticket.created_at <= timedelta(days=90) for ticket in recent)
    with pytest.raises(AccountBriefError):
        service.recent_tickets("ACC-3336", datetime(2026, 5, 22))


def test_unknown_account_is_controlled_error(repository: DatasetRepository) -> None:
    with pytest.raises(AccountNotFoundError):
        summarize_account("ACC-DOES-NOT-EXIST", repository)


def test_ticket_quotes_are_exact_substrings_when_generated(repository: DatasetRepository) -> None:
    ticket_text = {ticket.ticket_id: f"{ticket.subject}\n{ticket.body}" for ticket in repository.tickets}

    for account in repository.accounts:
        brief = summarize_account(account.account_id, repository)
        for flag in brief.open_risks_and_flagged_issues.flags:
            if flag.ticket_id is not None:
                assert flag.ticket_quote in ticket_text[flag.ticket_id]


def test_account_brief_api_smoke(repository: DatasetRepository) -> None:
    async def fetch_brief() -> httpx.Response:
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                return await client.get("/accounts/ACC-3336/brief")

    response = asyncio.run(fetch_brief())

    assert response.status_code == 200
    assert set(response.json()) == {"Executive Summary", "Open Risks & Flagged Issues", "Recommended Talking Points"}
