# MRM Model Review Architecture

## Purpose

This repository contains one local FastAPI MVP for use-case understanding and monitoring-metric review.

## Runtime Flow

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

Call 2 runs only when at least one non-blank, non-skipped answer exists. Call 3 is reachable only
from the review state shown with the button labelled exactly `OK`. No result file is created.

## Data Contract

`LLMInput` always contains five keys:

- `system_main_info`: exact decoded QM text
- `global_metrics`: exact full Markdown catalog
- `system_metrics`: flat three-column workbook rows
- `system_extra_info`: answered question/answer pairs only
- `previous_output`: null for Call 1, otherwise the latest `LLMOutput`

All three calls return the complete `LLMOutput`. Later-stage fields remain empty until their stage.
The raw catalog string is sent to OpenAI. A separate minimal parser creates an internal dictionary
only for case-insensitive validation and source-spelling normalization.

## Module Boundaries

- `config.py` reads local runtime configuration.
- `schemas.py` defines provider and upload contracts.
- `user_input_reader.py` reads the selected QM file and workbook.
- `metric_catalog_reader.py` reads raw catalog text and parses its validation view.
- `openai_connection.py` constructs the OpenAI client.
- `prompt_loader.py` loads versioned YAML instructions.
- `ai_reviewer.py` sends three structured requests using the same contracts.
- `workflow.py` sequences calls and applies catalog and metric guardrails.
- `api.py` owns HTTP forms and process-local review state.
- `templates/` contains the display-only frontend.

Production modules remain directly under `src/`; there is no service, repository, database, or
provider-abstraction layer.

## Guardrails

- Category, subcategory, application, and expected Metric values must exist in `metrics.md`.
- Returned names match case-insensitively and normalize to exact source spelling.
- Every workbook metric receives exactly one flat review row.
- Objective and Formula statuses are validated independently against the original workbook values.
- Invalid structured output gets at most one repair call; provider errors bypass repair.
- Failed later stages retain their current process-local state for manual retry.
- API credentials stay in environment variables or `.env.local` and are never returned.
