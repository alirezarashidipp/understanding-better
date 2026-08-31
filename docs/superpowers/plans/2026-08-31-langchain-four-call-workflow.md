# LangChain Four-Call Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a four-call, human-in-the-loop MRM review process managed by `langchain-core` while preserving focused file responsibilities and browser-only output.

**Architecture:** `ReviewWorkflow` owns three named LangChain runnables for the three HTTP-stage invocations. The refinement runnable branches around optional Call 2 and always proceeds to Call 3; the metric-review runnable executes Call 4 after `OK`. `ai_reviewer.py` remains the only OpenAI boundary and `schemas.py` remains data-contract-only.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic 2, OpenAI Responses API, `langchain-core>=1.6,<2`, openpyxl, PyYAML, Jinja2.

**Spec:** `docs/superpowers/specs/2026-08-31-langchain-four-call-workflow-design.md`

## Global Constraints

- Use `langchain-core` for workflow composition only; do not add `langchain-openai` or LangGraph.
- The LLM sequence is Call 1, optional Call 2, always Call 3, then Call 4 only after exact `OK`.
- Keep all provider prompt prose in YAML files under `prompts/`.
- Keep one structured-output repair attempt per call; provider errors bypass repair.
- Keep `metrics/metrics.md` as the only approved metric catalog.
- Keep results display-only in the browser; create no output files.
- Remove `MetricReview.validate_fields()` and `_validate_field()` without relocating those rules.
- Delete `src/openai_connection.py`; `OpenAIReviewer` constructs its own client.
- Preserve the existing `temperature=self.temperature` working-tree change in `src/ai_reviewer.py`.
- Preserve the unrelated existing deletion of `src/cli.py`; do not stage, restore, or modify it.
- Do not create a `tests/` directory or automated test files. Use inline deterministic harnesses.
- Do not make a live OpenAI request during verification.

---

### Task 1: Separate the Four Provider-Stage Contracts

**Files:**
- Modify: `src/schemas.py`
- Modify: `prompts/use_case_refinement.yml`
- Create: `prompts/mrm_explanation.yml`
- Modify: `prompts/metric_review.yml`

**Interfaces:**
- Consumes: existing `LLMInput` and `LLMOutput` models.
- Produces: a permissive `MetricReview` data model and distinct prompt instructions for Calls 2, 3, and 4.

- [ ] **Step 1: Run the current schema harness to capture the validation being removed**

Run:

```powershell
$env:PYTHONPATH = (Resolve-Path src).Path
@'
from pydantic import ValidationError
from schemas import MetricReview

try:
    MetricReview(
        metric="Accuracy",
        objective_status="OK",
        objective_reason="",
        objective_revised="unwanted but allowed after this change",
        objective_questions=[],
        formula_status="OK",
        formula_reason="",
        formula_revised="",
        formula_questions=[],
    )
except ValidationError:
    print("current cross-field validation rejects the row")
else:
    raise AssertionError("expected the current validator to reject the row")
'@ | .\.venv\Scripts\python.exe -
```

Expected: `current cross-field validation rejects the row`.

- [ ] **Step 2: Remove the cross-field validator from `schemas.py`**

Make these exact structural changes:

```python
from pydantic import BaseModel, ConfigDict, Field
```

Keep `MetricReview` as fields only:

```python
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
```

Delete `MetricReview.validate_fields()` and the complete `_validate_field()` function. Retain the `Status` literal and question-count limits.

- [ ] **Step 3: Make Call 2 refinement-only**

Update `prompts/use_case_refinement.yml` so it requires the model to refine the base understanding from answered question/answer pairs, preserve the Call 1 questions, and keep these fields empty:

```yaml
version: "3.0"
instructions: |-
  Act as an MRM reviewer. Use system_extra_info and previous_output to refine
  the system understanding. Preserve answered facts and never invent an answer
  for a skipped or absent question. Catalog selections must use exact values
  from global_metrics.

  Return the complete LLMOutput schema. Preserve the original Call 1 questions,
  refine only the base understanding fields, and keep mrm_explanation empty.
  Keep flow, expected_metrics, and metric_reviews as empty lists.
```

- [ ] **Step 4: Add the Call 3 final-MRM prompt**

Create `prompts/mrm_explanation.yml`:

