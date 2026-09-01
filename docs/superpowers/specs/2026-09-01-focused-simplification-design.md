# Focused Simplification Design

## Goal

Make the local FastAPI MRM review project substantially easier to read without changing its user-visible review behavior, OpenAI call sequence, validation rules, or security boundaries.

## Behavior that must remain unchanged

- Accept one `QM-*.txt` file and one `MRM_*.xlsx` workbook.
- Use `metrics/metrics.md` as the only approved metric catalog.
- Run Call 1, optional Call 2, mandatory Call 3, exact `OK`, then Call 4.
- Skip Call 2 when no non-blank, non-skipped answer exists.
- Preserve the current stage when refinement or metric review fails.
- Allow at most one structured-output repair attempt and never repair provider authentication, billing, rate-limit, or connection errors.
- Normalize catalog values case-insensitively to their exact source spelling.
- Keep original workbook Objective and Formula values for server-side validation.
- Show results only in the browser and never create review output files.
- Keep all provider prompt prose in YAML files under `prompts/`.
- Never expose `OPENAI_API_KEY`.

## Chosen approach

Use focused simplification instead of either a backend-only cleanup or a large module merge. Keep the existing module boundaries when they represent a real responsibility, but remove configuration and abstractions that only hide fixed MVP rules.

## Backend changes

### Fixed input contracts

Delete `input_format.yml`. Move its fixed filename patterns, workbook header aliases, empty placeholder, and catalog section labels into clearly named constants beside the readers that use them.

Change `read_user_inputs` to accept one QM upload and one workbook upload directly. Remove the `Sequence` types, one-item list construction, and `_only_file` helper. FastAPI already accepts exactly one file for each field.

### Prompt loading

Keep prompt instructions in the existing four YAML files. Remove the unused `version` property and its validation because no runtime behavior reads or exposes it.

### Packaging

Remove the console-script declaration and `cli` module entry because `cli.py` does not exist. Ensure every live module required by the application, including `views.py`, is included in the explicit module list.

### Workflow and API

Keep the three `langchain-core` Runnables, four named OpenAI calls, `PendingReview`, route-stage checks, public provider-error mapping, structured-output repair limit, and catalog/workbook validation. These are required behavior, not accidental complexity.

Only make local naming or formatting improvements in these modules when they reduce cognitive load without changing control flow.

## Frontend changes

Keep `templates/index.html`, `templates/styles.css`, and `templates/app.js` as plain server-rendered HTML, CSS, and JavaScript.

Reduce the page to the information required for the four stages:

1. Upload the QM text and developer workbook.
2. Show confidence and clarification questions with Skip.
3. Show the final MRM explanation and flow with the exact `OK` button.
4. Show expected metrics and independent Objective and Formula reviews.

Remove decorative enterprise branding, duplicated summaries, numbered ornamental elements, and CSS rules that exist only to support those decorations. Retain responsive layout, readable error messages, form labels, loading feedback, disabled duplicate submission, status visibility, and accessible semantic markup.

## Documentation

Create a concise `docs/architecture.md` that describes the live browser-to-route-to-workflow-to-OpenAI flow and the responsibility of each production file. Do not modify or delete the existing untracked architecture visualization artifacts.

Update `README.md` only where filenames, packaging, or the simplified UI description would otherwise become inaccurate.

## Verification

Automated tests remain out of scope. Before completion, run:

- Python compilation for `main.py` and `src/`
- Import checks for every production module
- Ruff lint checks
- `pip check`
- Package build or equivalent package-content verification
- Route registration assertions
- HTTP smoke checks for `/`, `/health`, `/static/styles.css`, and `/api/docs`
- A deterministic fake-reviewer flow covering Start, skipped refinement, exact `OK`, Call 4, and same-stage failure retry
- `git diff --check` and a final scan confirming provider prompt prose remains outside Python

Do not make a live paid OpenAI request during deterministic verification.

## Success criteria

- The full review behavior and required guardrails remain intact.
- The primary data flow is readable from the route through workflow validation to the OpenAI call.
- Fixed rules are visible near the code that enforces them.
- Frontend code is materially shorter and remains usable on desktop and mobile.
- No user-owned uncommitted file or unrelated artifact is modified.
- All required verification commands pass, with any unrun live-provider check explicitly reported as unverified.
