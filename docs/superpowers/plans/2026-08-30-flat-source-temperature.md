# Flat Source and OpenAI Temperature Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Flatten production modules under `src/`, move YAML prompts to root `prompts/`, and apply one validated temperature to every structured OpenAI call.

**Architecture:** The existing focused responsibilities remain unchanged; only the redundant Python package directory is removed. A concrete `prompt_loader.py` reads root YAML files, and `AppSettings` carries one float temperature into `OpenAIReviewer`.

**Tech Stack:** Python 3.14 development environment with Python >=3.11 support, FastAPI, OpenAI Python SDK, Pydantic, PyYAML, setuptools.

**Spec:** `docs/superpowers/specs/2026-08-30-flat-source-temperature-design.md`

## Global Constraints

- Keep one concrete module per existing responsibility; add no wrapper, factory, service, or compatibility package.
- Keep all provider prompt prose in root `prompts/*.yml`.
- Accept `OPENAI_TEMPERATURE` only from environment or `.env.local`, default it to `0.0`, and require `0.0 <= value <= 2.0`.
- Create no automated test files; use deterministic inline harnesses and the project verification commands.
- Preserve upload validation, catalog guardrails, `Next -> refined explanation -> OK`, output pairing, and safe provider errors.

---

### Task 1: Flatten production modules

**Files:**
- Move: `src/mrm_review/{api,workflow,input_reader,output_writer,openai_connection,ai_reviewer,config,schemas,cli}.py` to `src/`
- Delete: `src/mrm_review/__init__.py`, `src/mrm_review/__main__.py`
- Modify: `main.py`, `pyproject.toml`, and every moved module import

**Interfaces:**
- Consumes: Existing public functions and Pydantic models unchanged.
- Produces: Top-level import paths such as `from api import create_app` and console target `cli:main`.

- [ ] Move the nine responsibility modules directly into `src/`.
- [ ] Replace every `from mrm_review...` import with its flat module import.
- [ ] Set `main.py` to import `create_app` from `api` and execution `main` from `cli`.
- [ ] Set `cli.main()` default application path to `api:create_app`.
- [ ] Replace package discovery/package data with explicit flat `py-modules` in `pyproject.toml`.
- [ ] Reinstall editable packaging and verify `python -c "from api import create_app"` succeeds.

### Task 2: Move and load root prompts

**Files:**
- Move: `src/mrm_review/prompts/*.yml` to `prompts/`
- Create: `src/prompt_loader.py`
- Delete: `src/mrm_review/prompts/__init__.py`
- Modify: `src/ai_reviewer.py`

**Interfaces:**
- Produces: `load_prompt(filename: str) -> str` resolving `prompts/` from the repository root.
- Consumes: The existing three YAML filenames and their `version`/`instructions` contract.

- [ ] Move the three versioned YAML prompt files into root `prompts/`.
- [ ] Implement `PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"` in `src/prompt_loader.py` and preserve YAML validation.
- [ ] Import `load_prompt` from `prompt_loader` in `src/ai_reviewer.py`.
- [ ] Run an inline harness that loads all three prompts and rejects a missing prompt path.

### Task 3: Configure temperature

**Files:**
- Modify: `.env.example`, `src/config.py`, `src/ai_reviewer.py`, `src/api.py`

**Interfaces:**
- Produces: `AppSettings.openai_temperature: float` and `OpenAIReviewer(client, model, temperature)`.
- Consumes: Optional environment value `OPENAI_TEMPERATURE`.

- [ ] Add `OPENAI_TEMPERATURE=0.0` to `.env.example`.
- [ ] Parse the environment value as float in `AppSettings.from_env()`, reject non-numeric and out-of-range values, and default omission to `0.0`.
- [ ] Store temperature on `OpenAIReviewer` and pass `temperature=self.temperature` to each `responses.parse` call.
- [ ] Pass `settings.openai_temperature` during default reviewer composition in `src/api.py`.
- [ ] Run an inline fake-client harness proving all three calls receive the configured value and invalid config is rejected.

### Task 4: Align contracts and verify the application

**Files:**
- Modify: `AGENTS.md`, `README.md`, `docs/architecture.md`, `specs/001-focused-mvp-boundaries/{plan,research,spec,tasks}.md`
- Verify: `main.py`, `src/`, `prompts/`, live server

**Interfaces:**
- Produces: Documentation and Spec Kit artifacts matching the live flat layout and temperature contract.

- [ ] Replace stale `src/mrm_review/` and packaged-prompt references in active documentation.
- [ ] Append and complete traceable implementation tasks in the active Spec Kit `tasks.md`.
- [ ] Run Ruff, compileall, editable installation, pip check, flat import, route, prompt, temperature, deterministic HTTP, and live health checks.
- [ ] Confirm `src/mrm_review/` is absent and no stale `mrm_review` import remains outside historical documents.
- [ ] Restart the local server, commit the verified change, scan staged content for secrets/runtime inputs, and push `main` without force.
