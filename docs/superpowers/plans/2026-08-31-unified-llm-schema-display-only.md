# Unified LLM Schema and Display-Only Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace stage-specific OpenAI payloads with one stable `LLMInput` and one stable `LLMOutput`, skip Call 2 when no answer exists, and display Call 3 results without writing output files.

**Architecture:** Two focused readers create raw user/system inputs, three direct reviewer methods return the same output model, and a linear workflow carries the latest output forward through process-local API state. The exact Markdown catalog is sent to OpenAI while a minimal internal parse validates returned catalog values.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic 2, OpenAI Responses API, openpyxl, PyYAML, Jinja2, vanilla JavaScript.

**Spec:** `docs/superpowers/specs/2026-08-31-unified-llm-schema-display-only-design.md`

## Global Constraints

- Preserve the current approved, uncommitted reader split and `metrics/metrics.md` content; never reset or overwrite unrelated working-tree changes.
- `system_main_info` is the decoded `QM-*.txt` text without a filename prefix, trimming, summary, or rewrite.
- `global_metrics` is the exact full text of `metrics/metrics.md`, not a nested provider payload.
- Serialized `system_metrics` rows use exactly `Monitoring Metric`, `Test Objective`, and `Calculation Method/Formula`.
- Call 2 runs only when at least one non-blank, non-skipped answer exists.
- Call 3 runs only after the user selects the button labelled exactly `OK`.
- All three calls return the complete `LLMOutput`; fields owned by later calls remain empty.
- Remove all Download buttons and the download route; show the complete final result in the page.
- Reject catalog selections and expected metrics outside the approved `metrics.md` category.
- Keep one structured-output repair attempt; do not repair authentication, billing, access, rate-limit, timeout, or connection errors.
- Do not create a `tests/` directory or automated test files. Use temporary in-memory harnesses, lint, compilation, imports, route checks, and HTTP smoke checks.
- Do not make a live or paid OpenAI request during deterministic verification.
- Existing ignored workbooks under `Output/` are user data; do not delete, read, or stage them.
- Do not add a database, authentication, repository, service, adapter, factory, background job, or multi-agent production layer.

---

### Task 1: Define the Unified Contracts and Input Readers

**Files:**
- Modify: `src/schemas.py`
- Modify: `src/user_input_reader.py`
- Modify: `src/metric_catalog_reader.py`
- Modify: `input_format.yml`
- Modify: `AGENTS.md`

**Interfaces:**
- Produces: `SystemMetric`, `ExtraInfo`, `ExpectedMetric`, `MetricReview`, `LLMOutput`, `LLMInput`, and `UploadedFileData` in `schemas.py`.
- Produces: `read_user_inputs(qm_files, workbook_files) -> tuple[str, list[SystemMetric]]`.
- Produces: `read_global_metrics(path: Path) -> str`.
- Produces: `parse_global_metrics(text: str) -> Catalog`, where `Catalog = dict[str, dict[str, list[str]]]`.
- Consumes: the approved column aliases and Markdown section names from `input_format.yml`.

- [ ] **Step 1: Record the expected failing contract with an in-memory harness**

Run before editing production code:

```powershell
$env:PYTHONPATH = (Resolve-Path src).Path
@'
from schemas import LLMInput, LLMOutput, SystemMetric

metric = SystemMetric(
    monitoring_metric="Accuracy",
    test_objective="Above 90%",
    calculation_method="Correct / Total",
)
assert metric.model_dump(mode="json", by_alias=True) == {
    "Monitoring Metric": "Accuracy",
    "Test Objective": "Above 90%",
    "Calculation Method/Formula": "Correct / Total",
}
print(LLMInput, LLMOutput)
'@ | .\.venv\Scripts\python.exe -
```

Expected: FAIL because `LLMInput`, `LLMOutput`, and `SystemMetric` do not yet exist.

- [ ] **Step 2: Replace stage-specific schemas with the two top-level contracts**

Keep only the upload transport model plus these provider contracts and row models in `schemas.py`:

