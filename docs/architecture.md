# MRM Model Review Architecture

## Purpose

This repository contains one local FastAPI MVP for use-case understanding and monitoring-metric review.

## Runtime Flow

```text
QM text + workbook rows + exact metrics.md
                  |
                  v
        Call 1: initial understanding
                  |
       at least one answered question?
           /                 \
         yes                 no
          |                   |
 Call 2: refined understanding|
           \                 /
                  v
        Call 3: final MRM explanation and flow
                  |
             browser + OK
                  |
        Call 4: metric review and proposals
                  |
                  v
                browser
```

Call 2 runs only when at least one non-blank, non-skipped answer exists. Call 3 always runs
after the questions form and produces the final MRM view shown before `OK`. Call 4 is reachable
only after the button labelled exactly `OK`. No result file is created.

## LangChain Workflow

`ReviewWorkflow` owns three named `langchain-core` runnables because the browser creates two
human checkpoints:

- `start_chain` builds `LLMInput`, runs Call 1, and validates the initial understanding.
- `refine_chain` uses `RunnableBranch` to run or skip Call 2, then always runs Call 3.
- `metric_review_chain` runs Call 4 after the API receives `OK`.

The runnables manage orchestration only. They do not hide file reading, OpenAI calls, validation,
or FastAPI state behind additional service or repository layers.

## Data Contract

`LLMInput` always contains five keys:

- `system_main_info`: exact decoded QM text
- `global_metrics`: exact full Markdown catalog
- `system_metrics`: flat three-column workbook rows
- `system_extra_info`: answered question/answer pairs only
- `previous_output`: null for Call 1, otherwise the latest `LLMOutput`

All four calls return the complete `LLMOutput`. Later-stage fields remain empty until their
stage. Call 1 owns initial understanding and questions. Call 2 may refine only the base
understanding. Call 3 owns `mrm_explanation` and `flow`. Call 4 owns `expected_metrics` and
`metric_reviews`.

The raw catalog string is sent to OpenAI. A separate minimal parser creates an internal
dictionary only for case-insensitive validation and source-spelling normalization.

## Module Boundaries

- `config.py` reads local runtime configuration.
- `schemas.py` defines provider and upload data contracts.
- `user_input_reader.py` reads the selected QM file and workbook.
- `metric_catalog_reader.py` reads raw catalog text and parses its validation view.
- `prompt_loader.py` loads versioned YAML instructions.
- `ai_reviewer.py` constructs the OpenAI client and sends four structured requests.
- `workflow.py` owns the LangChain runnables, call sequencing, repair boundary, and guardrails.
- `api.py` owns HTTP forms, page rendering, and process-local review state.
- `templates/` contains the display-only frontend.

Production modules remain directly under `src/`; there is no service, repository, database,
provider-abstraction, agent, or LangGraph layer.

## Guardrails

- Category, subcategory, application, and expected Metric values must exist in `metrics.md`.
- Returned names match case-insensitively and normalize to exact source spelling.
- Call 2 preserves the Call 1 questions and leaves final-view and metric fields empty.
- Call 3 preserves the latest base understanding and returns a two-to-six-label flow.
- Call 4 preserves the complete Call 3 understanding.
- Every workbook metric receives exactly one flat review row.
- Objective and Formula statuses are validated independently against the original workbook values.
- Invalid structured output gets at most one repair call per stage; provider errors bypass repair.
- Failed later stages retain their current process-local state for manual retry.
- API credentials stay in environment variables or `.env.local` and are never returned.