```yaml
version: "1.0"
instructions: |-
  Act as an MRM reviewer. Use previous_output as the latest system understanding.
  Preserve every base understanding field and the original questions exactly.

  Return the complete LLMOutput schema. Fill mrm_explanation with the final
  product explanation from an MRM perspective and fill flow with two to six
  concise business and risk labels. Keep expected_metrics and metric_reviews
  as empty lists. Do not invent source facts or catalog values.
```

- [ ] **Step 5: Re-label the metric prompt as Call 4 behavior**

Set `prompts/metric_review.yml` to:

```yaml
version: "4.0"
instructions: |-
  Act as an MRM reviewer. Preserve every understanding field from the Call 3
  previous_output. Select expected_metrics only from the Metrics section of
  the selected global_metrics category. Return exactly one metric_reviews row
  for every system_metrics row.

  Assess Objective and Formula independently. Use only OK, IT IS EMPTY, or
  NEEDS REVISION. NEEDS REVISION requires a short reason and corrected text;
  IT IS EMPTY requires proposed text; OK has empty revised text. Ask at most
  three questions for each field. Return the complete LLMOutput schema.
```

Do not move any prompt prose into Python.

- [ ] **Step 6: Run the new schema and prompt harness**

Run:

```powershell
$env:PYTHONPATH = (Resolve-Path src).Path
@'
from schemas import MetricReview
from prompt_loader import load_prompt

row = MetricReview(
    metric="Accuracy",
    objective_status="OK",
    objective_reason="",
    objective_revised="now accepted",
    objective_questions=[],
    formula_status="OK",
    formula_reason="",
    formula_revised="",
    formula_questions=[],
)
assert row.objective_revised == "now accepted"
assert "mrm_explanation" in load_prompt("mrm_explanation.yml")
assert "refine only" in load_prompt("use_case_refinement.yml")
print("schema and four-stage prompts passed")
'@ | .\.venv\Scripts\python.exe -
```

Expected: `schema and four-stage prompts passed`.

- [ ] **Step 7: Commit the contract and prompt split**

```powershell
git add -- src/schemas.py prompts/use_case_refinement.yml prompts/mrm_explanation.yml prompts/metric_review.yml
git diff --cached --check
git commit -m "Split final understanding from metric review"
```

---

### Task 2: Make `ai_reviewer.py` the Complete OpenAI Boundary

**Files:**
- Modify: `src/ai_reviewer.py`
- Delete: `src/openai_connection.py`

**Interfaces:**
- Consumes: `api_key: str`, `model: str`, `temperature: float`, `LLMInput`, and optional repair feedback.
- Produces: `OpenAIReviewer.call_1`, `call_2`, `call_3`, and `call_4`, each returning `LLMOutput`.

- [ ] **Step 1: Run a failing interface check for Call 4**

Run:

```powershell
$env:PYTHONPATH = (Resolve-Path src).Path
.\.venv\Scripts\python.exe -c "from ai_reviewer import OpenAIReviewer; assert hasattr(OpenAIReviewer, 'call_4')"
```

Expected: FAIL because `call_4` does not exist.

- [ ] **Step 2: Move client construction into `OpenAIReviewer`**

Change the constructor to:

```python
class OpenAIReviewer:
    def __init__(self, api_key: str, model: str, temperature: float) -> None:
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature
```

Keep API key handling inside construction only; never store, print, or serialize the key separately.

- [ ] **Step 3: Load four prompts and expose four calls**

Use these constants and methods:

```python
CALL_1_PROMPT = load_prompt("use_case.yml")
CALL_2_PROMPT = load_prompt("use_case_refinement.yml")
CALL_3_PROMPT = load_prompt("mrm_explanation.yml")
CALL_4_PROMPT = load_prompt("metric_review.yml")

def call_1(self, data: LLMInput, *, repair_feedback: str = "") -> LLMOutput:
    return self._request(CALL_1_PROMPT, data, repair_feedback)

def call_2(self, data: LLMInput, *, repair_feedback: str = "") -> LLMOutput:
    return self._request(CALL_2_PROMPT, data, repair_feedback)

def call_3(self, data: LLMInput, *, repair_feedback: str = "") -> LLMOutput:
    return self._request(CALL_3_PROMPT, data, repair_feedback)

def call_4(self, data: LLMInput, *, repair_feedback: str = "") -> LLMOutput:
    return self._request(CALL_4_PROMPT, data, repair_feedback)
```