```python
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


Status = Literal["OK", "IT IS EMPTY", "NEEDS REVISION"]
SystemType = Literal["RAG", "LLM", "Traditional ML", "Agentic", "Hybrid", "Other"]


class SystemMetric(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    monitoring_metric: str = Field(serialization_alias="Monitoring Metric")
    test_objective: str = Field(default="", serialization_alias="Test Objective")
    calculation_method: str = Field(
        default="",
        serialization_alias="Calculation Method/Formula",
    )


class ExtraInfo(BaseModel):
    question: str
    answer: str


class ExpectedMetric(BaseModel):
    name: str
    applicability_reason: str
    test_objective: str
    calculation_method: str


class MetricReview(BaseModel):
    metric: str
    objective_status: Status
    objective_reason: str
    objective_revised: str
    objective_questions: list[str] = Field(max_length=3)
    formula_status: Status
    formula_reason: str
    formula_revised: str
    formula_questions: list[str] = Field(max_length=3)

    @model_validator(mode="after")
    def validate_fields(self) -> "MetricReview":
        _validate_field(self.objective_status, self.objective_reason, self.objective_revised)
        _validate_field(self.formula_status, self.formula_reason, self.formula_revised)
        return self


def _validate_field(status: Status, reason: str, revised: str) -> None:
    if status == "NEEDS REVISION" and (not reason or not revised):
        raise ValueError("NEEDS REVISION requires a reason and revised text.")
    if status == "IT IS EMPTY" and not revised:
        raise ValueError("IT IS EMPTY requires proposed text.")
    if status == "OK" and revised:
        raise ValueError("OK must not contain revised text.")


class LLMOutput(BaseModel):
    business_use_case: str
    system_type: SystemType
    main_category: str
    subcategory: str
    closest_application: str
    components: list[str]
    input: str
    processing: str
    output: str
    understanding_confidence: int | None = Field(ge=0, le=100)
    questions: list[str] = Field(max_length=4)
    mrm_explanation: str
    flow: list[str]
    expected_metrics: list[ExpectedMetric]
    metric_reviews: list[MetricReview]


class LLMInput(BaseModel):
    system_main_info: str
    global_metrics: str
    system_metrics: list[SystemMetric]
    system_extra_info: list[ExtraInfo]
    previous_output: LLMOutput | None


class UploadedFileData(BaseModel):
    filename: str
    content: bytes
```

Delete the old catalog, draft, refined, state, completed-review, and output-path models. Do not add replacement wrapper models.

- [ ] **Step 3: Make the user reader return exact QM text and typed workbook rows**

Change the public signature and the QM return value in `src/user_input_reader.py`:

```python
from schemas import SystemMetric, UploadedFileData


def read_user_inputs(
    qm_files: Sequence[UploadedFileData],
    workbook_files: Sequence[UploadedFileData],
) -> tuple[str, list[SystemMetric]]:
    qm_file = _only_file(qm_files, "QM text file")
    workbook_file = _only_file(workbook_files, "developer workbook")
    return _read_qm(qm_file), _read_workbook(workbook_file)
```

Return `content` directly from `_read_qm`; remove `SOURCE FILE: ...`. Replace `DeveloperMetric(...)` with:

```python
SystemMetric(
    monitoring_metric=name,
    test_objective=objective,
    calculation_method=calculation,
)
```

Retain filename, UTF-8, workbook, header, duplicate-name, placeholder-row, and empty-input validation.

- [ ] **Step 4: Return raw catalog text and a separate minimal internal parse**

Use these public interfaces in `src/metric_catalog_reader.py`:

```python
Catalog = dict[str, dict[str, list[str]]]


def read_global_metrics(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError("metrics/metrics.md was not found.")
    return path.read_text(encoding="utf-8-sig")


def parse_global_metrics(text: str) -> Catalog:
    catalog: Catalog = {}
    category = ""
    section = ""

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            category = _category_name(line[3:])
            if category.casefold() in {name.casefold() for name in catalog}:
                raise ValueError(f"Catalog contains duplicate category '{category}'.")
            catalog[category] = {name: [] for name in SECTIONS.values()}
            section = ""
            continue
        if line.startswith(("* **", "- **")):
            section = _plain_text(line[2:])
            continue
        if category and section in catalog[category] and line.startswith(("* ", "- ")):
            value = _plain_text(line[2:])
            values = catalog[category][section]
            if value.casefold() in {item.casefold() for item in values}:
                raise ValueError(
                    f"Catalog category '{category}' has duplicate {section} value '{value}'."
                )
            values.append(value)

    if not catalog:
        raise ValueError("metrics.md must contain at least one category.")
    for category, sections in catalog.items():
        missing = [name for name, values in sections.items() if not values]
        if missing:
            raise ValueError(f"Catalog category '{category}' is missing: {', '.join(missing)}.")
    return catalog
```

Keep the existing `_category_name()` and Markdown-cleaning helper. The raw string returned by `read_global_metrics()` must not be rebuilt from `Catalog`.

- [ ] **Step 5: Make configuration names match the new concepts**

Use this structure in `input_format.yml`:

```yaml
user_inputs:
  qm_filename: 'QM-.+\.txt'
  workbook_filename: 'MRM_.+\.xlsx'
  workbook_columns:
    monitoring_metric:
      - Monitoring Metric
      - Metric
    test_objective:
      - Test Objective
    calculation_method:
      - Calculation Method/Formula
      - Calcution Method/Formula
      - Calculation Method / Formula
  empty_metric_placeholders:
    - Any other(s)

global_metrics_format:
  sections:
    subcategories: Main Subcategories
    examples: Exmaples
    metrics: Metrics
```

Update reader lookups from `metric` to `monitoring_metric`. Load `SECTIONS` from `global_metrics_format.sections`.

- [ ] **Step 6: Align governing instructions before later implementation**

Update `AGENTS.md` so it says:

- Call 1 sends the exact QM text, exact Markdown catalog, and three-column workbook rows.
- Call 2 is skipped when no non-blank answer exists.
- Call 3 returns display-only results after exact `OK`.
- No output workbook is written.
- The two top-level provider schemas are `LLMInput` and `LLMOutput`.
- `user_input_reader.py` and `metric_catalog_reader.py` own the two input boundaries.

