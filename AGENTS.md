# AGENTS.md

## Project purpose

This is a small local FastAPI MVP that supports an MRM reviewer with use-case understanding and metric review.

## Start here

- At the start of a new session, read `README.md` for setup and user flow and `docs/architecture.md` for runtime flow and module boundaries before project-wide or workflow changes.
- Inspect the live files relevant to the task; treat the live implementation as current when documentation has drifted.

## Required behavior

- Read use-case content only from `QM-*.txt`.
- Read exactly one developer workbook named `MRM_*.xlsx`.
- Treat `metrics/metrics.md` as the only approved metric catalog.
- Select the main category, subcategory, closest application, and Metrics only from values parsed from `metrics.md`.
- Require the initial use-case draft to include `understanding_confidence` as an integer from 0 to 100 and show it before clarification questions.
- Ask zero to four use-case questions only when they materially improve system understanding and always support Skip.
- Run Call 2 only when at least one non-blank, non-skipped answer exists.
- When Call 2 is skipped, carry the Call 1 result forward unchanged.
- Start metric review only after a button labelled exactly `OK` is selected.
- Never accept an AI-expected Metric outside the selected catalog category.
- Assess Test Objective and Calculation Method / Formula independently.
- Use only `OK`, `IT IS EMPTY`, or `NEEDS REVISION` for field status.
- Require a short reason and corrected text for `NEEDS REVISION`.
- Limit questions for each reviewed field to three.
- Show final results in the browser; never write review output files.
- Never print, log, return, or commit `OPENAI_API_KEY`.
- Load `OPENAI_API_KEY`, `OPENAI_MODEL`, and `OPENAI_TEMPERATURE` only from the environment or `.env.local`.
- Give an invalid structured result at most one repair call with concise validation feedback;
  never automatically repair provider authentication, billing, rate-limit, or connection errors.
- Keep original developer Objective and Formula values in `system_metrics` for validation.
- Match returned catalog values case-insensitively, then normalize them to exact source spelling.
- Preserve the current refinement or metric-review stage after failure so it can be retried.

## OpenAI flow

1. Call 1 sends exact QM text, exact `metrics.md` Markdown, and the three-column workbook rows.
2. Call 2 sends answered question/answer pairs and the previous output; skip it when no answer exists.
3. After exact `OK`, Call 3 returns expected metrics and independent Objective and Formula assessments for browser display.

All calls use the same top-level `LLMInput` and `LLMOutput` schemas. Fields owned by later calls stay empty until that call.

## Architecture

- Keep production modules directly under `src/`; do not add a redundant package directory.
- Keep provider prompts as version-controlled `.yml` files under root `prompts/` and load them through `src/prompt_loader.py`; do not inline provider prompt prose in Python.
- Keep Pydantic contracts in `schemas.py`.
- Keep user TXT/workbook reading in `user_input_reader.py` and raw catalog reading plus internal
  validation parsing in `metric_catalog_reader.py`.
- Keep OpenAI client construction and authentication in `openai_connection.py`; changing the
  supported authentication mechanism must not require changes to review logic.
- Keep OpenAI calls in `ai_reviewer.py` and orchestration in `workflow.py`.
- Keep FastAPI routes in `api.py` and execution arguments in `cli.py`.
- Keep frontend assets together under root `templates/`: `index.html`, `styles.css`, and `app.js`.
- Keep the existing `create_app()` FastAPI application factory; do not add repository, service, factory abstraction, database, authentication, or multi-agent layers.

## Code style

- Prefer simple, explicit, linear code.
- Keep the main data flow visible.
- Use concrete names and small focused functions.
- Validate all AI output with Pydantic.

## Verification

- Automated tests are intentionally out of scope for the current migration.
- Do not create a `tests/` directory unless the user requests tests again.
- Before claiming completion, run compile, import, lint, dependency, route, and HTTP smoke checks.
- Never include real input documents or `.env.local` in version control.
