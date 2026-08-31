# LangChain Four-Call Workflow Design

## Goal

Use `langchain-core` to manage the human-in-the-loop review workflow while keeping each
production file focused on one responsibility.

The workflow has four distinct LLM calls:

1. Create the initial system understanding and clarification questions.
2. Optionally refine that understanding when the user answers at least one question.
3. Always create the final MRM explanation and flow shown before `OK`.
4. After `OK`, review the workbook metrics and propose additional catalog metrics.

## Scope

- Add `langchain-core` for workflow composition only.
- Keep the OpenAI SDK integration in `ai_reviewer.py`.
- Keep provider prompts in version-controlled YAML files under `prompts/`.
- Remove the cross-field `_validate_field` validation from `schemas.py`.
- Delete `openai_connection.py` and move client construction into `OpenAIReviewer`.
- Preserve the existing FastAPI routes, browser-only output, catalog guardrails, bounded
  repair behavior, and process-local state.
- Do not add LangGraph, agents, a database, authentication, service/repository layers, or
  automated test files.

## Responsibilities

### `schemas.py`

Own only the Pydantic data contracts used by the provider and upload boundary.

- Keep the allowed status literals and list-size constraints.
- Remove `MetricReview.validate_fields()` and `_validate_field()`.
- Do not move that cross-field validation into another production file.

### `ai_reviewer.py`

Own only OpenAI client construction and the four structured provider calls.

- Construct `OpenAI` from explicit API key, model, and temperature arguments.
- Load four external prompt files.
- Expose one clearly named method for each LLM call.
- Continue to use `LLMInput` as input and `LLMOutput` as structured output.
- Keep `store=False` and preserve the current provider-request configuration.
- Append repair feedback to instructions only for the single bounded repair attempt.

### `workflow.py`

Own the complete review process and deterministic guardrails.

`ReviewWorkflow` will create three named LangChain runnables:

- `start_chain`: build `LLMInput`, execute Call 1, then validate the initial output.
- `refine_chain`: use `RunnableBranch` to execute Call 2 only when at least one non-blank
  answer exists, otherwise carry Call 1 forward unchanged; then always execute Call 3 and
  validate the final MRM explanation and flow.
- `metric_review_chain`: execute Call 4 after the API's `OK` transition and validate the
  metric-review result.

The workflow remains split into three invocations because the browser introduces two human
checkpoints: answering or skipping questions, and selecting `OK`. LangChain manages the
process inside and across these named stage runnables; it does not attempt to keep one
blocking invocation alive while waiting for a user.

Each provider step uses the existing one-repair boundary:

1. Invoke the provider once.
2. Validate the result.
3. On `ValueError`, invoke the same provider call once more with concise validation feedback.
4. Do not repair authentication, billing, access, rate-limit, timeout, or connection errors.

### `api.py`

Own only HTTP forms, process-local review state, and page rendering.

- Construct `AppSettings`, `OpenAIReviewer`, and one `ReviewWorkflow` during app creation.
- Invoke the appropriate workflow runnable for `/start`, `/refine`, and `/review`.
- Keep failed refinement and metric-review state available for retry.
- Remove no routes and add no routes.

### Configuration and documentation

- Delete `src/openai_connection.py`.
- Remove `openai_connection` from `pyproject.toml`.
- Add `langchain-core` to runtime dependencies; do not add `langchain-openai`.
- Update `AGENTS.md`, `README.md`, and `docs/architecture.md` to describe the four calls and
  the LangChain workflow boundary.

## Data Flow

```text
QM text + workbook rows + exact metrics.md
                  |
                  v
          Call 1: initial understanding
                  |
        answered at least one question?
             /                 \
           yes                 no
            |                   |
 Call 2: refined understanding  |
             \                 /
                  v
          Call 3: final MRM view
                  |
          browser shows explanation
              and flow diagram
                  |
                 OK
                  |
          Call 4: metric review
                  |
     existing-metric feedback +
     additional catalog metrics
                  |
               browser
```

## Stage Contracts

### Call 1

Fill the base understanding, catalog selection, confidence, and zero to four questions.
Leave `mrm_explanation`, `flow`, `expected_metrics`, and `metric_reviews` empty.

### Call 2

Run only with at least one non-blank, non-skipped answer. Receive the original input, the
Call 1 output, and answered question/answer pairs. Refine the base understanding while
preserving the original questions. Keep all final-view and metric fields empty.

### Call 3

Run for every successful `/refine` submission. Receive the latest understanding from Call 2
or, when Call 2 was skipped, the unchanged Call 1 output. Preserve the base understanding,
fill `mrm_explanation` and a two-to-six-label `flow`, and leave metric fields empty.

### Call 4

Run only after exact `OK`. Receive the full original input, workbook metric rows, catalog,
and Call 3 output. Preserve the final understanding, return exactly one review row for each
workbook metric, and propose additional metrics only from the selected catalog category.

## Validation

Keep these server-side checks in `workflow.py`:

- Catalog category, subcategory, application, and proposed metric membership.
- Case-insensitive matching followed by canonical source spelling.
- Required understanding fields and confidence range.
- Stage-owned fields are empty until their stage.
- Call 2 preserves the original questions.
- Call 3 preserves the latest base understanding and provides explanation plus flow.
- Call 4 preserves the complete Call 3 understanding.
- Metric-review rows cover every workbook metric exactly once.
- Empty Objective and Formula values use `IT IS EMPTY` consistently.

The removed `_validate_field` rules will no longer reject combinations of status, reason, and
revised text. Provider instructions may still describe the desired output format, but the
Pydantic model will not enforce those cross-field combinations.

## Error Handling

- Invalid LLM structure or workflow validation receives at most one repair attempt per call.
- OpenAI provider errors bypass repair and continue through the existing safe API messages.
- A failed Call 2 or Call 3 returns the user to the questions stage with the original state.
- A failed Call 4 returns the user to the final-understanding stage with the `OK` retry path.
- Secrets remain environment-only and are never logged or returned.

## Verification

Automated test files remain out of scope. Verification will use temporary in-memory harnesses
and existing project checks:

- Ruff format and lint checks.
- Python compilation and import checks.
- Editable installation and `pip check`.
- Deterministic fake-reviewer workflow covering both branches:
  - no answers: Call 1, skip Call 2, Call 3, Call 4;
  - answered question: Call 1, Call 2, Call 3, Call 4.
- One-repair and provider-error bypass checks for all four calls.
- FastAPI route and HTTP smoke checks with no live OpenAI request.
- Source scan confirming `openai_connection.py` and stale three-call documentation are gone.
- Git diff checks that preserve unrelated working-tree changes.

