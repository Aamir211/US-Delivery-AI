# Prompt Changelog

## `triage_v1`

- Purpose: produces the structured Task 1 ticket-triage result.
- Initial version: restricts reasoning, documentation paths, and draft replies to
  the supplied ticket and locally retrieved knowledge-base evidence.

## `account_summary_v1`

- Purpose: defines the Task 2 account-health summary contract.
- Initial version: requires only supplied account/exact-ID ticket evidence and
  exact ticket substrings whenever a ticket-based risk is reported.
