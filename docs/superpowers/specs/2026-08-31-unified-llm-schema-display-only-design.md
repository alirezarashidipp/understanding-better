# Unified LLM Schema and Display-Only Review Design

## Goal

Replace the current stage-specific review contracts with one stable JSON input schema and one
stable JSON output schema. All three OpenAI calls use these same two top-level contracts. Later
fields remain empty until the call responsible for them runs.

The application remains a local, single-user FastAPI MVP. It stores unfinished review state only
in process memory and shows the completed review in the browser. It no longer creates or offers
downloadable output workbooks.

## Input Contract

Every OpenAI call receives one `LLMInput` object with five keys:

```json
{
  "system_main_info": "Exact text from the selected QM-*.txt file",
  "global_metrics": "Exact Markdown text from metrics/metrics.md",
  "system_metrics": [
    {
      "Monitoring Metric": "Accuracy",
      "Test Objective": "Accuracy remains above 90%",
      "Calculation Method/Formula": "Correct predictions / Total predictions"
    }
  ],
  "system_extra_info": [],
  "previous_output": null
}
```

### Field rules

- `system_main_info` is the decoded QM text exactly as supplied. The application does not add a
  filename, label, summary, or other content.
- `global_metrics` is the complete text of `metrics/metrics.md`. It is not converted into a nested
  JSON catalog before being sent to OpenAI.
- `system_metrics` contains one flat object per developer workbook row and preserves the three
  approved column names in the serialized JSON.
- `system_extra_info` is empty for Call 1. It contains only answered question-and-answer pairs for
  Call 2 and Call 3. Skipped and blank answers are omitted.
- `previous_output` is `null` for Call 1, the Call 1 output for Call 2, and the latest available
  output for Call 3.

Python may use readable snake_case attribute names with Pydantic aliases for the three Excel
column labels. Serialization sent to OpenAI must use the exact labels shown above.

## Output Contract

Every OpenAI call returns the complete `LLMOutput` schema:

```json
{
  "business_use_case": "",
  "system_type": "",
  "main_category": "",
  "subcategory": "",
  "closest_application": "",
  "components": [],
  "input": "",
  "processing": "",
  "output": "",
  "understanding_confidence": null,
  "questions": [],
  "mrm_explanation": "",
  "flow": [],
  "expected_metrics": [],
  "metric_reviews": []
}
```

All fields are required by the structured-output schema. A field that belongs to a later call uses
an empty string, empty list, or `null` until that call fills it. Later calls return the complete
result again rather than returning a partial patch.

### Call ownership

- Call 1 fills the system understanding, catalog selection, confidence, and zero to four
  clarification questions. Explanation, flow, expected metrics, and reviews remain empty.
- Call 2 uses answered clarification information and the Call 1 output. It returns the updated
  understanding plus `mrm_explanation` and `flow`. Metric fields remain empty.
- Call 3 preserves the latest understanding and fills `expected_metrics` and `metric_reviews`.

When filled, `understanding_confidence` is an integer from 0 through 100. `system_type` remains
limited to `RAG`, `LLM`, `Traditional ML`, `Agentic`, `Hybrid`, or `Other`.

Each `expected_metrics` row contains:

```json
{
  "name": "Accuracy",
  "applicability_reason": "Accuracy is required for this use case",
  "test_objective": "Accuracy remains above the approved threshold",
  "calculation_method": "Correct predictions / Total predictions"
}
```

Each `metric_reviews` row is flat:

```json
{
  "metric": "Accuracy",
  "objective_status": "OK",
  "objective_reason": "",
  "objective_revised": "",
  "objective_questions": [],
  "formula_status": "NEEDS REVISION",
  "formula_reason": "The denominator is missing",
  "formula_revised": "Correct predictions / Total predictions",
  "formula_questions": []
}
```

The allowed Objective and Formula statuses remain `OK`, `IT IS EMPTY`, and `NEEDS REVISION`.
`NEEDS REVISION` requires a short reason and revised text. Each field may contain at most three
questions.

## Supporting Row Models

`LLMInput` and `LLMOutput` are the only top-level provider contracts. Small Pydantic row models
are allowed only where they make nested list items explicit:

- `SystemMetric`
- `ExtraInfo`
- `ExpectedMetric`
- `MetricReview`

Stage-specific provider models and wrapper models are removed.

## Call Flow