Remove requirements that say missing metrics must be written under `Output/` or that OpenAI receives a nested parsed catalog.

- [ ] **Step 7: Run the focused reader/schema harness**

```powershell
$env:PYTHONPATH = (Resolve-Path src).Path
@'
from io import BytesIO
from pathlib import Path

from openpyxl import Workbook

from metric_catalog_reader import parse_global_metrics, read_global_metrics
from schemas import SystemMetric, UploadedFileData
from user_input_reader import read_user_inputs

book = Workbook()
book.active.append(["Monitoring Metric", "Test Objective", "Calculation Method/Formula"])
book.active.append(["Accuracy", "Above 90%", "Correct / Total"])
stream = BytesIO()
book.save(stream)
book.close()

qm_text, rows = read_user_inputs(
    [UploadedFileData(filename="QM-example.txt", content=b"exact text")],
    [UploadedFileData(filename="MRM_example.xlsx", content=stream.getvalue())],
)
raw_catalog = read_global_metrics(Path("metrics/metrics.md"))
catalog = parse_global_metrics(raw_catalog)

assert qm_text == "exact text"
assert rows[0].model_dump(mode="json", by_alias=True)["Monitoring Metric"] == "Accuracy"
assert raw_catalog == Path("metrics/metrics.md").read_text(encoding="utf-8-sig")
assert catalog["Non-Agentic"]["Exmaples"][0] == "Q&A"
assert "Accuracy" in catalog["Non-Agentic"]["Metrics"]
print("schema and readers passed")
'@ | .\.venv\Scripts\python.exe -
```

Expected: `schema and readers passed`.

- [ ] **Step 8: Commit the contracts and readers**

```powershell
git add -- AGENTS.md input_format.yml metrics/metrics.md src/schemas.py src/user_input_reader.py src/metric_catalog_reader.py src/input_reader.py
git commit -m "Build unified LLM input contracts"
```

---

### Task 2: Make All Three OpenAI Calls Use the Same Contracts

**Files:**
- Modify: `src/ai_reviewer.py`
- Modify: `prompts/use_case.yml`
- Modify: `prompts/use_case_refinement.yml`
- Modify: `prompts/metric_review.yml`

**Interfaces:**
- Consumes: `LLMInput` serialized with `model_dump(mode="json", by_alias=True)`.
- Produces: `call_1(data, repair_feedback="") -> LLMOutput`.
- Produces: `call_2(data, repair_feedback="") -> LLMOutput`.
- Produces: `call_3(data, repair_feedback="") -> LLMOutput`.

- [ ] **Step 1: Run a failing reviewer-interface import check**

```powershell
$env:PYTHONPATH = (Resolve-Path src).Path
.\.venv\Scripts\python.exe -c "from ai_reviewer import OpenAIReviewer; assert hasattr(OpenAIReviewer, 'call_1')"
```

Expected: FAIL because the current class exposes `create_draft`, `refine_use_case`, and `review_metrics`.

- [ ] **Step 2: Replace stage-specific reviewer methods with three thin calls**

Use this structure in `src/ai_reviewer.py`:

```python
import json

from openai import OpenAI

from prompt_loader import load_prompt
from schemas import LLMInput, LLMOutput

CALL_1_PROMPT = load_prompt("use_case.yml")
CALL_2_PROMPT = load_prompt("use_case_refinement.yml")
CALL_3_PROMPT = load_prompt("metric_review.yml")


class OpenAIReviewer:
    def __init__(self, client: OpenAI, model: str, temperature: float) -> None:
        self.client = client
        self.model = model
        self.temperature = temperature

    def call_1(self, data: LLMInput, *, repair_feedback: str = "") -> LLMOutput:
        return self._request(CALL_1_PROMPT, data, repair_feedback)

    def call_2(self, data: LLMInput, *, repair_feedback: str = "") -> LLMOutput:
        return self._request(CALL_2_PROMPT, data, repair_feedback)

    def call_3(self, data: LLMInput, *, repair_feedback: str = "") -> LLMOutput:
        return self._request(CALL_3_PROMPT, data, repair_feedback)

    def _request(self, prompt: str, data: LLMInput, repair_feedback: str) -> LLMOutput:
        instructions = prompt
        if repair_feedback:
            instructions += f"\n\nPrevious output validation error: {repair_feedback}"
        response = self.client.responses.parse(
            model=self.model,
            temperature=self.temperature,
            store=False,
            instructions=instructions,
            input=json.dumps(data.model_dump(mode="json", by_alias=True), ensure_ascii=False),
            text_format=LLMOutput,
        )
        if response.output_parsed is None:
            raise ValueError("OpenAI did not return a valid structured result.")
        return response.output_parsed
```

Do not add `repair_feedback` to the JSON payload.

- [ ] **Step 3: Update Call 1 instructions**

Set `prompts/use_case.yml` to a new version and require:

