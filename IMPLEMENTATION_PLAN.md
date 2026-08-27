# Implementation Plan — US Delivery Internship Technical Task Round

## Scope and constraints

This plan is based exclusively on the supplied repository materials and the
provided task brief. No application code is included in this change. The
existing JSON datasets and knowledge-base files are immutable inputs: the
application will read them but never edit, enrich, scrape, or supplement them.

## 1. Actual repository structure

```text
US-Delivery-AI/
├── README.md
├── DATA_SCHEMA.md
├── data/
│   ├── tickets.json                 # 500 synthetic ticket records
│   └── accounts.json                # 50 synthetic account records
├── knowledge-base/
│   ├── billing/billing-and-plans.md
│   ├── onboarding/onboarding-guide.md
│   ├── products/
│   │   ├── analyticshub.md
│   │   ├── cloudsync.md
│   │   ├── databridge-pro.md
│   │   ├── securevault.md
│   │   └── workflowengine.md
│   └── troubleshooting/
│       ├── authentication-sso.md
│       └── performance-and-integrations.md
├── .venv/                           # local virtual environment; not application source
└── .git/
```

There is currently no application source directory, dependency manifest, test
suite, or application configuration. The only existing Python environment is
`.venv`; it currently provides `pip`, not a project application.

## 2. Ticket dataset schema

`data/tickets.json` is a JSON array of 500 unique records. All fields are
present; `satisfaction_score` is `null` in 146 records.

| Field | Observed type | Notes |
|---|---|---|
| `ticket_id` | string | Unique `TKT-...` identifier |
| `account_id` | string | Foreign-key-like identifier; it is not reliably resolvable |
| `company`, `subject`, `body` | string | Customer and free-text ticket content |
| `product`, `product_area` | string | Product and feature/module context |
| `category` | string | One of `Billing`, `Bug`, `Data Loss`, `Feature Request`, `How-To`, `Integration`, `Onboarding`, `Performance` |
| `urgency` | string | One of `P1`, `P2`, `P3`, `P4` (14, 110, 217, and 159 records respectively) |
| `status` | string | `Open`, `In Progress`, `Pending Customer`, `Resolved`, or `Closed` |
| `plan_tier` | string | `Starter`, `Professional`, `Business`, or `Enterprise` |
| `assigned_agent` | string | One of 10 named support agents |
| `created_at`, `updated_at` | ISO-8601 UTC timestamp strings | Creation range: 2026-02-20T22:39:32.195432Z through 2026-05-22T00:23:32.203871Z; updates extend to 2026-05-24T14:39:32.186735Z |
| `tags` | array of strings | No empty tag arrays observed |
| `channel` | string | `email`, `portal`, `chat`, or `phone` |
| `satisfaction_score` | integer or null | Submitted scores are 1–5 |

`product` values are `AnalyticsHub`, `CloudSync`, `DataBridge Pro`,
`SecureVault`, and `WorkflowEngine`. The 25 observed `product_area` values are
`API`, `Actions`, `Alerts`, `Audit Logs`, `Authentication`, `Bandwidth Limits`,
`Conflict Resolution`, `Connectors`, `Dashboard`, `Data Ingestion`, `Data Sources`,
`Encryption`, `Error Handling`, `Exports`, `File Sync`, `Integrations`, `Key Management`,
`Permissions`, `Pipeline Monitoring`, `Reports`, `SSO`, `Scheduling`,
`Schema Management`, `Templates`, and `Triggers`.

The source documentation explicitly says that some ticket category and urgency
labels are deliberately ambiguous. They must be treated as evaluation edge
cases, not as an opportunity to invent a hidden ground truth.

## 3. Account dataset schema

`data/accounts.json` is a JSON array of 50 unique records. All fields are
present. `nps_score` is `null` in 37 records; 27 accounts have no escalation
notes.

| Field | Observed type | Notes |
|---|---|---|
| `account_id`, `company`, `tam`, `plan_tier` | string | Identity, owner, and commercial context |
| `arr_usd`, `seats_licensed`, `seats_active` | integer | Revenue and adoption signals |
| `products`, `integrations_active`, `escalation_notes` | array of strings | Product footprint, integrations, and free-text escalation observations |
| `health_status` | string | `Healthy`, `At Risk`, `Churning`, or `New` |
| `usage_trend` | string | `Increasing`, `Stable`, `Declining`, or `Inactive` |
| `open_tickets`, `p1_tickets_last_30d`, `last_login_days_ago` | integer | Support and usage signals |
| `customer_since`, `renewal_date`, `last_qbr_date` | `YYYY-MM-DD` string | Lifecycle and renewal dates |
| `primary_contact` | object | Always has `name` and `title` |
| `nps_score` | integer or null | Net Promoter Score when supplied |
| `region`, `industry` | string | Account segmentation |

