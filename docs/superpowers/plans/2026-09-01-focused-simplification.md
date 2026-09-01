# Focused Simplification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the FastAPI MRM review project substantially shorter and easier to understand while preserving its four-call behavior and validation guardrails.

**Architecture:** Keep the current flat `src/` modules and visible route-to-workflow-to-provider flow. Remove fixed-rule configuration indirection, stale packaging declarations, and decorative frontend code; retain every server-side MRM, retry, catalog, workbook, and provider-error boundary.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic 2, OpenAI Responses API, langchain-core Runnables, Jinja2, openpyxl, PyYAML, vanilla HTML/CSS/JavaScript.

**Spec:** `docs/superpowers/specs/2026-09-01-focused-simplification-design.md`

## Global Constraints

- Accept exactly one `QM-*.txt` file and one `MRM_*.xlsx` workbook.
- Treat `metrics/metrics.md` as the only approved metric catalog.
- Preserve Call 1, optional Call 2, mandatory Call 3, exact `OK`, then Call 4.
- Keep the three `langchain-core` Runnables and all current server-side workflow guardrails.
- Preserve case-insensitive catalog matching followed by normalization to exact catalog spelling.
- Preserve server-owned workbook Objective and Formula values and validate both fields independently.
- Keep provider prompt prose only in `.yml` files under `prompts/`.
- Do not add a database, authentication, provider abstraction, repository/service layer, frontend framework, test suite, or new dependency.
- Do not modify `AGENTS.md` or the existing `docs/mrm-runtime-architecture*` artifacts.
- Do not make a live paid OpenAI request.
- Preserve uncommitted user changes and stage only the files owned by each task.

---

## File map

- Delete `input_format.yml`: remove fixed-contract indirection.
- Modify `src/user_input_reader.py`: own fixed upload filename and workbook-column rules.
- Modify `src/metric_catalog_reader.py`: own fixed catalog section labels.
- Modify `src/api.py`: pass the two uploaded files directly to the reader.
- Modify `src/prompt_loader.py`: validate only the prompt instructions used at runtime.
- Modify `prompts/*.yml`: remove unused `version` keys; keep instructions unchanged.
- Modify `pyproject.toml`: remove the nonexistent CLI and package every live source module.
- Modify `templates/index.html`: retain the four stages in direct, semantic Jinja markup.
- Modify `templates/styles.css`: retain a small responsive visual system.
- Modify `templates/app.js`: keep Skip behavior and duplicate-submit protection with direct functions.
- Create `docs/architecture.md`: document the live runtime flow and module ownership.
- Modify `README.md`: keep setup and structure documentation accurate.

### Task 1: Make fixed input contracts visible

**Files:**
- Delete: `input_format.yml`
- Modify: `src/user_input_reader.py:1-32`
- Modify: `src/metric_catalog_reader.py:1-8`
- Modify: `src/api.py:91-96`

**Interfaces:**
- Consumes: `UploadedFileData(filename: str, content: bytes)` from `src/schemas.py`.
- Produces: `read_user_inputs(qm_file: UploadedFileData, workbook_file: UploadedFileData) -> tuple[str, list[SystemMetric]]` and unchanged `SECTIONS`/`Catalog` exports.

- [ ] **Step 1: Record the current deterministic baseline**

Run:

```powershell
.\.venv\Scripts\python.exe -m compileall -q main.py src
.\.venv\Scripts\python.exe -m ruff check main.py src
```

Expected: both commands exit `0`; Ruff prints `All checks passed!`.

- [ ] **Step 2: Put the upload contract beside the upload reader**

Replace the YAML-loading globals in `src/user_input_reader.py` with these constants and direct signature:

```python
QM_FILENAME = re.compile(r"QM-.+\.txt")
WORKBOOK_FILENAME = re.compile(r"MRM_.+\.xlsx")
WORKBOOK_COLUMNS = {
    "monitoring_metric": ["Monitoring Metric", "Metric"],
    "test_objective": ["Test Objective"],
    "calculation_method": [
        "Calculation Method/Formula",
        "Calcution Method/Formula",
        "Calculation Method / Formula",
    ],
}
EMPTY_METRICS = {"any other(s)"}


def read_user_inputs(
    qm_file: UploadedFileData,
    workbook_file: UploadedFileData,
) -> tuple[str, list[SystemMetric]]:
    return _read_qm(qm_file), _read_workbook(workbook_file)
```

