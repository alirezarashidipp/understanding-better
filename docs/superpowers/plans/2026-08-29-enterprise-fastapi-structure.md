# Enterprise FastAPI Structure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the MRM Review POC to a professional `mrm_review` FastAPI package with Prompt-as-Code and standard executable/dependency files.

**Architecture:** Preserve the existing linear file → AI → validation → Excel workflow inside one focused package. FastAPI owns HTTP delivery, Pydantic owns contracts, direct functions own file and workflow operations, and two dedicated modules own prompts.

**Tech Stack:** Python 3.11+, FastAPI, Uvicorn, Jinja2, OpenAI Python SDK, Pydantic 2, openpyxl, python-dotenv

**Spec:** `docs/superpowers/specs/2026-08-29-enterprise-fastapi-structure-design.md`

## Global Constraints

- Do not add automated tests in this migration.
- Preserve all current MRM validation and Excel-output behavior.
- Do not expose or modify the value of `OPENAI_API_KEY`.
- Keep one package and avoid repository/service/factory layers beyond the FastAPI app factory.
- Remove the legacy raw extractor and old `input_extractor` package after the new package imports successfully.

---

### Task 1: Core package and Prompt-as-Code

**Files:**
- Create: `src/mrm_review/__init__.py`
- Create: `src/mrm_review/config.py`
- Create: `src/mrm_review/schemas.py`
- Create: `src/mrm_review/file_io.py`
- Create: `src/mrm_review/prompts/__init__.py`
- Create: `src/mrm_review/prompts/use_case.py`
- Create: `src/mrm_review/prompts/metric_review.py`
- Create: `src/mrm_review/ai_reviewer.py`
- Create: `src/mrm_review/workflow.py`

**Interfaces:**
- `Settings.from_env(root: Path) -> Settings`
- `read_qm_texts`, `read_metric_catalog`, `read_developer_metrics`
- `write_missing_metrics`, `write_review`
- `OpenAIReviewer.create_draft`, `OpenAIReviewer.complete_review`
- `start_review`, `finish_review`

- [ ] Copy current validated schemas and deterministic file behavior under the new package imports.
- [ ] Extract both OpenAI instruction strings into dedicated prompt constants.
- [ ] Import the new schemas, file I/O, AI reviewer, and workflow modules with `.venv/Scripts/python.exe`.

### Task 2: FastAPI web delivery and executable entry points

**Files:**
- Create: `src/mrm_review/api.py`
- Create: `src/mrm_review/cli.py`
- Create: `src/mrm_review/__main__.py`
- Create: `src/mrm_review/templates/index.html`
- Create: `src/mrm_review/static/styles.css`
- Create: `main.py`

**Interfaces:**
- `create_app(reviewer: AIReviewer | None = None, root: Path | None = None) -> FastAPI`
- `app: FastAPI` in root `main.py`
- `main() -> None` in `cli.py`

- [ ] Replace Flask routes with FastAPI GET/POST routes using `Request.form()` and `TemplateResponse`.
- [ ] Mount `/static`, serve the two allowed output files, and keep safe 400 error pages.
- [ ] Move inline CSS into the static stylesheet.
- [ ] Verify route names and methods through `app.routes` and fetch `/` with a running Uvicorn process.

### Task 3: Dependencies, docs, and cleanup

**Files:**
- Create: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `.env.example`
- Create: `docs/architecture.md`
- Modify: `pyproject.toml`
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `.gitignore`
- Delete: `src/input_extractor/`
- Delete: `tests/`
- Delete: `Output/extracted_data.json`

**Interfaces:**
- Runtime install: `python -m pip install -r requirements.txt`
- Development install: `python -m pip install -r requirements-dev.txt`

- [ ] Make `requirements.txt` the dynamic dependency source for `pyproject.toml`.
- [ ] Document setup, execution, package map, prompt locations, workflow, output files, and POC constraints.
- [ ] Delete the confirmed legacy extractor, old Flask package, obsolete tests, and generated legacy JSON.
- [ ] Reinstall editable package and run compile, import, `pip check`, route inspection, and HTTP smoke verification.
