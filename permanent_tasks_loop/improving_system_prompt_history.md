# System Prompt Iteration History

## 2026-03-22 Iteration 1

- Status: rejected
- Target model: `glm-4.7-flash:latest`
- Prompt change: added an "indirect matches are clues, not final answers" rule, initially with benchmark-shaped examples, then generalized the wording before screening.
- Reason: tried to improve cases where GLM stopped on intermediate evidence or path-only hits instead of confirming the actual answer file.
- Previous full GLM score: `90/125`
- Screening subset:
  - cases: `faraday_signed_msa`, `redwood_signed_msa`, `northquay_scanner`, `shipment_7724_status_from_cause`, `northstar_owner`, `site_alias_note`, `personal_bash_retry`, `personal_read_backslashes`, `personal_history_redact`
  - previous baseline from the last full GLM report: `0/9`
- new score: `1/9`
- Decision: revert
- Notes: the revision was not strong enough to justify a full rerun, and the first draft also drifted into benchmark-shaped wording that is now explicitly banned by the loop spec.

## 2026-03-22 Iteration 2

- Status: rejected
- Target model: `glm-4.7-flash:latest`
- Prompt change: added a general rule to prefer distinctive clue terms over broad document or relationship words.
- Reason: tried to reduce GLM's tendency to search on generic terms like `signed`, `history`, or `note` instead of rarer user clues.
- Previous full GLM score: `90/125`
- Screening subset:
  - cases: `faraday_signed_msa`, `redwood_signed_msa`, `northquay_scanner`, `shipment_7724_status_from_cause`, `northstar_owner`, `site_alias_note`, `personal_bash_retry`, `personal_read_backslashes`, `personal_history_redact`
  - previous baseline from the last full GLM report: `0/9`
  - new score: `3/9`
- New full GLM score: `88/125`
- Decision: revert
- Notes: the revision improved some contract-style disambiguation cases, but the full 125-case run regressed overall relative to the validated prompt, so the system prompt was reverted to the prior accepted version.
