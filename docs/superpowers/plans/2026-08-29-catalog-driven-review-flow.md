# Catalog-Driven Review Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `metrics/metrics.md` the sole source for system classification and eligible Metrics, and require the reviewer to see the refined MRM explanation and flow before selecting `OK` to begin metric review.

**Architecture:** Parse the Markdown catalog into category objects containing their own subcategories, applications, and Metrics. Split the current two-stage workflow into three explicit AI operations—initial understanding, refinement, and metric review—with independent in-memory states and Pydantic contracts.

**Tech Stack:** Python 3.14, FastAPI, Jinja2, Pydantic v2, OpenAI Responses API, openpyxl, Ruff

**Spec:** `docs/superpowers/specs/2026-08-29-catalog-driven-review-flow-design.md`

## Global Constraints

- `metrics/metrics.md` is the only source of category, subcategory, application, and Metric names.
- The LLM may ask zero to four questions only when they materially improve system understanding.
- Every question supports an answer or `Skip`.
- The refined MRM explanation and flow must be shown before metric review.
- The acknowledgement button is labelled exactly `OK`, never `Confirm` or `Approve`.
- Only Metrics belonging to the selected top-level category are eligible.
- Runtime state remains in memory; no database, authentication, worker, or multi-agent system is added.
- Per the user's current request, do not create or run test files; use deterministic harnesses, lint, compilation, route assertions, and HTTP smoke checks.
- This directory is not currently a Git repository, so do not add commit steps.

---

### Task 1: Represent the catalog hierarchy and three workflow states

**Files:**
- Modify: `src/mrm_review/schemas.py`

**Interfaces:**
- Produces: `MetricCategory`, `CatalogSelection`, `RefinedUseCase`, `MetricReviewResult`, and `ReadyForMetricReview`.
- Changes: `PendingReview.catalog` from `list[MetricCatalogItem]` to `list[MetricCategory]`.
- Preserves: `SystemType`, developer field-review contracts, and output workbook contracts.

- [ ] **Step 1: Add the hierarchical catalog models**

```python
class MetricCategory(BaseModel):
    name: str
    subcategories: list[str]
    applications: list[str]
    metrics: list[MetricCatalogItem]


class CatalogSelection(BaseModel):
    main_category: str
    subcategory: str
    closest_application: str
```

- [ ] **Step 2: Attach the catalog selection to `UseCaseSummary`**

```python
class UseCaseSummary(BaseModel):
    business_use_case: str
    system_type: SystemType
    catalog_selection: CatalogSelection
    components: list[str]
    input: str
    processing: str
    output: str
```

- [ ] **Step 3: Split refined understanding from metric output**

```python
class RefinedUseCase(BaseModel):
    use_case: UseCaseSummary
    mrm_explanation: str = Field(max_length=600)
    diagram: list[str] = Field(min_length=2, max_length=6)


class MetricReviewResult(BaseModel):
    expected_metrics: list[ExpectedMetric]
    metric_reviews: list[MetricReview]


class ReadyForMetricReview(BaseModel):
    pending: PendingReview
    refined: RefinedUseCase
```

- [ ] **Step 4: Verify schema imports and compilation**

Run:

```powershell
.\.venv\Scripts\python.exe -m compileall -q src\mrm_review\schemas.py
.\.venv\Scripts\ruff.exe check src\mrm_review\schemas.py
```

Expected: both commands exit successfully.

### Task 2: Parse the complete hierarchy from metrics.md

**Files:**
- Modify: `src/mrm_review/file_io.py`

**Interfaces:**
- Produces: `read_metric_catalog(path: Path) -> list[MetricCategory]`.
- Consumes the existing Markdown labels `Main Subcategories`, `Applications`, and `Metrics` as structure markers, not as domain mappings.

- [ ] **Step 1: Replace the flat Metric parser with a section state machine**

For every `##` heading, create one category. Collect bullet values under the three bold section labels into that category. Strip Markdown bold markers and the numeric prefix from category display names.

```python
def read_metric_catalog(path: Path) -> list[MetricCategory]:
    categories: list[MetricCategory] = []
    category_name = ""
    section = ""
    subcategories: list[str] = []
    applications: list[str] = []
    metrics: list[MetricCatalogItem] = []
    # Flush each completed heading into MetricCategory.
```

- [ ] **Step 2: Reject incomplete catalog categories explicitly**

Each parsed category must have a name, at least one subcategory, at least one application, and at least one Metric. Duplicate Metrics are removed only inside the same category; the same Metric may legitimately appear in different categories.

- [ ] **Step 3: Run a deterministic parser harness**

Run:

```powershell
.\.venv\Scripts\python.exe -c 'from pathlib import Path; from mrm_review.file_io import read_metric_catalog; items=read_metric_catalog(Path("metrics/metrics.md")); first=items[0]; assert len(items)==6; assert first.name=="Non-Agentic"; assert "RAG" in first.subcategories; assert "Q&A" in first.applications; assert "Accuracy" in {item.name for item in first.metrics}; print("Catalog hierarchy OK")'
```

Expected: `Catalog hierarchy OK`.

### Task 3: Separate the three OpenAI prompt contracts

**Files:**
- Modify: `src/mrm_review/prompts/use_case.py`
- Create: `src/mrm_review/prompts/use_case_refinement.py`
- Modify: `src/mrm_review/prompts/metric_review.py`
- Modify: `src/mrm_review/ai_reviewer.py`

**Interfaces:**
- Produces: `create_draft(source_text, catalog) -> UseCaseDraft`.
- Produces: `refine_use_case(pending, answers) -> RefinedUseCase`.
- Produces: `review_metrics(ready, eligible_metrics) -> MetricReviewResult`.