Remove the `Sequence`, `yaml`, and YAML-path imports, remove `_only_file`, and use `WORKBOOK_COLUMNS.items()` when resolving workbook columns.

- [ ] **Step 3: Put the catalog contract beside the catalog parser**

Replace YAML loading in `src/metric_catalog_reader.py` with:

```python
SECTIONS = {
    "subcategories": "Main Subcategories",
    "examples": "Exmaples",
    "metrics": "Metrics",
}
Catalog = dict[str, dict[str, list[str]]]
```

The source catalog uses the exact spelling `Exmaples`; do not silently correct that contract in this refactor.

- [ ] **Step 4: Pass direct uploads from the route**

Change the `/start` route call in `src/api.py` to:

```python
system_main_info, developer_metrics = read_user_inputs(
    qm_upload,
    workbook_upload,
)
```

- [ ] **Step 5: Delete the obsolete configuration file**

Delete only `input_format.yml`. Confirm no production reference remains:

```powershell
rg -n "input_format|FORMAT\[|COLUMNS" main.py src README.md pyproject.toml
```

Expected: no references to `input_format.yml`, `FORMAT[...]`, or the old `COLUMNS` name.

- [ ] **Step 6: Verify the readers and catalog parser**

Run:

```powershell
@'
from pathlib import Path
from metric_catalog_reader import parse_global_metrics, read_global_metrics
from schemas import UploadedFileData
from user_input_reader import read_user_inputs

root = Path.cwd()
catalog = parse_global_metrics(read_global_metrics(root / "metrics" / "metrics.md"))
assert catalog

try:
    read_user_inputs(
        UploadedFileData(filename="wrong.txt", content=b"text"),
        UploadedFileData(filename="wrong.xlsx", content=b"data"),
    )
except ValueError as error:
    assert "QM-*.txt" in str(error)
else:
    raise AssertionError("Invalid QM filename was accepted")

print("reader and catalog checks passed")
'@ | .\.venv\Scripts\python.exe -
```

Expected: `reader and catalog checks passed`.

- [ ] **Step 7: Commit the fixed-contract simplification**

```powershell
git add -- input_format.yml src/user_input_reader.py src/metric_catalog_reader.py src/api.py
git diff --cached --check
git commit -m "refactor: make input contracts explicit"
```

### Task 2: Remove stale prompt and packaging declarations

**Files:**
- Modify: `src/prompt_loader.py:8-20`
- Modify: `prompts/use_case.yml:1`
- Modify: `prompts/use_case_refinement.yml:1`
- Modify: `prompts/mrm_explanation.yml:1`
- Modify: `prompts/metric_review.yml:1`
- Modify: `pyproject.toml:13-31`

**Interfaces:**
- Consumes: YAML mappings containing a non-blank `instructions` string.
- Produces: unchanged `load_prompt(filename: str) -> str`; an installable module set containing `views` and no nonexistent `cli` command.

- [ ] **Step 1: Simplify prompt loading to the value runtime uses**

Use this implementation in `src/prompt_loader.py`:

```python
def load_prompt(filename: str) -> str:
    path = PROMPT_DIR / filename
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Prompt file {filename} must contain a YAML mapping.")

    instructions = data.get("instructions")
    if not isinstance(instructions, str) or not instructions.strip():
        raise ValueError(f"Prompt file {filename} requires instructions.")
    return instructions.strip()
```

- [ ] **Step 2: Remove only unused prompt metadata**

Delete the top-level `version:` line from all four prompt YAML files. Do not change a single character inside any `instructions: |` block.

Verify the instruction blocks are unchanged relative to `HEAD` after ignoring `version:` lines:

```powershell
git diff --word-diff=porcelain -- prompts
```

Expected: four deleted `version:` lines and no instruction-prose edits.

- [ ] **Step 3: Correct the explicit module list**

Delete `[project.scripts]` and `mrm-review = "cli:main"`. In `tool.setuptools.py-modules`, remove `"cli"` and add `"views"`; retain every other current module.