Preserve the existing `_request()` behavior, including `temperature=self.temperature`, `store=False`, JSON serialization with aliases, and `text_format=LLMOutput`.

- [ ] **Step 4: Delete the redundant connection module**

Delete `src/openai_connection.py`. Do not create a replacement connection or provider-wrapper file.

- [ ] **Step 5: Verify the reviewer without a network call**

Run an inline fake by constructing the instance with `OpenAIReviewer.__new__` so no real client is created:

```powershell
$env:PYTHONPATH = (Resolve-Path src).Path
@'
from types import SimpleNamespace
from ai_reviewer import OpenAIReviewer

reviewer = OpenAIReviewer.__new__(OpenAIReviewer)
reviewer.client = SimpleNamespace()
reviewer.model = "test-model"
reviewer.temperature = 0.0
assert all(hasattr(reviewer, name) for name in ("call_1", "call_2", "call_3", "call_4"))
print("four reviewer calls passed")
'@ | .\.venv\Scripts\python.exe -
```

Expected: `four reviewer calls passed`.

- [ ] **Step 6: Commit the provider boundary**

The `temperature` line is now explicitly part of the approved design, so stage the complete reviewer change:

```powershell
git add -- src/ai_reviewer.py src/openai_connection.py
git diff --cached --check
git commit -m "Keep OpenAI calls in one reviewer module"
```

Do not stage the unrelated `src/cli.py` deletion.

---

### Task 3: Build the LangChain Four-Call Workflow

**Files:**
- Modify: `requirements.txt`
- Modify: `src/workflow.py`

**Interfaces:**
- Consumes: an `AIReviewer` with `call_1` through `call_4` and the existing upload/catalog inputs.
- Produces: `ReviewWorkflow.start_chain`, `refine_chain`, and `metric_review_chain`; each is a LangChain `Runnable` invoked at one HTTP stage.
- Produces: `StartReviewRequest`, `RefineReviewRequest`, and `MetricReviewRequest` typed request dataclasses.

- [ ] **Step 1: Add and install the focused dependency**

Add this line to `requirements.txt`:

```text
langchain-core>=1.6,<2
```

Then run:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip check
```

Expected: installation succeeds and `pip check` prints `No broken requirements found.`

- [ ] **Step 2: Run the pre-change workflow interface check**

Run:

```powershell
$env:PYTHONPATH = (Resolve-Path src).Path
.\.venv\Scripts\python.exe -c "from workflow import ReviewWorkflow"
```

Expected: FAIL because `ReviewWorkflow` does not exist.

- [ ] **Step 3: Extend the reviewer protocol to four calls**

Keep the existing signatures and add:

```python
class AIReviewer(Protocol):
    def call_1(self, data: LLMInput, *, repair_feedback: str = "") -> LLMOutput: ...
    def call_2(self, data: LLMInput, *, repair_feedback: str = "") -> LLMOutput: ...
    def call_3(self, data: LLMInput, *, repair_feedback: str = "") -> LLMOutput: ...
    def call_4(self, data: LLMInput, *, repair_feedback: str = "") -> LLMOutput: ...
```

- [ ] **Step 4: Add typed requests for runnable inputs**

Define these immutable dataclasses in `workflow.py`:

```python
@dataclass(frozen=True)
class StartReviewRequest:
    catalog_path: Path
    qm_files: list[UploadedFileData]
    workbook_files: list[UploadedFileData]


@dataclass(frozen=True)
class RefineReviewRequest:
    data: LLMInput
    previous_output: LLMOutput
    answers: list[ExtraInfo]


@dataclass(frozen=True)
class MetricReviewRequest:
    data: LLMInput
    previous_output: LLMOutput
