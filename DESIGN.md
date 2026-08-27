# Production Design Note

## 1. Failure Modes

The first realistic failure mode is an unsupported triage or account claim. The
deterministic Task 1 path can misclassify sparse or ambiguous prose, while the
optional Task 1 LLM path can return invalid or insufficiently grounded output.
The application detects this with Pydantic enum/schema validation, local
knowledge-base-path checks, and evaluation cases for ambiguous and adversarial
inputs. It mitigates the problem by returning no knowledge-base match unless an
exact error pattern or sufficiently specific heading match supports one; a
future production version should add sampled human review and metric-based
monitoring of overrides.

Second, source-data quality can fail joins and summaries. The supplied data
already demonstrates this: most ticket account IDs have no matching account,
and the few matching IDs can have different company names. The loader validates
record shapes and unique IDs at startup, Task 2 joins only exact account IDs,
and unknown accounts return a controlled 404. The brief explicitly calls out
zero exact-ID recent tickets as a possible data-linkage gap. In production, I
would add data-quality dashboards, upstream referential-integrity checks, and a
review queue rather than attempting fuzzy company-name joins.

Third, configuration or model availability can fail. A malformed `.env`,
missing local files, invalid timestamps, or an optional OpenAI request failure
can stop reliable output. The current code validates local JSON through Pydantic
and exposes controlled API errors for invalid requests and unavailable accounts.
Task 1 only calls an external model when `OPENAI_API_KEY` is configured; without
it, the deterministic path remains available. Production mitigation would add
request timeouts, retry policy with limits, uptime metrics, and an explicit
fallback-status field.

## 2. Latency vs Quality

The implementation trades broad retrieval recall for precision. It uses a small
in-process lexical scan of the nine supplied Markdown documents and only marks
a known issue when there is an exact documented error pattern or a specific
heading match. This can miss a vaguely described issue, but it avoids surfacing
an unrelated document as evidence. The latency cost is tiny at this corpus size
and avoids embedding generation, a vector database, and network calls. The
optional LLM route can improve language interpretation, but increases latency,
cost, and nondeterminism. If latency became the hard constraint, I would keep
the deterministic model as the default, pre-index tokens at startup, limit
retrieval to a single best chunk, and make LLM enrichment asynchronous or
optional rather than blocking the support response.

## 3. Data Sensitivity

Tickets and accounts may contain names, job titles, company names, usage,
commercial, support, and escalation information. Task 2 currently makes no
external API call. Task 1 sends the raw ticket and locally retrieved knowledge
base text to OpenAI only if an operator supplies `OPENAI_API_KEY`; otherwise it
uses local deterministic logic. The key is read from ignored `.env`; only empty
placeholder configuration is committed in `.env.example`. The implementation
does not redact prompts, encrypt application logs, or configure provider data
retention controls, so it must not claim those protections. It uses no live
customer data, web search, or external documentation: all facts originate in
the supplied synthetic files. A production implementation would minimize fields
sent to providers, redact PII, enforce access control and audit logs, apply
retention agreements, and use a secrets manager rather than a developer `.env`.

## 4. Scaling

At ten times the ticket volume, the first bottleneck is likely repeated
in-process JSON loading and linear lexical retrieval, followed by LLM/API
throughput when that option is enabled. The current dataset is small enough for
startup caching, but a larger deployment should parse and validate data once,
build a durable inverted or vector index only when retrieval quality warrants
it, and cache document chunks and account-ticket indexes. API workers can scale
horizontally behind a load balancer as long as their read-only indexes are
rebuilt consistently. External LLM calls need bounded concurrency, timeouts,
rate-limit handling, and caching of identical requests. Evaluation also grows:
the deterministic harness should run in CI on a representative regression set,
with broader suites sharded or scheduled so quality gates remain timely.