- [ ] **Step 1: Update the initial prompt**

Require exact selection of one category, one belonging subcategory, and one belonging application from the supplied catalog. Questions must be optional, necessary for understanding, and limited to four by the schema.

- [ ] **Step 2: Add the refinement prompt**

The new prompt updates the use case from non-skipped answers, preserves skipped unknowns as unknown, and produces the short MRM explanation and 2–6 node business/risk flow. It must select only values present in the supplied catalog.

- [ ] **Step 3: Narrow the metric prompt**

Remove use-case updating from `METRIC_REVIEW_PROMPT`. Tell the model that `eligible_metrics` already contains the complete and only allowed Metric set for the selected category.

- [ ] **Step 4: Implement the three reviewer methods**

Each method sends structured JSON and uses `responses.parse` with its stage-specific Pydantic model. Keep `store=False` and never log request payloads or credentials.

- [ ] **Step 5: Compile and lint the prompt/reviewer files**

Run Ruff and `compileall` on the four files. Expected: success without a live OpenAI call.

### Task 4: Split workflow orchestration and enforce catalog membership

**Files:**
- Modify: `src/mrm_review/workflow.py`

**Interfaces:**
- Produces: `start_review(paths, reviewer) -> PendingReview`.
- Produces: `refine_review(pending, answers, reviewer) -> ReadyForMetricReview`.
- Produces: `finish_review(ready, reviewer) -> MetricReviewResult`.

- [ ] **Step 1: Validate initial and refined catalog selections**

Implement one focused validator:

```python
def _selected_category(
    catalog: list[MetricCategory],
    selection: CatalogSelection,
) -> MetricCategory:
    # Require exact category name, then exact belonging subcategory/application.
```

Raise concise `ValueError` messages for invented or mismatched selections. Do not normalize or silently replace LLM values.

- [ ] **Step 2: Make `start_review` catalog-aware**

Read source, hierarchy, and workbook; pass source plus hierarchy to `create_draft`; validate the returned selection; return `PendingReview` regardless of whether the question list is empty.

- [ ] **Step 3: Implement `refine_review`**

Validate answer IDs, call `refine_use_case`, validate its possibly updated catalog selection, and return `ReadyForMetricReview`. Skipped or empty answers remain explicit in the payload.

- [ ] **Step 4: Narrow and implement `finish_review`**

Find the selected category from the refined use case, pass only its Metrics to `review_metrics`, validate every expected Metric against that subset, validate every developer row, then write both Excel files.

- [ ] **Step 5: Run a deterministic workflow validation harness**

Use in-memory schema objects and a tiny fake reviewer from a `python -c` command to prove that a belonging category/subcategory/application passes and an application from a different category raises `ValueError`. Do not create a test file or call OpenAI.

### Task 5: Implement the three-step FastAPI and Jinja flow

**Files:**
- Modify: `src/mrm_review/api.py`
- Modify: `src/mrm_review/templates/index.html`
- Modify: `src/mrm_review/static/styles.css` only if the new summary fields require minor layout styling.

**Interfaces:**
- Keeps: `POST /start`.
- Adds: `POST /refine` and `POST /review`.
- Keeps: `/`, `/health`, `/download/{name}`, and `/api/docs`.

- [ ] **Step 1: Store draft and refined states separately**

Use two in-memory dictionaries keyed by the existing random `review_id`:

```python
draft_states: dict[str, PendingReview] = {}
refined_states: dict[str, ReadyForMetricReview] = {}
```

- [ ] **Step 2: Make `/start` always render the question stage**

Never skip directly to metric review. The page shows the initial use case and catalog selection. If there are no questions, it still shows a `Next` form.

- [ ] **Step 3: Add `/refine`**

Parse every answer/Skip, call `refine_review`, move the state from draft to refined, and render a new `understanding` stage containing the final MRM explanation, exact catalog selections, and flow.

- [ ] **Step 4: Add `/review` for the `OK` action**

The understanding form contains only the hidden review ID and a submit button labelled `OK`. The route calls `finish_review`, removes completed state, and renders the existing output table and download links.

- [ ] **Step 5: Update error handling**

Keep concise user-facing errors and detailed server-side exceptions without logging secrets or full source payloads.

- [ ] **Step 6: Assert route registration**

Run a Python import command and assert the route set contains `/start`, `/refine`, `/review`, `/health`, and both download/documentation routes.

### Task 6: Update documentation and verify the complete implementation

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `AGENTS.md` only if its workflow description contradicts the new three-stage flow.

**Interfaces:**
- Documents the catalog hierarchy, three stages, exact `OK` gate, and output timing.

- [ ] **Step 1: Update user-facing workflow documentation**

Document that `metrics.md` controls all four hierarchy levels and that outputs are not written until after `OK`.

- [ ] **Step 2: Run static verification**

```powershell
.\.venv\Scripts\ruff.exe check . --exclude .venv --exclude '*.egg-info'
.\.venv\Scripts\ruff.exe format . --check --exclude .venv --exclude '*.egg-info'
.\.venv\Scripts\python.exe -m compileall -q main.py src
.\.venv\Scripts\python.exe -m pip check
```

Expected: all commands succeed.

- [ ] **Step 3: Restart FastAPI and run HTTP smoke checks**

Run the server on port 8000, then check `/`, `/health`, `/static/styles.css`, and `/api/docs` return HTTP 200. Keep the server running for the user.

- [ ] **Step 4: Verify no test source files were created**

Use `rg --files tests -g '*.py'`. Expected: no results.
