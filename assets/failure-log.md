# Failure Log

Use this file for reusable failures only. Do not dump transient debugging notes here.

## Entries

- Date:
  Task or spec:
  Symptom:
  Root cause class:
    Use one of `docs`, `constraints`, `tools`, `verification`, or `other`.
  What was missing:
  Permanent prevention:
  Status:
    Use `open`, `patched`, or `retired`.

## Review Rule

- If the same type of failure appears twice, strengthen the harness instead of writing a third note.
- Prefer prevention changes such as:
  - better spec fields
  - verification rules
  - repo scripts
  - tighter AGENTS guidance
  - task templates