Observed account-health distribution is 22 `Healthy`, 20 `At Risk`, 5 `New`,
and 3 `Churning`; usage can be `Increasing`, `Stable`, `Declining`, or
`Inactive`. These fields, escalation notes, low/absent NPS, usage decline, open
tickets, P1 count, and renewal timing are source-backed risk inputs.

## 4. Knowledge-base structure

The retrieval corpus contains nine Markdown documents:

- `products/`: five product references for AnalyticsHub, CloudSync, DataBridge
  Pro, SecureVault, and WorkflowEngine. They cover product/module behaviour,
  configuration, known errors, support scenarios, and plan limits.
- `troubleshooting/`: shared authentication/SSO and performance/integration
  diagnosis guides, including error-code reference tables and resolution steps.
- `billing/`: plans, seat billing, invoices, upgrades, cancellation, and FAQs.
- `onboarding/`: organisation onboarding, roles, provisioning, training, and
  first-90-day guidance.

The corpus has explicit Markdown headings, horizontal-rule section boundaries,
tables, error codes, and cross-links. The loader will retain source path,
directory/topic, heading hierarchy, and section ordinal as chunk metadata.
Horizontal rules are the primary chunk boundary; tables/error-code rows remain
atomic chunks when practical. This follows the repository's own RAG guidance.

## 5. Data loading strategy

Create a single read-only repository layer, for example `src/data_loader.py`,
that resolves paths relative to the project root rather than the current shell
directory. It will:

1. Load both JSON arrays with the Python standard library and validate required
   keys, scalar/collection types, enum membership, unique primary IDs, and
   parseable timestamps/dates.
2. Parse ticket timestamps as timezone-aware UTC datetimes and account lifecycle
   values as dates; preserve original text exactly for citations and responses.
3. Build immutable in-memory indexes by `ticket_id`, `account_id`, and ticket
   account ID; load and chunk the Markdown corpus once at startup.
4. Return structured validation diagnostics for malformed input rather than
   silently dropping source records. No normalized or generated record may be
   written back to `data/`.

Small dataset size makes in-process read-through caching adequate initially.

## 6. Ticket-to-account joining strategy

Use only exact `account_id` equality and a left join from the requested ticket
or account. Never fall back to company-name matching: the source data proves it
is unsafe. Only 4 ticket records (`TKT-10047`, `TKT-10112`, `TKT-10197`, and
`TKT-10293`) have account IDs present in `accounts.json`; their ticket company
values also disagree with the company on the matched account. The remaining 496
tickets reference 480 unmatched account IDs.

For Task 1, an unresolved ID will produce `account_context: unavailable` and a
clear provenance/status field while retaining the ticket's own supplied
company/plan fields. For Task 2, an unknown account ID will return a typed
not-found result; it must not select a “closest” account. For a known account,
ticket history is the exact account-ID bucket (one-to-many) and the account
record remains the authoritative account profile.

## 7. 90-day ticket filtering strategy

Filter by parsed `created_at`, not `updated_at`, with an inclusive cutoff:
`created_at >= as_of_utc - timedelta(days=90)`. Expose `as_of_utc` as an
explicit, injected parameter for repeatable tests and reports.

The current calendar date is later than the static ticket range, so using the
machine clock would yield no records. Dataset mode will therefore default
`as_of_utc` to the maximum observed `created_at` timestamp
(`2026-05-22T00:23:32.203871Z`), and will disclose that reference time in each
Task 2 output. Production mode can explicitly supply the actual current UTC
time. This uses only supplied data and keeps the requested window meaningful
and deterministic.

## 8. Task 1 architecture

Expose `triage_ticket(input: RawTicketInput) -> TriageResult` through a FastAPI
endpoint such as `POST /triage`, with the pure function callable directly by
tests. The pipeline will be:

1. Validate raw text or `subject` + `body`; combine only those fields for the
   incoming-ticket analysis.
2. Retrieve the top relevant knowledge-base chunks using deterministic lexical
   retrieval over supplied Markdown, preferring exact error codes and matching
   product/topic metadata.
3. Ask the configured LLM for schema-constrained JSON (or use a deterministic
   fallback when no model is configured), limited to the observed product-area,
   category, and P1–P4 enums.
4. Validate the result with Pydantic, attach retrieved document paths/sections,
   route to a defined responder team, and produce a grounded draft first reply.
5. Return classification, reasoning/evidence, retrieval matches, recommended
   responder team, draft response, confidence/ambiguity flag, and prompt/model
   version. Ambiguous cases must express uncertainty rather than inventing facts.

