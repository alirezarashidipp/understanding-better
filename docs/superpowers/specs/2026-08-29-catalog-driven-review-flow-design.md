# Catalog-Driven MRM Review Flow

## Goal

Use `metrics/metrics.md` as the only source of truth for understanding the
system category and selecting metrics. The reviewer must see the updated use
case and business-oriented flow before metric review begins.

## Catalog structure

The application parses the existing hierarchy in `metrics.md`:

1. One of the six top-level categories
2. A `Main Subcategory` belonging to that category
3. The closest `Application` belonging to that category
4. The approved Metrics belonging to that category

No category, subcategory, application, or metric mapping is hard-coded in
Python. Values selected by the LLM must exactly match values parsed from
`metrics.md`.

## Review stages

### 1. Initial understanding

The application reads all `QM-*.txt` files and the complete catalog hierarchy.
The LLM returns:

- Business Use Case
- Simple input, processing, and output flow
- One exact top-level catalog category
- One exact Main Subcategory from that category
- The closest exact Application from that category
- Zero to four clarification questions

The questions are not predefined. The LLM asks a question only when missing or
ambiguous information would materially improve its understanding of the system,
its catalog classification, its business-risk flow, or the later metric
selection. It must not ask questions merely to collect optional detail.

Every question supports either a user answer or `Skip`. Zero questions is a
valid result when the TXT already provides enough information.

### 2. Refined MRM understanding

When the reviewer selects `Next`, the application sends all answers and skips
back to the LLM. This happens even when every question was skipped or no
questions were generated.

The LLM returns an updated final use-case understanding. The UI displays:

- Business Use Case
- Selected main category
- Selected Main Subcategory
- Closest Application
- A short explanation written for an MRM reviewer
- A simple, business/risk-oriented Input → Processing → Output flow

The reviewer acknowledges this screen with a button labelled exactly `OK`.
The UI must not label this action `Confirm` or `Approve`.

### 3. Metric review

Only after `OK`, the application passes the Metrics belonging to the selected
top-level category to the LLM. Metrics from the other five categories are not
eligible for selection.

The LLM then:

- Selects required expected Metrics from the eligible category
- Creates short Test Objectives and Calculation Methods
- Reviews every developer Metric from `MRM_*.xlsx`
- Assesses Test Objective and Calculation Method independently

The existing status and output contracts remain unchanged. Missing required
Metrics are written only to `Output/missing_metrics.xlsx`; developer Metric
reviews are written to `Output/mrm_review.xlsx`.

## Validation rules

Pydantic and deterministic workflow checks enforce that:

- The selected category exists in the parsed catalog.
- The selected subcategory belongs to the selected category.
- The selected application belongs to the selected category.
- Every AI-expected Metric belongs to the selected category.
- Every developer Metric is reviewed exactly once.
- Developer Test Objective and Calculation Method text is preserved.
- Field statuses and revision requirements follow the existing contract.

An invalid LLM selection stops the workflow with a concise reviewer-facing
error. The application never silently substitutes a value.

## Application state and API flow

Runtime state remains in memory for this POC:

1. `POST /start` creates the initial understanding and questions.
2. `POST /refine` applies answers/skips and creates the final MRM explanation.
3. `POST /review` handles the `OK` action, performs metric review, and writes
   both Excel outputs.

No database, authentication, background worker, or multi-agent system is added.

## Prompt as code

Provider instructions remain outside workflow code:

- `prompts/use_case.py` — initial understanding and optional questions
- `prompts/use_case_refinement.py` — updated MRM explanation and flow
- `prompts/metric_review.py` — metric selection and developer review

Each prompt receives structured JSON containing only the data needed for its
stage.

## UI behavior

The existing single FastAPI/Jinja page remains. It renders four simple states:

1. Ready to review
2. Clarification questions, when present
3. Final MRM understanding with the `OK` button
4. Completed review with output download links

If no clarification questions exist, the second state still provides `Next` so
the final MRM understanding is generated and shown before metric review.

## Verification for this iteration

Per the current project request, no test files are added. Verification uses:

- Ruff lint and format checks
- Python compilation
- Deterministic parser and validation harnesses without OpenAI
- FastAPI route assertions
- HTTP smoke checks for the rendered stages where live AI is not required
