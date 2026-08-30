<!--
Sync Impact Report
- Version change: template -> 1.0.0
- Added principles: Visible Linear Flow; One Reason to Change; Catalog and Schema Guardrails;
  Replaceable OpenAI Connection; Minimal Local MVP
- Added sections: Product and Data Constraints; Delivery and Verification
- Removed sections: none
- Templates requiring updates:
  - updated: .specify/templates/plan-template.md
  - reviewed, no change required: .specify/templates/spec-template.md
  - updated: .specify/templates/tasks-template.md
- Follow-up TODOs: none
-->
# MRM Model Review Constitution

## Core Principles

### I. Visible Linear Flow
Production code MUST make the primary flow visible from uploaded inputs through use-case
understanding, clarification, approval, metric review, and downloadable outputs. Prefer
simple functions, concrete names, and direct calls over deep nesting, generic frameworks,
or hidden orchestration. Complexity requires a current, demonstrated need.

### II. One Reason to Change
Input reading and validation MUST live in `input_reader.py`. Workbook creation and output
storage MUST live in `output_writer.py`. OpenAI client construction and authentication MUST
live in `openai_connection.py`. Provider request payloads and structured responses MUST remain
in `ai_reviewer.py`, while business sequencing and guardrails MUST remain in `workflow.py`.
No repository, service, factory hierarchy, database, authentication, or multi-agent layer may
be added without an approved requirement that cannot be met by the focused modules.

### III. Catalog and Schema Guardrails
`metrics/metrics.md` MUST remain the only approved metric catalog. Category, subcategory,
application, and expected Metric values MUST be parsed from it rather than hard-coded. All AI
outputs MUST be validated with Pydantic before business decisions or file writes. The workflow
MUST preserve the exact `Next` then refined understanding then `OK` gate, and Objective and
Formula assessments MUST remain independent.

### IV. Replaceable OpenAI Connection
OpenAI authentication and client construction MUST be isolated so changing from an API key to
another supported token mechanism requires changing only `openai_connection.py` and runtime
configuration. Provider prompt prose MUST remain in version-controlled YAML files. Secrets MUST
come only from the environment or `.env.local` and MUST never be printed, logged, returned, or
committed. Speculative provider implementations and generic provider factories are prohibited.

### V. Minimal Local MVP
The MVP MUST target one local reviewer, exactly one uploaded `QM-*.txt`, and exactly one uploaded
`MRM_*.xlsx` per review. It MUST not require a database or user authentication. Each completed
review MUST retain its two output workbooks as uniquely named files directly under `Output/`,
without per-review directories or overwriting earlier results. Features outside this scope are
deferred until validated by observed user need.

## Product and Data Constraints

- Use-case content MUST be read only from the uploaded `QM-*.txt` file.
- Developer metrics MUST be read from exactly one uploaded `MRM_*.xlsx` workbook.
- Only the expected workbook headers and explicitly documented legacy aliases are accepted.
- Clarification questions MUST number zero to four, be material to system understanding, and
  support Skip.
- Field statuses MUST be exactly `OK`, `IT IS EMPTY`, or `NEEDS REVISION`; revisions require a
  short reason and corrected text, with at most three questions per field.
- Only absent required metrics may be written to the missing-metrics workbook.
- Existing public route behavior and validated business guardrails MUST be preserved unless a
  feature specification explicitly changes them.

## Delivery and Verification

Every feature MUST proceed through the active Spec Kit artifacts before implementation:
specification, clarification when material ambiguity remains, plan, requirements checklist,
tasks, consistency analysis, implementation, and convergence. Changes MUST be delivered in small,
observable increments. Automated test files and a `tests/` directory remain out of scope until the
user explicitly changes that decision. Before completion, run lint, formatting or style checks,
Python compilation/import checks, dependency checks, catalog and workbook validation, route
inspection, and deterministic HTTP smoke scenarios without a live OpenAI request. A live provider
call is optional and MUST be explicitly reported rather than implied.

## Governance

This constitution governs feature specifications, plans, tasks, and implementation. Any conflict
MUST be resolved in favor of this document. Amendments require an explicit user decision, a Sync
Impact Report, semantic versioning, and propagation to dependent Spec Kit templates. Every plan
and completion review MUST check all five principles. Constitution violations require either a
design change or an explicit amendment; convenience is not an acceptable exception.

**Version**: 1.0.0 | **Ratified**: 2026-08-30 | **Last Amended**: 2026-08-30