```yaml
version: "3.0"
instructions: |-
  Act as an MRM reviewer. Read system_main_info, the exact global_metrics
  Markdown, and every system_metrics row. Select main_category, subcategory,
  and closest_application only from global_metrics; closest_application must
  come from the selected category's Exmaples section.

  Return the complete LLMOutput schema. Fill the business understanding,
  system_type, catalog selection, components, input, processing, output,
  understanding_confidence, and zero to four material questions. Set
  mrm_explanation to an empty string and set flow, expected_metrics, and
  metric_reviews to empty lists. Do not invent source facts or catalog values.
```

- [ ] **Step 4: Update Call 2 instructions**

Set `prompts/use_case_refinement.yml` to:

```yaml
version: "2.0"
instructions: |-
  Act as an MRM reviewer. Use system_extra_info and previous_output to refine
  the understanding. Preserve answered facts and never invent an answer for a
  skipped or absent question. Catalog selections must use exact values from
  global_metrics.

  Return the complete LLMOutput schema. Preserve or improve the Call 1 fields,
  keep the original questions, fill mrm_explanation and a two-to-six-label
  business/risk flow, and leave expected_metrics and metric_reviews empty.
```

- [ ] **Step 5: Update Call 3 instructions**

Set `prompts/metric_review.yml` to:

```yaml
version: "3.0"
instructions: |-
  Act as an MRM reviewer. Preserve all understanding fields from
  previous_output. Select expected_metrics only from the Metrics section of
  the selected global_metrics category. Return exactly one metric_reviews row
  for every system_metrics row.

  Assess Objective and Formula independently. Use only OK, IT IS EMPTY, or
  NEEDS REVISION. NEEDS REVISION requires a short reason and corrected text;
  IT IS EMPTY requires proposed text; OK has empty revised text. Ask at most
  three questions for each field. Return the complete LLMOutput schema.
```

- [ ] **Step 6: Verify exact input keys with a fake OpenAI client**

Run an inline fake that captures the JSON without contacting OpenAI:

```powershell
$env:PYTHONPATH = (Resolve-Path src).Path
@'
import json
from types import SimpleNamespace

from ai_reviewer import OpenAIReviewer
from schemas import LLMInput, LLMOutput

output = LLMOutput(
    business_use_case="Use case", system_type="RAG", main_category="Non-Agentic",
    subcategory="RAG", closest_application="Q&A", components=[], input="Documents",
    processing="Retrieval", output="Answer", understanding_confidence=80, questions=[],
    mrm_explanation="", flow=[], expected_metrics=[], metric_reviews=[]
)

class Responses:
    def parse(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(output_parsed=output)

responses = Responses()
client = SimpleNamespace(responses=responses)
reviewer = OpenAIReviewer(client, "model", 0.0)
data = LLMInput(
    system_main_info="raw qm", global_metrics="raw metrics", system_metrics=[],
    system_extra_info=[], previous_output=None
)
assert reviewer.call_1(data) == output
payload = json.loads(responses.kwargs["input"])
assert set(payload) == {
    "system_main_info", "global_metrics", "system_metrics",
    "system_extra_info", "previous_output"
}
assert responses.kwargs["text_format"] is LLMOutput
print("reviewer contract passed")
'@ | .\.venv\Scripts\python.exe -
```

Expected: `reviewer contract passed`.

- [ ] **Step 7: Commit reviewer and prompts**

```powershell
git add -- src/ai_reviewer.py prompts/use_case.yml prompts/use_case_refinement.yml prompts/metric_review.yml
git commit -m "Use unified schemas for OpenAI calls"
```

---

### Task 3: Replace Stage Wrappers with a Linear Workflow

**Files:**
- Modify: `src/workflow.py`

**Interfaces:**
- Consumes: `read_user_inputs`, `read_global_metrics`, `parse_global_metrics`, and reviewer `call_1`, `call_2`, `call_3`.
- Produces: `ReviewState = tuple[LLMInput, LLMOutput]`.
- Produces: `start_review(catalog_path, reviewer, qm_files, workbook_files) -> ReviewState`.
- Produces: `continue_review(data, previous_output, answers, reviewer) -> ReviewState`.
- Produces: `finish_review(data, previous_output, reviewer) -> LLMOutput`.

- [ ] **Step 1: Run a failing optional-Call-2 interface check**

```powershell
$env:PYTHONPATH = (Resolve-Path src).Path
.\.venv\Scripts\python.exe -c "from workflow import continue_review; print(continue_review)"
```

Expected: FAIL because `continue_review` does not exist.

- [ ] **Step 2: Define the minimal reviewer protocol and state alias**

At the top of `workflow.py`, use:

```python
from collections.abc import Callable
from pathlib import Path
from typing import Protocol, TypeVar

from metric_catalog_reader import parse_global_metrics, read_global_metrics
from schemas import ExtraInfo, LLMInput, LLMOutput, UploadedFileData
from user_input_reader import read_user_inputs


class AIReviewer(Protocol):
    def call_1(self, data: LLMInput, *, repair_feedback: str = "") -> LLMOutput: ...
    def call_2(self, data: LLMInput, *, repair_feedback: str = "") -> LLMOutput: ...
    def call_3(self, data: LLMInput, *, repair_feedback: str = "") -> LLMOutput: ...


ReviewState = tuple[LLMInput, LLMOutput]
ReviewResult = TypeVar("ReviewResult")
```

