# Conservative API Rendering Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove repeated Jinja response construction from `api.py` while preserving every observable application behavior.

**Architecture:** Keep all routes and state inside the existing FastAPI application factory. Add one local page-rendering helper and one local error wrapper inside `create_app()`, then delete the two module-level rendering helpers.

**Tech Stack:** Python 3.11+, FastAPI, Jinja2, Ruff, HTTPX ASGI transport

**Spec:** `docs/superpowers/specs/2026-08-30-conservative-api-rendering-refactor-design.md`

## Global Constraints

- Preserve route paths, methods, names, and response classes.
- Preserve template context keys, error messages, and HTTP status codes.
- Do not change workflow state, OpenAI calls, prompts, schemas, file handling, downloads, or frontend files.
- Do not create a `tests/` directory; automated tests are out of scope for the current migration.
- Do not create a commit because the workspace is not a Git repository.
- Keep the implementation simple, explicit, and local to `src/mrm_review/api.py`.

---

### Task 1: Consolidate page rendering

**Files:**
- Modify: `src/mrm_review/api.py:12-199`
- Verify: one-off Python contract and HTTP smoke commands only; create no test file

**Interfaces:**
- Consumes: the existing local `templates: Jinja2Templates` instance and route `Request` objects.
- Produces: local `render_page(request, stage, *, status_code=200, **context) -> HTMLResponse` and `render_error(request, message) -> HTMLResponse` callables available to the route closures.

- [ ] **Step 1: Run the source-shape contract to verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -B -c "from pathlib import Path; source=Path('src/mrm_review/api.py').read_text(encoding='utf-8'); assert 'def render_page(' in source; assert 'def _render_result(' not in source"
```

Expected: FAIL because `render_page` does not exist and `_render_result` still exists.

- [ ] **Step 2: Remove imports needed only by `_render_result`**

Change the schema import block from:

```python
from mrm_review.schemas import (
    ClarificationAnswer,
    MetricReviewResult,
    PendingReview,
    ReadyForMetricReview,
    RefinedUseCase,
    ReviewPaths,
)
```

to:

```python
from mrm_review.schemas import (
    ClarificationAnswer,
    PendingReview,
    ReadyForMetricReview,
    ReviewPaths,
)
```

- [ ] **Step 3: Add the local rendering helpers**

Immediately after the `draft_states` and `refined_states` declarations inside `create_app()`, add:

```python
    def render_page(
        request: Request,
        stage: str,
        *,
        status_code: int = 200,
        **context: object,
    ) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"stage": stage, **context},
            status_code=status_code,
        )

    def render_error(request: Request, message: str) -> HTMLResponse:
        return render_page(request, "error", status_code=400, error=message)
```

- [ ] **Step 4: Replace repeated rendering calls**

Use these exact route return shapes:

```python
return render_page(request, "start")
```

```python
return render_page(
    request,
    "questions",
    review_id=review_id,
    draft=pending.draft,
)
```

```python
return render_page(
    request,
    "understanding",
    review_id=review_id,
    refined=ready.refined,
)
```

```python
return render_page(
    request,
    "result",
    refined=ready.refined,
    result=result,
)
```

Replace every `_render_error(templates, request, message)` or multiline equivalent with:

```python
return render_error(request, message)
```

Keep every existing error message unchanged.

- [ ] **Step 5: Delete the old module-level rendering helpers**

Delete `_render_result()` and `_render_error()` from the end of `api.py`. Nothing replaces them outside `create_app()`.

- [ ] **Step 6: Run the source-shape contract to verify GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -B -c "from pathlib import Path; source=Path('src/mrm_review/api.py').read_text(encoding='utf-8'); assert 'def render_page(' in source; assert 'def _render_result(' not in source; assert 'def _render_error(' not in source; print('Rendering simplification: OK')"
```

Expected: `Rendering simplification: OK`.

- [ ] **Step 7: Run complete behavior-preservation verification**

Run Python syntax compilation without writing cache files, import `main` and the production modules, run `ruff check --no-cache src main.py`, and run `python -m pip check`.

Then create the app with a deterministic fake reviewer and HTTPX ASGI transport. Verify:

```text
GET  /                       -> 200
GET  /health                 -> 200
GET  /static/styles.css      -> 200
GET  /static/app.js          -> 200
POST /start                  -> questions stage
POST /refine                 -> understanding stage
POST /review                 -> result stage
invalid review session       -> 400 with the existing error message
```

The fake reviewer must return valid `UseCaseDraft`, `RefinedUseCase`, and `MetricReviewResult` objects and must not call OpenAI. Use temporary business inputs and outputs so the checked-in runtime files are not modified.

Expected: all assertions pass, Ruff reports `All checks passed!`, pip reports no broken requirements, and no project cache directory is created.
