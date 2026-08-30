# Conservative API Rendering Refactor

## Goal

Reduce repeated Jinja `TemplateResponse` construction in `src/mrm_review/api.py` without changing observable behavior, public routes, workflow state, prompts, schemas, or generated files.

## Scope

- Add one local `render_page()` helper inside `create_app()`.
- Render the `start`, `questions`, `understanding`, `result`, and `error` stages through that helper.
- Keep a small local `render_error()` wrapper so every error response retains HTTP status `400` and the existing context shape.
- Remove the one-caller module-level `_render_result()` helper.
- Remove the module-level `_render_error()` helper and its repeated `templates` argument.
- Remove schema imports used only by the deleted result helper.

## Behavior That Must Not Change

- Route paths, methods, names, and response classes.
- HTML template name and context keys for every stage.
- User-visible error messages and HTTP status codes.
- Draft and refined in-memory session transitions.
- OpenAI calls, prompts, payloads, and Pydantic validation.
- Input and output file handling.
- Download allowlist behavior.
- Frontend HTML, CSS, and JavaScript.

## Verification

- Run Python compile and import checks.
- Run Ruff and dependency checks.
- Confirm every expected route remains registered.
- Confirm `/`, `/health`, `/static/styles.css`, and `/static/app.js` return `200`.
- Exercise the start, refine, result, and error render stages with a deterministic fake reviewer so no OpenAI request is sent.
- Confirm no generated cache directories remain in the project.

## Expected Reduction

Approximately 18 production lines removed, with no new production file and no behavior change.