Keep `AIReviewValidationError` and the existing one-repair helper.

- [ ] **Step 3: Implement Call 1 assembly**

```python
def start_review(
    catalog_path: Path,
    reviewer: AIReviewer,
    *,
    qm_files: list[UploadedFileData],
    workbook_files: list[UploadedFileData],
) -> ReviewState:
    system_main_info, system_metrics = read_user_inputs(qm_files, workbook_files)
    global_metrics = read_global_metrics(catalog_path)
    data = LLMInput(
        system_main_info=system_main_info,
        global_metrics=global_metrics,
        system_metrics=system_metrics,
        system_extra_info=[],
        previous_output=None,
    )
    result = _call_with_one_repair(
        lambda feedback: reviewer.call_1(data, repair_feedback=feedback),
        lambda output: _validate_output(data, output, stage=1),
    )
    return data, result
```

- [ ] **Step 4: Implement optional Call 2**

```python
def continue_review(
    data: LLMInput,
    previous_output: LLMOutput,
    answers: list[ExtraInfo],
    reviewer: AIReviewer,
) -> ReviewState:
    next_input = data.model_copy(
        update={"system_extra_info": answers, "previous_output": previous_output}
    )
    if not answers:
        return next_input, previous_output

    result = _call_with_one_repair(
        lambda feedback: reviewer.call_2(next_input, repair_feedback=feedback),
        lambda output: _validate_output(next_input, output, stage=2),
    )
    return next_input, result
```

- [ ] **Step 5: Implement Call 3 without output writing**

```python
def finish_review(
    data: LLMInput,
    previous_output: LLMOutput,
    reviewer: AIReviewer,
) -> LLMOutput:
    final_input = data.model_copy(update={"previous_output": previous_output})
    return _call_with_one_repair(
        lambda feedback: reviewer.call_3(final_input, repair_feedback=feedback),
        lambda output: _validate_output(final_input, output, stage=3),
    )
```

Delete all imports and calls involving `output_writer`, `CompletedReview`, `PendingReview`, `ReadyForMetricReview`, and `ReviewPaths`.

- [ ] **Step 6: Validate and normalize the full output by stage**

Implement these exact responsibilities in `_validate_output(data, output, stage)`:

```python
def _validate_output(data: LLMInput, output: LLMOutput, stage: int) -> None:
    catalog = parse_global_metrics(data.global_metrics)
    category = _canonical_key(catalog, output.main_category, "Category")
    sections = catalog[category]
    output.main_category = category
    output.subcategory = _canonical_value(
        sections["Main Subcategories"], output.subcategory, "Subcategory"
    )
    output.closest_application = _canonical_value(
        sections["Exmaples"], output.closest_application, "Application"
    )

    required_text = (
        output.business_use_case,
        output.main_category,
        output.subcategory,
        output.closest_application,
        output.input,
        output.processing,
        output.output,
    )
    if any(not value.strip() for value in required_text):
        raise ValueError("The system understanding fields must not be empty.")
    if output.understanding_confidence is None:
        raise ValueError("The result requires understanding_confidence.")

    if stage == 1:
        if output.mrm_explanation or output.flow or output.expected_metrics or output.metric_reviews:
            raise ValueError("Call 1 fields for later stages must be empty.")
        return

    if data.previous_output is None:
        raise ValueError("Later calls require previous_output.")
    if output.questions != data.previous_output.questions:
        raise ValueError("Later calls must preserve the Call 1 questions.")
    if not output.mrm_explanation or not 2 <= len(output.flow) <= 6:
        raise ValueError("The final understanding requires an explanation and 2-6 flow labels.")
    if stage == 2:
        if output.expected_metrics or output.metric_reviews:
            raise ValueError("Call 2 metric fields must be empty.")
        return

    preserved_fields = (
        "business_use_case", "system_type", "main_category", "subcategory",
        "closest_application", "components", "input", "processing", "output",
        "understanding_confidence", "questions", "mrm_explanation", "flow",
    )
    if any(
        getattr(output, field) != getattr(data.previous_output, field)
        for field in preserved_fields
    ):
        raise ValueError("Call 3 must preserve the latest system understanding.")
    _validate_metric_results(data, sections["Metrics"], output)
```

Use case-insensitive helpers that return source spelling:

```python
def _canonical_key(values: dict[str, object], returned: str, label: str) -> str:
    match = next((name for name in values if name.casefold() == returned.casefold()), None)
    if match is None:
        raise ValueError(f"{label} '{returned}' is not present in metrics.md.")
    return match


def _canonical_value(values: list[str], returned: str, label: str) -> str:
    match = next((value for value in values if value.casefold() == returned.casefold()), None)
    if match is None:
        raise ValueError(f"{label} '{returned}' is not present in metrics.md.")
    return match
```

`_validate_metric_results` must:

- normalize every expected metric against the selected category's metric list;
- reject duplicate expected metric names after case-insensitive normalization;
- require exactly one unique review row for every `data.system_metrics` metric;
- normalize review-row names to workbook spelling;
- require `IT IS EMPTY` exactly when the corresponding original workbook field is blank;
- rely on `MetricReview` Pydantic validation for revision and question-count rules.

