"""Deterministic, source-grounded Task 2 account health summaries."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models import AccountBrief, RiskFlag, RiskSection, Ticket
from app.services.dataset import DatasetRepository


class AccountBriefError(RuntimeError):
    """Controlled failure for malformed source data or summary generation."""


class AccountNotFoundError(AccountBriefError):
    """Raised when an exact supplied account ID is unavailable."""


ACTIVE_TICKET_STATUSES = {"Open", "In Progress", "Pending Customer"}


class AccountBriefService:
    """Reusable account-brief service that reads only the assignment data."""

    def __init__(self, repository: DatasetRepository) -> None:
        self._repository = repository

    def summarize(self, account_id: str, as_of_utc: datetime | None = None) -> AccountBrief:
        account = self._repository.accounts_by_id.get(account_id)
        if account is None:
            raise AccountNotFoundError(f"Account '{account_id}' was not found in the supplied accounts dataset")

        reference_time = self._resolve_as_of(as_of_utc)
        recent_tickets = self.recent_tickets(account_id, reference_time)
        return self._build_brief(account, recent_tickets, reference_time)

    def recent_tickets(self, account_id: str, as_of_utc: datetime | None = None) -> tuple[Ticket, ...]:
        reference_time = self._resolve_as_of(as_of_utc)
        cutoff = reference_time - timedelta(days=90)
        filtered: list[Ticket] = []
        for ticket in self._repository.tickets_by_account_id.get(account_id, ()):
            if ticket.created_at.tzinfo is None:
                raise AccountBriefError(f"Ticket {ticket.ticket_id} has a timezone-naive created_at value")
            if ticket.created_at >= cutoff and ticket.created_at <= reference_time:
                filtered.append(ticket)
        return tuple(sorted(filtered, key=lambda ticket: (ticket.created_at, ticket.ticket_id), reverse=True))

    def _resolve_as_of(self, as_of_utc: datetime | None) -> datetime:
        if as_of_utc is not None:
            if as_of_utc.tzinfo is None:
                raise AccountBriefError("as_of_utc must be timezone-aware")
            return as_of_utc.astimezone(timezone.utc)
        try:
            return max(ticket.created_at for ticket in self._repository.tickets)
        except ValueError as error:
            raise AccountBriefError("No supplied tickets are available to establish the 90-day reference time") from error

    def _build_brief(self, account, recent_tickets: tuple[Ticket, ...], reference_time: datetime) -> AccountBrief:
        summary = [
            f"{account.company} is recorded as {account.health_status} on the {account.plan_tier} plan, with {account.tam} as TAM.",
            f"Usage is {account.usage_trend}, with {account.seats_active} active of {account.seats_licensed} licensed seats.",
            f"The account record lists {account.open_tickets} open tickets and {account.p1_tickets_last_30d} P1 tickets in the last 30 days; {len(recent_tickets)} exact-ID linked tickets fall within the 90-day window ending {reference_time.date().isoformat()}.",
            f"The recorded renewal date is {account.renewal_date.isoformat()} and the last QBR date is {account.last_qbr_date.isoformat()}.",
        ]
        flags = self._account_flags(account) + self._ticket_flags(recent_tickets)
        statement = "Material account risks or escalation signals are listed below." if flags else "No material risk is supported by the supplied account record or recent exact-ID linked tickets."
        return AccountBrief(
            executive_summary=summary,
            open_risks_and_flagged_issues=RiskSection(statement=statement, flags=flags),
            recommended_talking_points=self._talking_points(account, recent_tickets, flags),
        )

    @staticmethod
    def _account_flags(account) -> list[RiskFlag]:
        flags: list[RiskFlag] = []
        if account.health_status in {"At Risk", "Churning"}:
            flags.append(RiskFlag(flag_type="Churn Risk", explanation=f"Account health is recorded as {account.health_status}.", account_evidence=account.health_status))
        if account.usage_trend in {"Declining", "Inactive"}:
            flags.append(RiskFlag(flag_type="Churn Risk", explanation=f"Usage trend is recorded as {account.usage_trend}.", account_evidence=account.usage_trend))
        if account.open_tickets > 0 or account.p1_tickets_last_30d > 0:
            flags.append(RiskFlag(flag_type="Open Support Risk", explanation=f"Account metadata lists {account.open_tickets} open tickets and {account.p1_tickets_last_30d} P1 tickets in the last 30 days."))
        if account.nps_score is not None and account.nps_score <= 6:
            flags.append(RiskFlag(flag_type="Churn Risk", explanation=f"Recorded NPS score is {account.nps_score}.", account_evidence=str(account.nps_score)))
        for note in account.escalation_notes:
            flags.append(RiskFlag(flag_type="Escalation Signal", explanation="The supplied escalation note indicates a customer-management concern.", account_evidence=note))
        return flags

    @staticmethod
    def _ticket_flags(tickets: tuple[Ticket, ...]) -> list[RiskFlag]:
        flags: list[RiskFlag] = []
        for ticket in tickets:
            if ticket.status in ACTIVE_TICKET_STATUSES:
                flags.append(
                    RiskFlag(
                        flag_type="Open Support Risk",
                        explanation=f"Ticket status is {ticket.status}, so the supplied ticket remains unresolved.",
                        ticket_id=ticket.ticket_id,
                        ticket_quote=ticket.subject,
                    )
                )
        return flags

    @staticmethod
    def _talking_points(account, recent_tickets: tuple[Ticket, ...], flags: list[RiskFlag]) -> list[str]:
        points = [f"Review the recorded {account.health_status} health status and {account.usage_trend.lower()} usage trend with the customer."]
        if account.escalation_notes:
            points.append("Address the escalation observations documented on the account before moving to broader account planning.")
        if account.open_tickets or account.p1_tickets_last_30d:
            points.append(f"Confirm the current state and ownership of the {account.open_tickets} account-level open tickets and {account.p1_tickets_last_30d} P1 tickets recorded for the last 30 days.")
        if recent_tickets:
            points.append(f"Review the {len(recent_tickets)} exact-ID linked tickets in the 90-day window, including their recorded status and customer impact.")
        else:
            points.append("Confirm whether the absence of exact-ID linked tickets in the 90-day window reflects normal support activity or a data-linkage gap.")
        return points


def summarize_account(account_id: str, repository: DatasetRepository, as_of_utc: datetime | None = None) -> AccountBrief:
    """Reusable Task 2 function for API handlers, scripts, and tests."""
    return AccountBriefService(repository).summarize(account_id, as_of_utc)