```

Use a private `RefinementState` dataclass containing `data`, `output`, and `has_answers` for the internal branch.

- [ ] **Step 5: Create the three named runnables**

Import `RunnableBranch` and `RunnableLambda` from `langchain_core.runnables`. Build the workflow in one class:

```python
class ReviewWorkflow:
    def __init__(self, reviewer: AIReviewer) -> None:
        self.reviewer = reviewer
        self.start_chain = RunnableLambda(self._start).with_config(run_name="start_review")
        optional_refinement = RunnableBranch(
            (lambda state: state.has_answers, RunnableLambda(self._call_2)),
            RunnableLambda(self._skip_call_2),
        )
        self.refine_chain = (
            RunnableLambda(self._prepare_refinement)
            | optional_refinement
            | RunnableLambda(self._call_3)
        ).with_config(run_name="refine_and_finalize")
        self.metric_review_chain = RunnableLambda(self._call_4).with_config(
            run_name="metric_review"
        )
```

Do not create generic chain factories, base workflow classes, or additional production modules.

- [ ] **Step 6: Implement Call 1 and the optional Call 2 branch**

Implement the methods explicitly:

```python
def _start(self, request: StartReviewRequest) -> ReviewState:
    system_main_info, system_metrics = read_user_inputs(
        request.qm_files,
        request.workbook_files,
    )
    data = LLMInput(
        system_main_info=system_main_info,
        global_metrics=read_global_metrics(request.catalog_path),
        system_metrics=system_metrics,
        system_extra_info=[],
        previous_output=None,
    )
    result = _call_with_one_repair(
        lambda feedback: self.reviewer.call_1(data, repair_feedback=feedback),
        lambda output: _validate_output(data, output, stage=1),
    )
    return data, result


def _prepare_refinement(self, request: RefineReviewRequest) -> RefinementState:
    answers = [item for item in request.answers if item.answer.strip()]
    next_input = request.data.model_copy(
        update={
            "system_extra_info": answers,
            "previous_output": request.previous_output,
        }
    )
    return RefinementState(
        data=next_input,
        output=request.previous_output,
        has_answers=bool(answers),
    )


def _call_2(self, state: RefinementState) -> ReviewState:
    result = _call_with_one_repair(
        lambda feedback: self.reviewer.call_2(state.data, repair_feedback=feedback),
        lambda output: _validate_output(state.data, output, stage=2),
    )
    return state.data, result


def _skip_call_2(self, state: RefinementState) -> ReviewState:
    return state.data, state.output
```

- [ ] **Step 7: Implement always-on Call 3 and post-OK Call 4**

Implement:

```python
def _call_3(self, state: ReviewState) -> ReviewState:
    data, previous_output = state
    final_input = data.model_copy(update={"previous_output": previous_output})
    result = _call_with_one_repair(
        lambda feedback: self.reviewer.call_3(final_input, repair_feedback=feedback),
        lambda output: _validate_output(final_input, output, stage=3),
    )
    return final_input, result


def _call_4(self, request: MetricReviewRequest) -> LLMOutput:
    metric_input = request.data.model_copy(
        update={"previous_output": request.previous_output}
    )
    return _call_with_one_repair(
        lambda feedback: self.reviewer.call_4(metric_input, repair_feedback=feedback),
        lambda output: _validate_output(metric_input, output, stage=4),
    )
```

- [ ] **Step 8: Split stage validation across four calls**

Retain canonical catalog normalization and required base-field checks for all stages. Apply these ownership rules:

```text
stage 1: explanation, flow, expected metrics, and reviews are empty
stage 2: original questions preserved; explanation, flow, expected metrics, and reviews are empty
stage 3: latest base understanding preserved; explanation non-empty; flow length 2-6; metric fields empty
stage 4: complete Call 3 understanding preserved; expected metrics and workbook review rows validated
```

Change metric-result validation to run only at stage 4. Keep case-insensitive source normalization, duplicate rejection, exact workbook coverage, and empty-field status checks.

Use separate preserved-field tuples so Call 3 preserves the latest base understanding and Call 4 preserves the complete final view:

```python
base_fields = (
    "business_use_case",
    "system_type",
    "main_category",
    "subcategory",
    "closest_application",
    "components",
    "input",
    "processing",
    "output",
    "understanding_confidence",
    "questions",
)
final_fields = (*base_fields, "mrm_explanation", "flow")
```

- [ ] **Step 9: Run a deterministic four-call branch harness**

Use a temporary directory, in-memory workbook, exact catalog text, and fake reviewer. The fake must count each method and return valid stage-owned fields. Assert:

```python
first_state = workflow.start_chain.invoke(start_request)
assert fake.call_counts == [1, 0, 0, 0]