- [ ] **Step 7: Verify both optional-Call-2 branches and no file writes**

Run a temporary fake reviewer. Construct one valid `LLMOutput` for Call 1, one with explanation/flow for Call 2, and one with complete expected/review rows for Call 3. Assert:

```python
data, first = start_review(...)

data_without_answers, unchanged = continue_review(data, first, [], reviewer)
assert reviewer.call_2_count == 0
assert unchanged is first

answers = [ExtraInfo(question="Data source?", answer="Transactions")]
data_with_answers, refined = continue_review(data, first, answers, reviewer)
assert reviewer.call_2_count == 1
assert data_with_answers.system_extra_info == answers

final = finish_review(data_with_answers, refined, reviewer)
assert reviewer.call_3_count == 1
assert final.metric_reviews[0].metric == "Accuracy"
assert not list(Path("Output").glob("mrm_review_*.xlsx"))
```

Use a temporary directory for catalog and input fixtures so pre-existing ignored user workbooks do not affect the last assertion. Expected: both branches pass and the temporary output directory remains absent.

- [ ] **Step 8: Commit workflow replacement**

```powershell
git add -- src/workflow.py src/output_writer.py
git commit -m "Simplify review call sequencing"
```

---

### Task 4: Update FastAPI State and Remove Downloads

**Files:**
- Modify: `src/api.py`

**Interfaces:**
- Consumes: `ReviewState`, `start_review`, `continue_review`, and `finish_review`.
- Produces: unchanged `/start`, `/refine`, `/review`, `/health`, and `/api/docs` routes.
- Removes: `/download/{name}`.

- [ ] **Step 1: Capture the currently failing route expectation**

```powershell
$env:PYTHONPATH = (Resolve-Path src).Path
@'
from pathlib import Path
from api import create_app

app = create_app(reviewer=object(), root=Path.cwd())
paths = {route.path for route in app.routes}
assert "/download/{name}" not in paths
'@ | .\.venv\Scripts\python.exe -
```

Expected: FAIL because the download route still exists.

- [ ] **Step 2: Replace wrapper-model state with two typed dictionaries**

Use:

```python
from schemas import ExtraInfo, LLMInput, LLMOutput, UploadedFileData
from workflow import AIReviewer, ReviewState, continue_review, finish_review, start_review

question_states: dict[str, ReviewState] = {}
ready_states: dict[str, ReviewState] = {}
```

Remove `re`, `HTTPException`, `FileResponse`, `DOWNLOAD_NAME`, `PendingReview`, `ReadyForMetricReview`, and `ReviewPaths` imports.

- [ ] **Step 3: Adapt `/start` to the new state**

Call:

```python
state = start_review(
    project_root / "metrics" / "metrics.md",
    active_reviewer,
    qm_files=qm_files,
    workbook_files=workbook_files,
)
review_id = uuid4().hex
question_states[review_id] = state
return render_page(
    request,
    "questions",
    review_id=review_id,
    result=state[1],
)
```

- [ ] **Step 4: Adapt `/refine` and omit blank/skipped answers**

Read the stored tuple and build only answered pairs:

```python
data, previous_output = state
answers = []
for index, question in enumerate(previous_output.questions):
    skipped = form.get(f"skip_{index}") == "on"
    answer = str(form.get(f"answer_{index}", "")).strip()
    if answer and not skipped:
        answers.append(ExtraInfo(question=question, answer=answer))

ready = continue_review(data, previous_output, answers, active_reviewer)
question_states.pop(review_id, None)
ready_states[review_id] = ready
return render_page(
    request,
    "understanding",
    review_id=review_id,
    result=ready[1],
)
```

On failure, preserve `question_states[review_id]` and re-render the questions stage with `result=previous_output`.

- [ ] **Step 5: Adapt `/review` to return only the final result**

```python
data, previous_output = state
result = finish_review(data, previous_output, active_reviewer)
ready_states.pop(review_id, None)
return render_page(request, "result", result=result)
```

On failure, preserve `ready_states[review_id]` and re-render the understanding stage with the previous result.

- [ ] **Step 6: Delete the download route**

Remove the complete `@app.get("/download/{name}")` function. Do not replace it with another file-serving endpoint.

Expose the two dictionaries for deterministic inspection:

```python
app.state.question_states = question_states
app.state.ready_states = ready_states
```

- [ ] **Step 7: Run route and import checks**

```powershell
$env:PYTHONPATH = (Resolve-Path src).Path
@'
from pathlib import Path
from api import create_app

app = create_app(reviewer=object(), root=Path.cwd())
paths = {route.path for route in app.routes}
assert {"/", "/health", "/start", "/refine", "/review", "/api/docs"} <= paths
assert "/download/{name}" not in paths
assert app.state.question_states == {}
assert app.state.ready_states == {}
print("API routes passed")
'@ | .\.venv\Scripts\python.exe -
```

Expected: `API routes passed`.

- [ ] **Step 8: Commit API state and route changes**

```powershell
git add -- src/api.py
git commit -m "Remove persisted review outputs"
```