```text
selected QM text + selected workbook + metrics.md
                       |
                       v
                    Call 1
                       |
                       v
          show understanding and questions
                       |
                     Next
                       |
          any non-blank answer supplied?
              /                    \
            yes                    no
             |                      |
          Call 2              skip Call 2
              \                    /
               v                  v
          show final understanding and OK
                       |
                      OK
                       |
                    Call 3
                       |
                       v
       show complete metric results in browser
```

Call 2 runs only when at least one clarification question has a non-blank, non-skipped answer. If
Call 1 returns no questions, or the user answers none of them, the Call 1 output becomes the latest
output and the application proceeds without Call 2.

Call 3 remains behind the exact `OK` button.

## Catalog Handling and Validation

The exact Markdown source is sent in `global_metrics`. Separately, Python reads the same text into
a minimal internal catalog used only to validate provider output. This internal representation is
not sent to OpenAI.

The parser recognizes:

- `##` main-category headings
- `Main Subcategories`
- `Exmaples`, preserving the spelling used in the approved source file
- `Metrics`

Validation remains case-insensitive and normalizes accepted values to source spelling. Python
rejects:

- a main category not present in the file;
- a subcategory that does not belong to the selected category;
- a `closest_application` value not listed under that category's `Exmaples` section;
- an expected metric not listed under the selected category;
- missing or duplicate review rows for developer workbook metrics;
- invalid Objective or Formula statuses and invalid revision fields.

## Provider Calls and Repair

`OpenAIReviewer` exposes three direct methods for Call 1, Call 2, and Call 3. A small private
request helper may remove repeated OpenAI client syntax, but no provider interface, factory, or
service layer is added.

The JSON input remains exactly `LLMInput`. If a structured result fails validation, concise repair
feedback is appended to the loaded YAML instructions for the one allowed repair attempt; it is not
added as an extra JSON key. Authentication, billing, access, rate-limit, timeout, and connection
errors are not repaired automatically.

Provider instructions remain in the three existing version-controlled YAML prompt files.

## Runtime State

The API keeps two process-local dictionaries:

- reviews waiting for `Next`;
- reviews waiting for `OK`.

Each entry contains the current `LLMInput` and latest `LLMOutput`. No database, repository, state
manager, or persistence abstraction is introduced. A process restart discards unfinished reviews.

## Frontend

The existing stages remain recognizable:

1. Select the QM text and developer workbook.
2. View Call 1 understanding and optionally answer or skip questions.
3. Select `Next`; Call 2 runs only when at least one answer exists.
4. View the latest understanding and select exactly `OK`.
5. View the complete Call 3 result.

The final page displays:

- final system understanding and flow;
- expected metrics with their reason, proposed objective, and proposed formula;
- every developer metric with flat Objective and Formula assessment details.

Download buttons and download routes are removed.

## Removed Code

The implementation removes:

- `src/output_writer.py`;
- `OutputPair` and `CompletedReview`;
- `PendingReview` and `ReadyForMetricReview`;
- stage-specific provider output schemas replaced by `LLMOutput`;
- output-writing calls from `workflow.py`;
- `/download/{name}` and its filename/path validation;
- frontend download links;
- `output_writer` from package metadata.

Existing ignored workbooks already present under `Output/` are user data and are not deleted. The
application simply stops creating new ones.

## Module Boundaries

- `schemas.py`: the two top-level LLM contracts and their small row models.
- `user_input_reader.py`: validation and reading of the selected QM text and workbook.
- `metric_catalog_reader.py`: exact Markdown reading plus minimal internal validation parsing.
- `ai_reviewer.py`: the three structured OpenAI calls.
- `workflow.py`: linear call sequencing, optional Call 2, and output guardrails.
- `api.py`: multipart input, process-local state, routes, and rendering.
- `templates/`: the display-only browser flow.

No service, repository, adapter, factory, database, authentication, background job, or multi-agent
layer is added.

## Verification

Automated test files remain out of scope. Completion requires fresh evidence from:

- Ruff lint and format checks;
- Python compilation and imports;
- `pip check` and editable installation;
- deterministic in-memory QM, workbook, catalog, and fake-reviewer checks;
- a fake flow where an answer causes Call 2;
- a fake flow where no answer skips Call 2;
- validation checks for invented catalog values and malformed metric reviews;
- route inspection confirming the download route is absent;
- HTTP smoke checks for the page, health endpoint, and three review stages;
- `git diff --check`.

No paid or live OpenAI request is part of deterministic verification.
