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
- Show the refined MRM explanation and flow after Next, even when every question is skipped or no question exists.
- Start metric review only after a button labelled exactly `OK` is selected.
- Never accept an AI-expected Metric outside the selected catalog category.
- Assess Test Objective and Calculation Method / Formula independently.
- Use only `OK`, `IT IS EMPTY`, or `NEEDS REVISION` for field status.
- Require a short reason and corrected text for `NEEDS REVISION`.
- Limit questions for each reviewed field to three.
- Write absent required metrics only to the current `Output/missing_metrics_<id>.xlsx` file.
- Never print, log, return, or commit `OPENAI_API_KEY`.
- Load `OPENAI_API_KEY` and `OPENAI_MODEL` only from the environment or `.env.local`.

## OpenAI flow

1. Call 1 sends the QM source text and the full parsed catalog, then returns the initial use-case draft, `understanding_confidence`, and zero to four clarification questions.
2. Call 2 sends the source text, full initial draft, clarification answers, and full parsed catalog, then returns the refined use case, MRM explanation, and business/risk flow.
3. After the user selects exactly `OK`, Call 3 sends the refined use case, only the final selected category's catalog metrics, and the developer workbook metrics, then returns expected metrics and independent Objective and Formula assessments.

## Architecture

- Keep production code under `src/mrm_review/`.
- Keep provider prompts as version-controlled `.yml` files under `src/mrm_review/prompts/` and load them through `prompts/__init__.py`; do not inline provider prompt prose in Python.
- Keep Pydantic contracts in `schemas.py`.
- Keep input reading and validation in `input_reader.py` and output workbook creation and
  storage in `output_writer.py`.
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
