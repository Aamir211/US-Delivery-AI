"""Optional local UI that reuses the ticket-triage and account-brief services."""

from __future__ import annotations

import streamlit as st

from app.config import get_settings
from app.models.triage import TicketInput
from app.services.account_brief import AccountBriefError, AccountNotFoundError, summarize_account
from app.services.dataset import DatasetRepository
from app.services.triage import TriageServiceError, triage_ticket


@st.cache_resource
def get_repository() -> DatasetRepository:
    settings = get_settings()
    return DatasetRepository(settings.data_directory, settings.knowledge_base_directory)


st.set_page_config(page_title="US Delivery AI", page_icon="🛟", layout="wide")
st.title("US Delivery AI")
st.caption("Local interface for ticket triage and TAM account health briefs.")

triage_tab, account_brief_tab = st.tabs(["Ticket Triage", "Account Health Brief"])

with triage_tab:
    st.write("Classify a support ticket and retrieve relevant local knowledge-base guidance.")
    subject = st.text_input("Subject")
    body = st.text_area("Body", height=180)
    if st.button("Run Triage", type="primary"):
        try:
            result = triage_ticket(TicketInput(subject=subject, body=body), get_settings())
            st.json(result.model_dump())
        except (ValueError, TriageServiceError) as error:
            st.error(str(error))

with account_brief_tab:
    st.write("Create a source-grounded account brief from the supplied account and ticket data.")
    account_id = st.text_input("Account ID", placeholder="ACC-3336")
    if st.button("Generate Account Brief", type="primary"):
        try:
            result = summarize_account(account_id, get_repository())
            st.subheader("Executive Summary")
            for sentence in result.executive_summary:
                st.write(sentence)
            st.subheader("Open Risks & Flagged Issues")
            st.write(result.open_risks_and_flagged_issues.statement)
            for flag in result.open_risks_and_flagged_issues.flags:
                st.write(f"- **{flag.flag_type}:** {flag.explanation}")
                if flag.ticket_id:
                    st.caption(f"{flag.ticket_id}: “{flag.ticket_quote}”")
                elif flag.account_evidence:
                    st.caption(f"Account evidence: {flag.account_evidence}")
            st.subheader("Recommended Talking Points")
            for point in result.recommended_talking_points:
                st.write(f"- {point}")
        except AccountNotFoundError as error:
            st.warning(str(error))
        except AccountBriefError as error:
            st.error(str(error))
