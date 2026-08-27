"""Foundation routes only; task endpoints are intentionally absent."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, ValidationError

from app.config import get_settings
from app.models.account_brief import AccountBrief
from app.models.triage import TicketInput, TriageResult
from app.services.account_brief import AccountBriefError, AccountNotFoundError, summarize_account
from app.services.dataset import DatasetRepository
from app.services.triage import TriageServiceError, triage_ticket


router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    status: str
    tickets: int
    accounts: int
    knowledge_base_documents: int


@router.get("/health", response_model=HealthResponse)
def health_check(request: Request) -> HealthResponse:
    """Verify that the supplied, read-only assignment inputs load successfully."""
    repository: DatasetRepository = request.app.state.dataset_repository
    summary = repository.summary()
    return HealthResponse(status="ok", tickets=summary.ticket_count, accounts=summary.account_count, knowledge_base_documents=summary.knowledge_base_document_count)


async def _parse_ticket_request(request: Request) -> TicketInput:
    try:
        if request.headers.get("content-type", "").split(";", 1)[0] == "text/plain":
            return TicketInput(body=(await request.body()).decode("utf-8"))
        payload = await request.json()
        if isinstance(payload, str):
            return TicketInput(body=payload)
        return TicketInput.model_validate(payload)
    except (UnicodeDecodeError, ValidationError, ValueError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Provide non-empty plain text or JSON with subject and/or body.") from None


@router.post("/triage", response_model=TriageResult)
async def triage(request: Request) -> TriageResult:
    """Triage raw text or a JSON ticket using only the local knowledge base."""
    ticket = await _parse_ticket_request(request)
    try:
        return triage_ticket(ticket, get_settings())
    except TriageServiceError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error


@router.get("/accounts/{account_id}/brief", response_model=AccountBrief, response_model_by_alias=True)
def account_brief(account_id: str, request: Request) -> AccountBrief:
    """Generate a deterministic, source-grounded TAM brief for an exact account ID."""
    repository: DatasetRepository = request.app.state.dataset_repository
    try:
        return summarize_account(account_id, repository)
    except AccountNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except AccountBriefError as error:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(error)) from error
