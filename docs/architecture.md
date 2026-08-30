# MRM Model Review Architecture

## Purpose

This repository contains one local FastAPI application that helps an MRM reviewer understand a model use case and review monitoring metrics.

## Runtime Flow

```text
selected QM-*.txt + selected MRM_*.xlsx
                    |
                    v
     input_reader.py + metrics/metrics.md
                    |
                    v
        initial use case + optional questions
                    |
                  Next
                    |
                    v
       refined MRM explanation + business flow
                    |
                   OK
                    |
                    v
   selected-category metrics -> metric review
                    |
                    v
 output_writer.py -> two paired Output/*.xlsx files
```

## Module Boundaries

Production Python modules live directly under root `src/`. Provider prompts live under root
`prompts/`; there is no additional application package directory.

- `config.py` reads and validates local runtime configuration.
- `schemas.py` defines all data exchanged between modules and OpenAI.
- `input_reader.py` reads and validates the selected QM file, workbook, and approved catalog.
- `output_writer.py` creates and stores the paired Excel outputs without overwriting old reviews.
- `openai_connection.py` constructs the OpenAI client and owns authentication wiring.
- `prompt_loader.py` validates and loads versioned YAML instructions from root `prompts/`.
- `ai_reviewer.py` sends the three structured requests to the OpenAI Responses API.
- `workflow.py` makes the application data flow explicit and enforces metric guardrails.
- `api.py` converts HTTP forms into workflow calls and renders the result.
- Root `templates/` contains the HTML page, stylesheet, and JavaScript.
- `cli.py` and root `main.py` provide the standard execution paths.

## Guardrails

- Category, subcategory, application, and Metric names come only from `metrics/metrics.md`.
- A selected subcategory and application must belong to the selected category.
- AI-expected Metric names must belong to the selected category.
- An invalid structured result receives at most one repair call with validation feedback;
  provider connection and billing failures are never automatically retried by this loop.
- Catalog and developer names are matched case-insensitively and normalized to their source
  spelling before display or output.
- Original developer Objective and Formula values remain server-owned and are joined into the
  workbook by `output_writer.py`; OpenAI does not echo them in structured output.
- Metric outputs are not written until the reviewer selects `OK` after seeing the refined understanding.
- Every developer metric must receive exactly one independent Test Objective and Formula assessment.
- Original developer values cannot be changed before validation.
- The API key is represented as `SecretStr` and is never returned by an endpoint.
- Only generated `mrm_review_<id>.xlsx` and `missing_metrics_<id>.xlsx` files directly under
  `Output/` can be downloaded.
- Review state is process-local and intentionally non-durable for this local MVP.
- Failed refinement and metric-review requests retain that process-local state and re-render the
  current stage for manual retry.
