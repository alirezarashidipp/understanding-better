# MRM Model Review POC Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the existing extractor into a local Flask POC that produces an MRM use-case review and two validated Excel outputs.

**Architecture:** Deterministic Python functions read and validate files, while two OpenAI Structured Output calls handle interpretation. A thin Flask page presents the two-step review, and a linear orchestration function writes final workbooks only after validating AI metric names against the approved catalog.

**Tech Stack:** Python 3.11+, Flask, OpenAI Python SDK, Pydantic 2, openpyxl, python-dotenv, pytest

**Spec:** `docs/superpowers/specs/2026-08-28-mrm-model-review-design.md`

## Global Constraints

- Read only `QM-*.txt` for use-case content and one `MRM_*.xlsx` for developer metrics.
- Use only metric names parsed from `metrics/metrics.md` level-two headings.
- Ask zero to four short necessary questions, each answerable or skippable.
- Keep frontend, runtime state, and architecture minimal; add no authentication, database, multi-agent system, PDF, or complex UI.
- Never expose `OPENAI_API_KEY`; load the API key and model from `.env.local`.
- Tests must not call the live OpenAI API.

---

### Task 1: File contracts and Excel output

**Files:**
- Create: `src/input_extractor/files.py`
- Modify: `src/input_extractor/models.py`
- Test: `tests/test_review_files.py`

**Interfaces:**
- Produces: `read_qm_texts(input_dir: Path) -> str`
- Produces: `read_metric_catalog(path: Path) -> list[MetricCatalogItem]`
- Produces: `read_developer_metrics(input_dir: Path) -> list[DeveloperMetric]`
- Produces: `write_missing_metrics(path: Path, metrics: list[ExpectedMetric]) -> None`
- Produces: `write_review(path: Path, rows: list[MetricReview]) -> None`

- [ ] Write tests using `QM-one.txt`, ignored TXT files, heading-based metric Markdown, and a developer workbook with the required three columns.
- [ ] Run `python -m pytest tests/test_review_files.py -v` and verify missing interfaces fail.
- [ ] Implement direct readers and workbook writers with explicit missing-file and header errors.
- [ ] Re-run the file tests and verify they pass.

### Task 2: AI contracts and review workflow

**Files:**
- Create: `src/input_extractor/ai_review.py`
- Create: `src/input_extractor/review.py`
- Modify: `src/input_extractor/models.py`
- Test: `tests/test_review_workflow.py`

**Interfaces:**
- Produces: `OpenAIReviewer.create_draft(source_text: str) -> UseCaseDraft`
- Produces: `OpenAIReviewer.complete_review(...) -> FinalReview`
- Produces: `start_review(paths: ReviewPaths, reviewer: AIReviewer) -> PendingReview`
- Produces: `finish_review(pending: PendingReview, answers: list[ClarificationAnswer], reviewer: AIReviewer) -> FinalReview`

- [ ] Write fake-AI tests for zero-to-four questions, update inputs, catalog-name rejection, and both workbook outputs.
- [ ] Run `python -m pytest tests/test_review_workflow.py -v` and verify missing workflow modules fail.
- [ ] Implement Pydantic contracts, two direct `responses.parse` calls, environment loading, and linear orchestration.
- [ ] Re-run workflow tests and verify they pass.

### Task 3: Minimal Flask frontend

**Files:**
- Create: `src/input_extractor/web.py`
- Create: `src/input_extractor/templates/index.html`
- Test: `tests/test_web.py`

**Interfaces:**
- Produces: `create_app(reviewer: AIReviewer | None = None, root: Path | None = None) -> Flask`
- Produces: `python -m input_extractor.web`

- [ ] Write Flask-client tests for the start page, clarification form with Skip, final result, and safe error display.
- [ ] Run `python -m pytest tests/test_web.py -v` and verify missing web module fails.
- [ ] Implement three small routes and one responsive HTML template without JavaScript frameworks.
- [ ] Re-run web tests and verify they pass.

### Task 4: Setup, documentation, and verification

**Files:**
- Modify: `pyproject.toml`
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `.gitignore`
- Create: `metrics/.gitkeep`

**Interfaces:**
- Produces: editable installation and documented local startup command

- [ ] Add Flask, OpenAI, and python-dotenv dependencies and refresh the editable install in `.venv`.
- [ ] Document input formats, metric catalog headings, developer workbook headers, launch command, output files, AI boundaries, and POC limitations.
- [ ] Run `python -m pytest -v`, `python -m compileall -q src tests`, and `.venv` `pip check`.
- [ ] Start the Flask app with a fake reviewer for a local HTTP smoke test; do not spend API tokens when real inputs are absent.
