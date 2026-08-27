"""Read and validate only the supplied JSON datasets."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

from app.models import Account, Ticket


@dataclass(frozen=True, slots=True)
class DatasetSummary:
    ticket_count: int
    account_count: int
    knowledge_base_document_count: int


class DatasetRepository:
    """In-memory, read-only access to validated assignment inputs."""

    def __init__(self, data_directory: Path, knowledge_base_directory: Path) -> None:
        self._data_directory = data_directory
        self._knowledge_base_directory = knowledge_base_directory

    @staticmethod
    def _read_json(path: Path) -> list[dict[str, object]]:
        with path.open(encoding="utf-8") as source:
            content = json.load(source)
        if not isinstance(content, list):
            raise ValueError(f"Expected a JSON array in {path}")
        return content

    @cached_property
    def tickets(self) -> tuple[Ticket, ...]:
        tickets = tuple(Ticket.model_validate(item) for item in self._read_json(self._data_directory / "tickets.json"))
        ticket_ids = [ticket.ticket_id for ticket in tickets]
        if len(ticket_ids) != len(set(ticket_ids)):
            raise ValueError("tickets.json contains duplicate ticket_id values")
        return tickets

    @cached_property
    def accounts(self) -> tuple[Account, ...]:
        accounts = tuple(Account.model_validate(item) for item in self._read_json(self._data_directory / "accounts.json"))
        account_ids = [account.account_id for account in accounts]
        if len(account_ids) != len(set(account_ids)):
            raise ValueError("accounts.json contains duplicate account_id values")
        return accounts

    @cached_property
    def knowledge_base_paths(self) -> tuple[Path, ...]:
        return tuple(sorted(self._knowledge_base_directory.rglob("*.md")))

    @cached_property
    def tickets_by_account_id(self) -> dict[str, tuple[Ticket, ...]]:
        grouped: dict[str, list[Ticket]] = {}
        for ticket in self.tickets:
            grouped.setdefault(ticket.account_id, []).append(ticket)
        return {account_id: tuple(records) for account_id, records in grouped.items()}

    @cached_property
    def accounts_by_id(self) -> dict[str, Account]:
        return {account.account_id: account for account in self.accounts}

    def summary(self) -> DatasetSummary:
        return DatasetSummary(len(self.tickets), len(self.accounts), len(self.knowledge_base_paths))
