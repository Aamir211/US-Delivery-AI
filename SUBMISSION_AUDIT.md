# Submission Audit

| Requirement | Status | Evidence/File | Action |
|---|---|---|---|
| Task 1 raw text and JSON ticket input | Complete | `POST /triage`, `app/api/routes.py` | Tested by API smoke and `tests/test_triage.py` |
| Task 1 product area, category, P1–P4 urgency, reasoning | Complete | `app/models/triage.py`, `app/services/triage.py` | Pydantic enums and tests enforce values |
| Task 1 KB matching and local document path | Complete | `app/retrieval/knowledge_base.py` | No-match and path checks in tests/evals |
| Task 1 responder team and first response | Complete | `app/services/triage.py` | Required result fields and eval checks |
| Task 1 structured API and Python service | Complete | `app/models/triage.py`, `triage_ticket` | API and callable tests |
| Task 2 exact account lookup and 90-day tickets | Complete | `app/services/account_brief.py` | Timezone-aware created-at test |
| Task 2 three sections and 3–5 sentence summary | Complete | `app/models/account_brief.py` | Model bounds and tests |
| Task 2 support, escalation, and churn risks | Complete | `app/services/account_brief.py` | Real-account test cases |
| Task 2 direct ticket quotes | Complete | `RiskFlag` model and tests | Quote must be a ticket substring |
| Task 2 talking points, determinism, missing data | Complete | `summarize_account` | Exact-ID/no-ticket/404 tests |
| Task 3 at least five Task 1 cases | Complete | `evals/task1_cases.json` | Five distinct cases, including adversarial |
| Task 3 at least five Task 2 cases | Complete | `evals/task2_cases.json` | Five distinct cases, including missing account |
| Task 3 criteria, pass/fail, scoring, aggregates/report | Complete | `evals/evaluator.py`, `evals/eval_report.json` | Deterministic 0–1 checks |
| Task 4 failure modes, detection, mitigation | Complete | `DESIGN.md` | Three documented failure modes |
| Task 4 latency/quality, PII, external APIs, 10x scaling | Complete | `DESIGN.md` | Four required sections |
| README, setup, samples, documented entry point | Complete | `README.md` | `uvicorn app.main:app --reload` |
| `.env.example` and no committed credentials | Complete | `.env.example`, `.gitignore` | Placeholder key only; `.env` ignored |
| Supplied synthetic data only | Complete | `data/`, `knowledge-base/`, services | No web/data integrations |
| Clean installation dependencies | Complete | `requirements.txt`, CI | Fresh isolated Python 3.13 environment installed requirements and imported the app/UI |
| Bonus: prompt versioning | Complete | `prompts/CHANGELOG.md` | Two versioned prompt files |
| Bonus: GitHub Actions | Complete | `.github/workflows/ci.yml` | Installs, tests, evaluates |
| Bonus: optional UI | Complete | `streamlit_app.py` | Reuses existing service functions |
| Bonus: streaming | Not implemented | N/A | Intentionally out of scope |