---

### Task 5: Render the Unified Output in the Frontend

**Files:**
- Modify: `templates/index.html`
- Modify: `templates/app.js`
- Modify: `templates/styles.css`

**Interfaces:**
- Consumes: template variable `result: LLMOutput` for questions, understanding, and final stages.
- Produces: answer controls named `answer_<zero-based-index>` and `skip_<zero-based-index>`.
- Produces: a display-only final page with expected metrics and complete flat metric reviews.

- [ ] **Step 1: Record the current failing display contract**

After Task 4, run:

```powershell
rg -n "outputs\.|url_for\('download'|test_objective_assessment|calculation_method_assessment" templates\index.html
```

Expected: matches remain until the template is updated.

- [ ] **Step 2: Use `result` for the questions stage**

Replace `draft.use_case.*` expressions with flat `result.*` fields. Render questions with their loop index:

```html
{% for question in result.questions %}
  <div class="card">
    <label for="answer_{{ loop.index0 }}">{{ question }}</label>
    <input id="answer_{{ loop.index0 }}" name="answer_{{ loop.index0 }}" type="text">
    <label class="skip">
      <input name="skip_{{ loop.index0 }}" type="checkbox"> Skip
    </label>
  </div>
{% endfor %}
```

Show `result.understanding_confidence`, `result.main_category`, `result.subcategory`, and `result.closest_application` before the questions.

- [ ] **Step 3: Use `result` for the understanding stage**

Render `result.mrm_explanation` only when non-empty. Render the approved fields directly and loop over `result.flow`. Keep the hidden review ID and exact `OK` button.

- [ ] **Step 4: Render complete expected metrics**

Add a table with these columns:

```html
<tr>
  <th>Expected Metric</th>
  <th>Why Needed</th>
  <th>Proposed Test Objective</th>
  <th>Proposed Formula</th>
</tr>
```

Loop over `result.expected_metrics` and render `name`, `applicability_reason`, `test_objective`, and `calculation_method`. If the list is empty, show `No additional expected metrics were identified.`

- [ ] **Step 5: Render every flat metric-review field**

For each `result.metric_reviews` row, display:

- metric name;
- Objective status, reason, revised text, and questions;
- Formula status, reason, revised text, and questions.

Use conditional blocks so empty reason/revised/question values do not create empty labels. Delete all download links and every reference to `outputs`.

- [ ] **Step 6: Keep JavaScript aligned with numeric question names**

The existing JavaScript already derives the suffix after `skip_`. Keep that logic and confirm it finds `answer_0`, `answer_1`, and later inputs. No framework or additional script is needed.

Remove `.actions` styling if no element uses it. Keep `.button` because the error-stage Back link still uses it.

- [ ] **Step 7: Run template contract checks**

```powershell
rg -n "expected_metrics|objective_status|formula_status|objective_revised|formula_revised" templates\index.html
rg -n "outputs\.|url_for\('download'|test_objective_assessment|calculation_method_assessment" templates\index.html
```

Expected: the first command finds the new fields; the second command returns no matches.

- [ ] **Step 8: Commit frontend rendering**

```powershell
git add -- templates/index.html templates/app.js templates/styles.css
git commit -m "Display complete review results in browser"
```

---

### Task 6: Remove Obsolete Output Code and Align Current Documentation

**Files:**
- Delete: `src/output_writer.py`
- Delete: `Output/.gitkeep`
- Modify: `pyproject.toml`
- Modify: `.gitignore`
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `AGENTS.md`

**Interfaces:**
- Removes: `output_writer` from installable modules.
- Preserves: existing local ignored `Output/*.xlsx` files without reading, deleting, or staging them.
- Documents: the two schemas, exact raw inputs, optional Call 2, exact `OK`, and display-only result.

- [ ] **Step 1: Remove obsolete package and tracked-directory entries**

Ensure `src/output_writer.py` is deleted. Remove `"output_writer"` from `tool.setuptools.py-modules`.

Delete only the tracked `Output/.gitkeep`; do not enumerate or remove existing workbook files. Replace the Output ignore block with:

```gitignore
Output/
```

Keep the existing Input and metrics rules.

- [ ] **Step 2: Rewrite the README runtime flow**

Update `README.md` to state:

- `src/output_writer.py` no longer exists;
- `system_main_info` and `global_metrics` are exact text;
- `system_metrics` contains the three canonical Excel columns;
- all calls use `LLMInput` and `LLMOutput`;
- Call 2 is skipped when no answer is supplied;
- Call 3 starts only after exact `OK`;
- results appear in the page and no output workbook is created.

Remove the complete output-file section and replace it with a short `## خروجی` section describing the browser display.

- [ ] **Step 3: Rewrite the architecture document**

Update `docs/architecture.md` with this flow:

```text
QM text + workbook rows + exact metrics.md
                  |
                  v
               LLMInput
                  |
        Call 1 -> optional Call 2
                  |
                 OK
                  |
                Call 3
                  |
                  v
         LLMOutput -> browser
```

Remove output-writer, download, paired-file, and workbook-join statements. Document the raw-provider-payload versus internal-catalog-validation distinction.