- [ ] **Step 4: Verify prompt loading and imports**

Run:

```powershell
@'
import ai_reviewer
import api
import config
import metric_catalog_reader
import prompt_loader
import schemas
import user_input_reader
import views
import workflow

for filename in (
    "use_case.yml",
    "use_case_refinement.yml",
    "mrm_explanation.yml",
    "metric_review.yml",
):
    assert prompt_loader.load_prompt(filename)

print("production imports and prompts passed")
'@ | .\.venv\Scripts\python.exe -
```

Expected: `production imports and prompts passed`.

- [ ] **Step 5: Build and inspect the package**

Run:

```powershell
$packageCheck = Join-Path $env:TEMP "mrm-package-check-01a05d26"
New-Item -ItemType Directory -Force -Path $packageCheck | Out-Null
.\.venv\Scripts\python.exe -m pip wheel --no-deps --wheel-dir $packageCheck .
$wheel = Get-ChildItem -LiteralPath $packageCheck -Filter "*.whl" | Select-Object -First 1
@'
import sys
import zipfile

with zipfile.ZipFile(sys.argv[1]) as archive:
    names = set(archive.namelist())
assert "views.py" in names
assert "cli.py" not in names
print("package contents passed")
'@ | .\.venv\Scripts\python.exe - $wheel.FullName
```

Expected: wheel creation exits `0` and prints `package contents passed`. Cleanup of the exact temporary directory occurs during final verification after its resolved path is checked.

- [ ] **Step 6: Commit prompt and packaging cleanup**

```powershell
git add -- src/prompt_loader.py prompts pyproject.toml
git diff --cached --check
git commit -m "refactor: remove stale runtime metadata"
```

### Task 3: Reduce the frontend to the four required stages

**Files:**
- Modify: `templates/index.html:11-215`
- Modify: `templates/styles.css:1-430`
- Modify: `templates/app.js:1-46`

**Interfaces:**
- Consumes: Jinja context keys `stage`, `error`, `review_id`, and `result` from `render_page`.
- Produces: the same form actions `/start`, `/refine`, and `/review`; the exact approval label `OK`; skip field names `skip_<index>` and answer field names `answer_<index>`.

- [ ] **Step 1: Replace decorative page framing with one direct shell**

Use this top-level structure in `templates/index.html`:

```html
<body>
  <header class="site-header">
    <div class="container">
      <p class="eyebrow">Model Risk Management</p>
      <h1>MRM Model Review</h1>
      <p>Understand the use case, approve it, and review its metrics.</p>
    </div>
  </header>

  <main class="container">
    {% if error and stage != "error" %}
      <section class="alert" role="alert">
        <h2>This step could not be completed</h2>
        <p>{{ error }}</p>
        <small>Your current review is unchanged. Correct anything needed and retry.</small>
      </section>
    {% endif %}

    {# exactly one of the existing start/questions/understanding/result/error blocks #}
  </main>

  <div class="loading-overlay" id="loading-overlay" role="status" aria-live="polite" hidden>
    <div class="loading-card">
      <span class="loading-spinner" aria-hidden="true"></span>
      <p><strong>Review in progress</strong><br>Please wait while the assessment is completed.</p>
    </div>
  </div>
</body>
```

Keep the existing `<head>` metadata and asset links. Remove the sidebar, enterprise branding, repeated stage badge, decorative numbers, and ornamental marks.

- [ ] **Step 2: Keep one concise block for each stage**

Retain these exact data and action requirements while reformatting nested one-line markup into readable multi-line HTML:

- `start`: two labelled required file inputs and a `Start review` submit button.
- `questions`: business use case, category, subcategory, application, confidence, Input → Processing → Output, every question, answer input, Skip checkbox, and `Continue`.
- `understanding`: MRM explanation, category selection, flow, hidden `review_id`, and a submit button labelled exactly `OK`.
- `result`: MRM explanation, expected-metric table, and independent Objective and Formula review cards including status, reason, revised text, and questions.
- `error`: public error text and a link back to `/`.

Do not rename form fields or route names used by FastAPI.

- [ ] **Step 3: Replace the stylesheet with a small explicit system**