ready_without_answers = workflow.refine_chain.invoke(
    RefineReviewRequest(*first_state, answers=[])
)
assert fake.call_counts == [1, 0, 1, 0]

final_without_answers = workflow.metric_review_chain.invoke(
    MetricReviewRequest(*ready_without_answers)
)
assert fake.call_counts == [1, 0, 1, 1]

first_state = workflow.start_chain.invoke(start_request)
ready_with_answer = workflow.refine_chain.invoke(
    RefineReviewRequest(
        *first_state,
        answers=[ExtraInfo(question="Data source?", answer="Transactions")],
    )
)
assert fake.call_counts == [2, 1, 2, 1]
```

Also assert Call 3 receives Call 2 output in the answered branch and Call 1 output in the skipped branch. Add one invalid fake result followed by a valid result and assert only that call count increases by two. Raise an OpenAI provider error from a separate fake and assert it is not repaired.

Expected: the harness prints `four-call LangChain workflow passed` and performs no network request.

- [ ] **Step 10: Commit the LangChain workflow**

```powershell
git add -- requirements.txt src/workflow.py
git diff --cached --check
git commit -m "Manage four review calls with LangChain"
```

---

### Task 4: Wire FastAPI to the Workflow Object

**Files:**
- Modify: `src/api.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: `ReviewWorkflow` plus its three request dataclasses.
- Produces: unchanged `/start`, `/refine`, `/review`, `/health`, and `/api/docs` behavior with four provider-call stages.

- [ ] **Step 1: Update app construction**

Remove the `openai_connection` import. When no reviewer is injected, construct:

```python
settings = AppSettings.from_env(project_root)
active_reviewer = OpenAIReviewer(
    api_key=settings.openai_api_key.get_secret_value(),
    model=settings.openai_model,
    temperature=settings.openai_temperature,
)
workflow = ReviewWorkflow(active_reviewer)
```

The injected fake-reviewer path must construct the same `ReviewWorkflow` without reading environment secrets.

- [ ] **Step 2: Invoke the three workflow runnables from routes**

Use:

```python
state = workflow.start_chain.invoke(
    StartReviewRequest(
        catalog_path=project_root / "metrics" / "metrics.md",
        qm_files=qm_files,
        workbook_files=workbook_files,
    )
)
```

Use `workflow.refine_chain.invoke(RefineReviewRequest(...))` in `/refine`, and `workflow.metric_review_chain.invoke(MetricReviewRequest(...))` in `/review`.

Keep the current state transitions: questions state is consumed only after Call 3 succeeds; ready state is consumed only after Call 4 succeeds. Existing exception handling and safe provider messages remain.

- [ ] **Step 3: Remove the deleted connection module from packaging**

Delete only the `"openai_connection"` item from `tool.setuptools.py-modules`. Do not change the existing `cli` entry or stage the user's `src/cli.py` deletion as part of this feature.

- [ ] **Step 4: Run route and fake-reviewer HTTP checks**

Use `fastapi.testclient.TestClient` with in-memory uploads and a fake four-call reviewer:

1. POST `/start`; assert confidence and questions appear.
2. POST `/refine` with every answer blank; assert Call 2 count is zero, Call 3 count is one, and `OK` appears.
3. POST `/review`; assert Call 4 count is one and metric results appear.
4. Repeat with one answer; assert Calls 1, 2, 3, and 4 each run once for that review.
5. Assert `/health` returns 200 and `/api/docs` returns 200.
6. Assert the route set remains unchanged and no output files are created.

Expected: print `four-call HTTP flow passed` without contacting OpenAI.

- [ ] **Step 5: Commit API wiring and packaging cleanup**

```powershell
git add -- src/api.py pyproject.toml
git diff --cached --check
git commit -m "Wire FastAPI to the review workflow"
```

Confirm `git diff --cached --name-status` does not include `src/cli.py` before committing.

---

### Task 5: Align Operational Documentation

**Files:**
- Modify: `AGENTS.md`
- Modify: `README.md`
- Modify: `docs/architecture.md`

**Interfaces:**
- Consumes: the implemented four-call flow and module boundaries.
- Produces: current setup, runtime-flow, ownership, and verification instructions.

- [ ] **Step 1: Update project rules in `AGENTS.md`**

Document exactly:

- Call 1 creates initial understanding and questions.
- Call 2 runs only with at least one real answer and refines base understanding only.
- Call 3 always creates the final MRM explanation and flow before exact `OK`.
- Call 4 runs after `OK` and reviews workbook metrics plus additional catalog metrics.
- `workflow.py` owns the `langchain-core` runnables.
- `ai_reviewer.py` owns OpenAI client construction and four provider calls.
- `openai_connection.py` no longer exists.

Remove contradictory three-call statements while retaining all unrelated project rules.

- [ ] **Step 2: Update `README.md` user flow and setup**

Replace the three-call diagrams and numbered flow with the four-call sequence. State that Call 3 runs even when Call 2 is skipped. Add `langchain-core` to the architecture description without describing LangGraph or agents.

- [ ] **Step 3: Update `docs/architecture.md` boundaries and contracts**

Describe `ReviewWorkflow.start_chain`, `refine_chain`, and `metric_review_chain`, the `RunnableBranch` around Call 2, and the two browser checkpoints. Update stage-owned `LLMOutput` fields through Call 4.

- [ ] **Step 4: Scan for stale operational documentation**

Run:

```powershell
rg -n "three calls|three structured|Call 3 returns expected|Call 3.*metric|openai_connection|Call 1.*Call 2.*Call 3" AGENTS.md README.md docs\architecture.md
```

Expected: no stale three-call or deleted-module statements remain. Historical specs and plans are excluded from this scan.

- [ ] **Step 5: Commit documentation**

```powershell
git add -- AGENTS.md README.md docs/architecture.md
git diff --cached --check
git commit -m "Document the four-call review flow"
```

---

### Task 6: Run Full Deterministic Verification

**Files:**
- Modify only when a verification failure identifies a defect in a production or operational-documentation file already listed above.

**Interfaces:**
- Verifies: dependency health, imports, formatting, four call counts, optional Call 2, always-on Call 3, post-OK Call 4, repair bounds, route behavior, state preservation, and repository safety.

- [ ] **Step 1: Run formatting, lint, compilation, import, and dependency checks**

```powershell
.\.venv\Scripts\ruff.exe format --check src main.py
.\.venv\Scripts\ruff.exe check src main.py
.\.venv\Scripts\python.exe -m compileall -q src main.py
$env:PYTHONPATH = (Resolve-Path src).Path
.\.venv\Scripts\python.exe -c "from api import create_app; from workflow import ReviewWorkflow; from ai_reviewer import OpenAIReviewer; print('imports passed')"
.\.venv\Scripts\python.exe -m pip check
```

Expected: every command exits zero, imports print `imports passed`, and dependencies are healthy.

- [ ] **Step 2: Re-run the complete deterministic workflow harness**

Assert these exact final counts for independent reviews:

```text
no-answer review: Call 1 = 1, Call 2 = 0, Call 3 = 1, Call 4 = 1
answered review:  Call 1 = 1, Call 2 = 1, Call 3 = 1, Call 4 = 1
```

Assert every invalid structured stage receives at most one repair, provider errors receive none, Call 3 input points to the latest prior output, and Call 4 input points to Call 3.

- [ ] **Step 3: Re-run both HTTP flows**

Verify `/start`, `/refine`, `/review`, `/health`, `/api/docs`, same-stage retry behavior, visible final explanation/flow before `OK`, visible metric results after `OK`, and absence of output files or download routes.

- [ ] **Step 4: Run source and Git safety checks**

```powershell
rg -n "from openai_connection|import openai_connection|create_openai_client" src pyproject.toml
rg -n "OPENAI_API_KEY" src templates prompts README.md docs\architecture.md
git diff --check
git status --short
git log -6 --oneline
```

Expected:

- no deleted connection-module imports remain;
- API-key matches contain no secret value;
- `git diff --check` exits zero;
- `src/cli.py` remains an unrelated unstaged deletion;
- only intentional feature changes or the preserved unrelated deletion remain.

- [ ] **Step 5: Commit verification fixes only if required**

If verification required a correction, stage only the specific files corrected in that step, inspect `git diff --cached --name-status`, run `git diff --cached --check`, and commit them with message `Complete four-call workflow verification`.

If no correction was required, do not create an empty commit. Never stage `src/cli.py` as part of this feature.