- [ ] **Step 4: Scan current operational files for stale behavior**

```powershell
rg -n "output_writer|Output/missing_metrics|mrm_review_<id>|missing_metrics_<id>|/download|downloadable|فایل‌های Excel نوشته" AGENTS.md README.md docs\architecture.md pyproject.toml src templates
```

Expected: no matches. Historical specs and plans under `docs/superpowers/` and `specs/` are immutable design history and are excluded from this operational scan.

- [ ] **Step 5: Verify packaging after module removal**

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m pip check
```

Expected: editable build succeeds and `No broken requirements found.`

- [ ] **Step 6: Commit cleanup and documentation**

```powershell
git add -- AGENTS.md README.md docs/architecture.md pyproject.toml .gitignore Output/.gitkeep src/output_writer.py
git commit -m "Remove workbook output architecture"
```

---

### Task 7: Run End-to-End Deterministic Verification

**Files:**
- Modify only if a verification failure identifies a defect in an already listed production or documentation file.

**Interfaces:**
- Verifies: both Call 2 branches, exact input JSON, output validation, same-stage retry, route set, UI rendering, and absence of file creation.
- Does not use: a live OpenAI client, real user input documents, or persisted output files.

- [ ] **Step 1: Run formatting, lint, compilation, import, and dependency checks**

```powershell
.\.venv\Scripts\ruff.exe format --check .
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\python.exe -m compileall -q src main.py
.\.venv\Scripts\python.exe -c "from api import create_app; from schemas import LLMInput, LLMOutput; from workflow import start_review, continue_review, finish_review; print('imports passed')"
.\.venv\Scripts\python.exe -m pip check
```

Expected: every command exits zero, the import command prints `imports passed`, and pip reports no broken requirements.

- [ ] **Step 2: Run one deterministic workflow harness**

The harness must use temporary QM, workbook, catalog, and root directories plus a fake reviewer. It must assert all of these in one run:

```python
assert fake.call_1_count == 1
assert fake.received_call_1.system_main_info == exact_qm_text
assert fake.received_call_1.global_metrics == exact_metrics_markdown
assert set(fake.received_call_1.model_dump(mode="json", by_alias=True)) == {
    "system_main_info", "global_metrics", "system_metrics",
    "system_extra_info", "previous_output"
}
assert fake.received_call_1.previous_output is None

continue_review(data, first, [], fake)
assert fake.call_2_count == 0

answers = [ExtraInfo(question="Data source?", answer="Transactions")]
answered_data, refined = continue_review(data, first, answers, fake)
assert fake.call_2_count == 1
assert answered_data.system_extra_info == answers
assert fake.received_call_2.previous_output == first

final = finish_review(answered_data, refined, fake)
assert fake.call_3_count == 1
assert fake.received_call_3.previous_output == refined
assert final.metric_reviews[0].objective_status == "OK"
assert not (temporary_root / "Output").exists()
```

Also make the fake return one invalid catalog value followed by a valid value and assert exactly one repair call. Make a separate fake raise an OpenAI provider error and assert no repair call occurs.

Expected: the harness prints one success line and creates no output file.

- [ ] **Step 3: Run both HTTP flows with a fake reviewer**

Use `fastapi.testclient.TestClient` and in-memory upload bytes:

1. POST `/start`; assert confidence and questions appear.
2. POST `/refine` with every answer blank or skipped; assert fake Call 2 count stays zero and `OK` appears.
3. POST `/review`; assert expected metrics and complete Objective/Formula fields appear.
4. Start a second review; POST `/refine` with one answer; assert fake Call 2 count increments once.
5. Assert no response contains a download URL and the route set has no `/download/{name}`.
6. Assert `/health` returns `{"status": "ok"}` and `/api/docs` returns 200.

Expected: both HTTP flows complete with status 200 and no local output file is created.

- [ ] **Step 4: Run source and repository safety scans**

```powershell
rg -n "OPENAI_API_KEY" src templates prompts README.md docs\architecture.md
rg -n "output_writer|write_review_outputs|FileResponse|DOWNLOAD_NAME|/download" src templates pyproject.toml README.md docs\architecture.md AGENTS.md
git diff --check
git status --short
```

Expected:

- API-key matches are limited to safe environment-loading/error documentation and never include a secret value.
- No obsolete writer/download symbols remain in current operational files.
- `git diff --check` exits zero.
- `git status --short` lists only intentional feature changes, if any remain uncommitted.

- [ ] **Step 5: Commit verification fixes only when needed**

If Steps 1-4 required a production or documentation correction, stage only those corrected files and commit:

```powershell
git add -- <exact corrected paths>
git commit -m "Complete unified review verification"
```

If no correction was required, do not create an empty commit.

- [ ] **Step 6: Record final evidence**

Capture in the implementation handoff:

- exact commands and exit codes;
- whether Call 2 was observed once for answered input and zero times for blank/skipped input;
- whether the one-repair boundary was observed;
- route set and HTTP statuses;
- confirmation that no output file was created;
- confirmation that no live OpenAI call was made;
- final `git status --short` and commit list.