Organize `templates/styles.css` in this order and use only selectors present in the simplified template:

```css
:root {
  color-scheme: light;
  --background: #f5f5f2;
  --surface: #ffffff;
  --text: #1c1c1c;
  --muted: #666666;
  --border: #d8d8d2;
  --accent: #2457d6;
  --danger: #a42323;
  font-family: Inter, ui-sans-serif, system-ui, sans-serif;
}

* { box-sizing: border-box; }
body { margin: 0; background: var(--background); color: var(--text); line-height: 1.5; }
.container { width: min(100% - 2rem, 1100px); margin-inline: auto; }
.site-header { padding: 2.5rem 0 1.5rem; }
.panel { margin-bottom: 1rem; padding: 1.5rem; border: 1px solid var(--border); border-radius: 0.75rem; background: var(--surface); }
button, .button { display: inline-block; padding: 0.75rem 1rem; border: 0; border-radius: 0.5rem; background: var(--accent); color: white; font: inherit; font-weight: 700; cursor: pointer; }
input[type="text"], input[type="file"] { width: 100%; padding: 0.75rem; border: 1px solid var(--border); border-radius: 0.5rem; background: white; font: inherit; }
table { width: 100%; border-collapse: collapse; }
th, td { padding: 0.75rem; border-bottom: 1px solid var(--border); text-align: left; vertical-align: top; }
@media (max-width: 700px) { .grid, .review-fields { grid-template-columns: 1fr; } .table-wrap { overflow-x: auto; } }
```

Add only the declarations needed by `.eyebrow`, `.alert`, `.grid`, `.flow`, `.question`, `.skip`, `.actions`, `.status`, `.review-fields`, `.loading-overlay`, `.loading-card`, and `.loading-spinner`. Target fewer than 220 non-blank CSS lines.

- [ ] **Step 4: Make the JavaScript flow explicit**

Use two named functions and keep the existing behavior:

```javascript
function connectSkipCheckboxes() {
  for (const checkbox of document.querySelectorAll('input[name^="skip_"]')) {
    const index = checkbox.name.replace("skip_", "");
    const answer = document.getElementById(`answer_${index}`);
    if (!answer) continue;

    function updateAnswer() {
      if (checkbox.checked) answer.value = "";
      answer.disabled = checkbox.checked;
    }

    checkbox.addEventListener("change", updateAnswer);
    updateAnswer();
  }
}

function preventDuplicateSubmissions() {
  let submitting = false;
  const overlay = document.getElementById("loading-overlay");
  for (const form of document.querySelectorAll("form")) {
    form.addEventListener("submit", (event) => {
      if (submitting) {
        event.preventDefault();
        return;
      }
      submitting = true;
      form.setAttribute("aria-busy", "true");
      for (const button of form.querySelectorAll('button[type="submit"]')) {
        button.disabled = true;
        button.textContent = "Processing…";
      }
      if (overlay) overlay.hidden = false;
    });
  }
}

connectSkipCheckboxes();
preventDuplicateSubmissions();
```

- [ ] **Step 5: Check required template contracts**

Run:

```powershell
rg -n 'action="\{\{ url_for\(' templates/index.html
rg -n 'name="review_id"|name="answer_|name="skip_|>OK<' templates/index.html
rg -n 'Enterprise Governance|Secure local session|sidebar|stage-pill|section-number' templates
```

Expected: all three form actions and required field names exist; `OK` exists exactly; the final search returns no matches.

- [ ] **Step 6: Commit the frontend simplification**

```powershell
git add -- templates/index.html templates/styles.css templates/app.js
git diff --cached --check
git commit -m "refactor: simplify the review interface"
```

### Task 4: Align documentation with the simplified project

**Files:**
- Create: `docs/architecture.md`
- Modify: `README.md:10-30`

**Interfaces:**
- Consumes: the final production file names and runtime flow from Tasks 1-3.
- Produces: one short source-of-truth architecture page and an accurate README file map.

- [ ] **Step 1: Write the runtime architecture page**

Create `docs/architecture.md` with these sections and facts:

