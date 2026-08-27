"""Run deterministic Task 1 and Task 2 evaluations using supplied data only."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.models.triage import TicketInput
from app.services.account_brief import AccountNotFoundError, AccountBriefService, summarize_account
from app.services.dataset import DatasetRepository
from app.services.triage import triage_ticket


EVALS_DIRECTORY = Path(__file__).resolve().parent


def _load_cases(filename: str) -> list[dict[str, Any]]:
    with (EVALS_DIRECTORY / filename).open(encoding="utf-8") as source:
        payload = json.load(source)
    if not isinstance(payload, list):
        raise ValueError(f"{filename} must contain a JSON array")
    return payload


def _result(test_id: str, checks: dict[str, bool]) -> dict[str, Any]:
    passed = all(checks.values())
    failed_checks = [name for name, value in checks.items() if not value]
    return {
        "test_id": test_id,
        "passed": passed,
        "quality_score": round(sum(checks.values()) / len(checks), 2) if checks else 0.0,
        "explanation": "All deterministic acceptance checks passed." if passed else f"Failed checks: {', '.join(failed_checks)}.",
        "checks": checks,
    }


def _task1_results(repository: DatasetRepository) -> list[dict[str, Any]]:
    ticket_by_id = {ticket.ticket_id: ticket for ticket in repository.tickets}
    valid_areas = {ticket.product_area for ticket in repository.tickets}
    valid_categories = {"Bug", "Feature Request", "How-To", "Performance", "Billing", "Integration", "Onboarding", "Data Loss"}
    valid_urgencies = {"P1", "P2", "P3", "P4"}
    results: list[dict[str, Any]] = []
    for case in _load_cases("task1_cases.json"):
        source_ticket = ticket_by_id[case["input"]["source_ticket_id"]]
        output = triage_ticket(TicketInput(subject=source_ticket.subject, body=source_ticket.body), get_settings())
        criteria = case["acceptance_criteria"]
        document_exists = output.relevant_knowledge_base_document is None or (get_settings().project_root / output.relevant_knowledge_base_document).is_file()
        checks = {
            "valid_product_area": output.product_area in valid_areas,
            "valid_issue_category": output.issue_category in valid_categories,
            "valid_urgency": output.urgency in valid_urgencies,
            "required_fields": bool(output.reasoning and output.recommended_responder_team and output.draft_first_response),
            "kb_match_validity": output.known_issue_match == (output.relevant_knowledge_base_document is not None),
            "kb_document_exists": document_exists,
            "no_match_behavior": output.known_issue_match or output.relevant_knowledge_base_document is None,
            "no_detectable_unsupported_claim": not any(term in output.draft_first_response.lower() for term in ("root cause", "confirmed", "fixed", "resolved")),
        }
        if "expected_issue_category" in criteria:
            checks["expected_issue_category"] = output.issue_category == criteria["expected_issue_category"]
        if "expected_urgency" in criteria:
            checks["expected_urgency"] = output.urgency == criteria["expected_urgency"]
        if "expected_known_issue_match" in criteria:
            checks["expected_known_issue_match"] = output.known_issue_match == criteria["expected_known_issue_match"]
        if "expected_document" in criteria:
            checks["expected_document"] = output.relevant_knowledge_base_document == criteria["expected_document"]
        results.append(_result(case["test_id"], checks))
    return results


def _task2_results(repository: DatasetRepository) -> list[dict[str, Any]]:
    service = AccountBriefService(repository)
    ticket_text = {ticket.ticket_id: f"{ticket.subject}\n{ticket.body}" for ticket in repository.tickets}
    results: list[dict[str, Any]] = []
    for case in _load_cases("task2_cases.json"):
        criteria = case["acceptance_criteria"]
        account_id = case["account_id"]
        try:
            brief = summarize_account(account_id, repository)
        except AccountNotFoundError:
            results.append(_result(case["test_id"], {"graceful_missing_account": criteria.get("expected_error") == "not_found"}))
            continue

        account = repository.accounts_by_id[account_id]
        recent = service.recent_tickets(account_id)
        flags = brief.open_risks_and_flagged_issues.flags
        allowed_evidence = set(account.escalation_notes) | {account.health_status, account.usage_trend}
        if account.nps_score is not None:
            allowed_evidence.add(str(account.nps_score))
        ticket_flags_valid = all(
            flag.ticket_id in ticket_text and flag.ticket_quote in ticket_text[flag.ticket_id]
            for flag in flags
            if flag.ticket_id is not None
        )
        account_evidence_valid = all(
            flag.account_evidence is None or flag.account_evidence in allowed_evidence
            for flag in flags
        )
        sections = brief.model_dump(by_alias=True)
        checks = {
            "account_lookup": account_id in repository.accounts_by_id,
            "ninety_day_filter": all(ticket.account_id == account_id and ticket.created_at <= service._resolve_as_of(None) and ticket.created_at >= service._resolve_as_of(None).replace() - __import__("datetime").timedelta(days=90) for ticket in recent),
            "exactly_three_sections": set(sections) == {"Executive Summary", "Open Risks & Flagged Issues", "Recommended Talking Points"},
            "summary_sentence_count": 3 <= len(brief.executive_summary) <= 5,
            "evidence_supported_risks": account_evidence_valid,
            "valid_ticket_ids_and_exact_quotes": ticket_flags_valid,
            "recommended_talking_points": bool(brief.recommended_talking_points),
        }
        if "expected_health_status" in criteria:
            checks["expected_health_status"] = account.health_status == criteria["expected_health_status"]
        if "expected_recent_ticket_ids" in criteria:
            checks["expected_recent_ticket_ids"] = [ticket.ticket_id for ticket in recent] == criteria["expected_recent_ticket_ids"]
        if "required_flag_types" in criteria:
            actual_types = {flag.flag_type for flag in flags}
            checks["required_flag_types"] = set(criteria["required_flag_types"]).issubset(actual_types)
        results.append(_result(case["test_id"], checks))
    return results


def evaluate_all() -> dict[str, Any]:
    settings = get_settings()
    repository = DatasetRepository(settings.data_directory, settings.knowledge_base_directory)
    task1 = _task1_results(repository)
    task2 = _task2_results(repository)
    all_results = task1 + task2
    passed_count = sum(result["passed"] for result in all_results)
    report = {
        "run_timestamp": datetime.now(timezone.utc).isoformat(),
        "task1_results": task1,
        "task2_results": task2,
        "task1_aggregate_score": round(sum(result["quality_score"] for result in task1) / len(task1), 2),
        "task2_aggregate_score": round(sum(result["quality_score"] for result in task2) / len(task2), 2),
        "overall_score": round(sum(result["quality_score"] for result in all_results) / len(all_results), 2),
        "passed_count": passed_count,
        "failed_count": len(all_results) - passed_count,
    }
    return report


def main() -> None:
    report = evaluate_all()
    report_path = EVALS_DIRECTORY / "eval_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