The response draft must cite only retrieved documentation or user-provided
ticket content. An explicit escalation guard will ensure high-severity or data
loss/security indications are routed for human review.

## 9. Task 2 architecture

Expose `summarize_account(account_id, as_of_utc=None) -> AccountBrief` via
`GET /accounts/{account_id}/brief` and as a pure service function. Its
deterministic preparation phase loads the exact account, obtains its 90-day
ticket bucket, derives transparent counts (open/active statuses, P1s,
categories, products, and recent dates), and carries through source escalation
notes.

The summariser receives this bounded evidence package and returns exactly three
sections: a 3–5 sentence executive summary, open risks/flagged issues, and TAM
talking points. Every ticket-derived churn/escalation flag includes the source
ticket ID and a direct ticket quote as required by the brief. Risk flags may be
seeded by deterministic rules (health status, declining/inactive usage,
escalation notes, P1/open-ticket metrics, renewal date) and refined only from
provided source text. Stable ordering, fixed prompt version/settings, and
post-validation make identical inputs deterministic.

The output also distinguishes “no linked tickets” from “no tickets in the
90-day window,” particularly important given the observed join gaps.

## 10. Task 3 evaluation architecture

Add a versioned, repository-local evaluation fixture set and a runner that calls
the same pure Task 1/Task 2 functions as the API. It will include at least five
cases per task, including one adversarial case per task: ambiguous ticket input
for Task 1 and an incomplete/low-evidence account context for Task 2.

Each fixture specifies either expected fields/enums or acceptance criteria.
The scorer will combine deterministic gates (valid schema/enums, required
retrieval evidence, source-only citations, direct quote for each Task 2 risk,
three required brief sections, deterministic repeatability) with an optional
versioned LLM-as-judge rubric. Each case receives `pass`/`fail`, a 0–1 quality
score, failures, and provenance. The runner writes a checked-in or generated
`eval_report.json` (and optionally a readable Markdown table) with aggregate
scores and per-case results. No external records are used as test fixtures.

## 11. Task 4 design-note plan

Write a roughly 600-word `DESIGN_NOTE.md` (or link it from the README) covering
the four required topics:

1. Three production failure modes, their observable signals, and mitigations:
   retrieval misses/unsupported responses, structured-output or model drift,
   and data/join quality failures.
2. A concrete latency-versus-quality decision: deterministic lexical
   pre-filtering and compact evidence packages before an LLM call; explain the
   smaller retrieval/model strategy if latency becomes the hard constraint.
3. Data sensitivity: minimize ticket/account fields sent to a model, redact or
   avoid contact details where possible, keep secrets in environment variables,
   use approved data-processing controls, and never log raw sensitive prompts
   or credentials.
4. Tenfold-volume scaling: cached corpus/indexes and asynchronous API workers
   initially; identify retrieval indexing, LLM throughput/cost, and evaluation
   runtime as likely first bottlenecks, then describe batching, vector/search
   infrastructure, queues, rate limits, and monitoring.

## 12. Required dependencies

Keep the application dependency set small and pin it in `requirements.txt` only
when implementation starts:

- Python standard library: JSON/date handling, filesystem access, hashing,
  deterministic lexical scoring, and logging.
- `fastapi`, `uvicorn`, and `pydantic`: lightweight typed REST interface and
  request/response validation.
- An LLM provider SDK (for example, `openai`) only when a configured model path
  is implemented; an `.env.example` will name the required key without values.
- `pytest`: local unit/evaluation-runner checks.

Do not add a database, vector database, scraper, embedding service, or data
library for this dataset size unless a later implementation need demonstrably
requires it.

## 13. Recommended implementation order

1. Create the project package, read-only loaders, schema models, indexes, and
   validation tests.
2. Implement deterministic knowledge-base parsing/retrieval with citation
   metadata and test it against known errors/topics.
3. Implement Task 1 pure triage function, structured result validation, then
   its API route and sample run.
4. Implement exact joining, injected 90-day filtering, Task 2 evidence builder,
   deterministic brief renderer, and account API route.
5. Build the evaluation fixtures, gates, scoring runner, and report.
6. Add `requirements.txt`, `.env.example`, setup/run instructions, samples,
   design note, and optional thin UI/CI only after the core functions work from
   a clean install.

## 14. Proposed application entry point

Use `src/main.py` as the single application entry point, exposing `app` for
FastAPI and supporting one documented command:

```powershell
uvicorn src.main:app --reload
```

The README will document this alongside direct module/function commands for the
evaluation harness. This gives a clean-install reviewer one obvious way to run
the service while preserving pure, testable application functions underneath.