```markdown
# Runtime Architecture

## Flow

Browser → FastAPI route → input reader → workflow → OpenAI reviewer → validation → browser

1. `/start` reads one QM text file and one developer workbook, then invokes Call 1.
2. `/refine` sends real answers to optional Call 2 and always invokes Call 3.
3. `/review` is available only after the exact `OK` submission and invokes Call 4.
4. Failed refinement or review keeps the same `PendingReview.stage` for retry.

## File responsibilities

- `main.py`: creates and starts the FastAPI application.
- `src/api.py`: routes and in-process review state.
- `src/user_input_reader.py`: uploaded TXT and workbook validation/parsing.
- `src/metric_catalog_reader.py`: raw catalog reading and hierarchy parsing.
- `src/schemas.py`: shared Pydantic input/output contracts.
- `src/ai_reviewer.py`: OpenAI client and four named calls.
- `src/workflow.py`: call order, one-repair policy, and output guardrails.
- `src/views.py`: safe public errors and Jinja rendering.
- `src/prompt_loader.py`: YAML prompt loading.
- `templates/`: the server-rendered browser interface.

## State and boundaries

Review state is temporary and process-local. The server owns workbook values and catalog validation. Provider prompt prose stays under `prompts/`; credentials come only from environment variables or `.env.local`; review results are never written to files.
```

- [ ] **Step 2: Update the README file map**

Remove any reference to `input_format.yml` or a CLI command. Keep the existing four-call diagram, setup commands, input contract, and MVP limitations. Make the module descriptions match `docs/architecture.md` without duplicating its detailed flow.

- [ ] **Step 3: Verify documentation against live files**

Run:

```powershell
rg -n 'input_format|cli.py|mrm-review' README.md docs/architecture.md pyproject.toml
rg -n 'Call 1|Call 2|Call 3|OK|Call 4|views.py|workflow.py' README.md docs/architecture.md
```

Expected: the obsolete-name search returns no matches; the architecture terms and live module names are present.

- [ ] **Step 4: Commit documentation alignment**

```powershell
git add -- README.md docs/architecture.md
git diff --cached --check
git commit -m "docs: align architecture with runtime"
```

### Task 5: Verify the complete review flow

**Files:**
- Verify only: `main.py`, `src/`, `templates/`, `prompts/`, `pyproject.toml`, `README.md`, `docs/architecture.md`

**Interfaces:**
- Consumes: `create_app(settings: AppSettings | None, reviewer: OpenAIReviewer | None) -> FastAPI` and the three HTTP form routes.
- Produces: evidence that static checks, packaging, HTTP endpoints, stage gating, retry behavior, and prompt boundaries pass without a live OpenAI request.

- [ ] **Step 1: Run compilation, imports, lint, and dependency checks**

```powershell
.\.venv\Scripts\python.exe -m compileall -q main.py src
.\.venv\Scripts\python.exe -m ruff check main.py src
.\.venv\Scripts\python.exe -m pip check
```

Expected: all commands exit `0`.

- [ ] **Step 2: Run route and HTTP smoke checks with a fake reviewer**

Run this in-memory harness; it deliberately fails Call 3 once to prove the clarification stage is preserved and retryable:

```powershell
@'
import re
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from openpyxl import Workbook
from pydantic import SecretStr

from api import create_app
from config import AppSettings
from schemas import LLMOutput, MetricReview


def understanding(**updates):
    values = {
        "business_use_case": "Answer questions from retrieved documents",
        "main_category": "Non-Agentic",
        "subcategory": "RAG",
        "closest_application": "Q&A",
        "components": ["Retriever", "Generator"],
        "input": "Question",
        "processing": "Retrieve and answer",
        "output": "Answer",
        "understanding_confidence": 90,
        "questions": [],
        "mrm_explanation": "",
        "flow": [],
        "expected_metrics": [],
        "metric_reviews": [],
    }
    values.update(updates)
    return LLMOutput(**values)


class FakeReviewer:
    def __init__(self):
        self.call_3_attempts = 0

    def call_1(self, data, *, repair_feedback=""):
        return understanding()

    def call_2(self, data, *, repair_feedback=""):
        raise AssertionError("Call 2 must be skipped")

    def call_3(self, data, *, repair_feedback=""):
        self.call_3_attempts += 1
        if self.call_3_attempts == 1:
            raise RuntimeError("deliberate retry check")
        return data.previous_output.model_copy(
            update={"mrm_explanation": "The system retrieves evidence before answering.", "flow": ["Question", "Answer"]}
        )

    def call_4(self, data, *, repair_feedback=""):
        return data.previous_output.model_copy(
            update={
                "metric_reviews": [
                    MetricReview(
                        metric="Accuracy",
                        objective_status="OK",
                        objective_reason="",
                        objective_revised="",
                        objective_questions=[],
                        formula_status="OK",
                        formula_reason="",
                        formula_revised="",
                        formula_questions=[],
                    )
                ]
            }
        )


workbook = Workbook()
sheet = workbook.active
sheet.append(["Monitoring Metric", "Test Objective", "Calculation Method/Formula"])
sheet.append(["Accuracy", "Measure correct answers", "Correct / Total"])
buffer = BytesIO()
workbook.save(buffer)
workbook.close()

settings = AppSettings(
    root=Path.cwd(),
    openai_api_key=SecretStr("fake-key"),
    openai_model="fake-model",
    openai_temperature=0.0,
)
client = TestClient(create_app(settings=settings, reviewer=FakeReviewer()))

for path in ("/", "/health", "/static/styles.css", "/api/docs"):
    assert client.get(path).status_code == 200, path

start = client.post(
    "/start",
    files={
        "qm_file": ("QM-demo.txt", b"A retrieval augmented Q&A system.", "text/plain"),
        "workbook_file": ("MRM_demo.xlsx", buffer.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    },
)
assert start.status_code == 200
review_id = re.search(r'name="review_id" value="([a-f0-9]+)"', start.text).group(1)

failed_refine = client.post("/refine", data={"review_id": review_id})
assert failed_refine.status_code == 502
assert 'action="http://testserver/refine"' in failed_refine.text
assert "Clarification questions" in failed_refine.text

refined = client.post("/refine", data={"review_id": review_id})
assert refined.status_code == 200
assert '>OK<' in refined.text

reviewed = client.post("/review", data={"review_id": review_id})
assert reviewed.status_code == 200
assert "Metric review" in reviewed.text
assert "Accuracy" in reviewed.text

print("route, retry, and HTTP smoke checks passed")
'@ | .\.venv\Scripts\python.exe -
```

Expected: `route, retry, and HTTP smoke checks passed`.

- [ ] **Step 3: Verify prompt and secret boundaries**

Run:

```powershell
rg -n 'You are an|Your task is' src main.py
rg -n 'OPENAI_API_KEY\s*=' src main.py
rg -n 'OPENAI_API_KEY' . --glob '!.env.local' --glob '!.venv/**' --glob '!docs/mrm-runtime-architecture*'
```

Expected: no inline provider prompt prose or assigned key in Python; only safe configuration/documentation references to `OPENAI_API_KEY`.

- [ ] **Step 4: Verify the final diff and line reduction**

Run:

```powershell
git diff --check HEAD~4..HEAD
git diff --stat HEAD~4..HEAD
git status --short
```

Expected: no whitespace errors; production/frontend deletions materially exceed additions; only the user's pre-existing `AGENTS.md` and `docs/mrm-runtime-architecture*` changes remain outside the implementation commits.

- [ ] **Step 5: Remove only the verified package-check directory**

Run:

```powershell
$packageCheck = [System.IO.Path]::GetFullPath((Join-Path $env:TEMP "mrm-package-check-01a05d26"))
$tempRoot = [System.IO.Path]::GetFullPath($env:TEMP)
if (-not $packageCheck.StartsWith($tempRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Package-check path is outside the temporary directory."
}
if (Test-Path -LiteralPath $packageCheck) {
    Remove-Item -LiteralPath $packageCheck -Recurse -Force
}
```

Expected: only the exact temporary package-build directory is removed.

- [ ] **Step 6: Record final evidence**

Run:

```powershell
git log -5 --oneline --decorate
git status --short
```

Expected: the four implementation commits are visible after the design/plan commits; user-owned changes remain uncommitted and untouched. Report the live OpenAI provider path as intentionally unverified.
