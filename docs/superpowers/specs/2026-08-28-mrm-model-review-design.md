# MRM Model Review POC Design

## Goal

Build a small local web POC that helps an MRM reviewer understand a model use case, ask only necessary clarification questions, select metrics from an approved catalog, and compare them with developer-provided metrics.

## Inputs

- One or more `Input/QM-*.txt` files contain the model description.
- One `Input/MRM_*.xlsx` file contains developer metrics.
- `metrics/metrics.md` is the only allowed metric catalog.
- `.env.local` provides `OPENAI_API_KEY` and `OPENAI_MODEL`.

The metric catalog uses a level-two Markdown heading for each approved metric, followed by optional guidance text. The developer workbook contains `Monitoring Metric`, `Test Objective`, and `Calcution Method/Formula` columns. The reader also accepts the earlier `Metric` and `Calculation Method / Formula` aliases.

## User Flow

1. The reviewer opens a single local Flask page and selects **Start Review**.
2. Python reads the approved input files. OpenAI returns a structured use-case draft and zero to four necessary clarification questions.
3. The page shows the draft and questions. Every question has an answer field and a Skip option.
4. After submission, OpenAI updates the use case, produces a short MRM-oriented explanation and a simple business/risk diagram, selects only catalog metrics, and compares them with developer metrics.
5. Python validates all metric names against `metrics.md`, creates `Output/missing_metrics.xlsx` and `Output/mrm_review.xlsx`, and displays the result.

## AI Boundaries

OpenAI is used only for interpretation, concise clarification, metric applicability, and qualitative comparison. File discovery, allowed-name filtering, schema validation, catalog enforcement, Excel writing, and output paths are deterministic Python code. The model and key come from `.env.local`; secrets are never shown in the UI or logs. API responses use Pydantic Structured Outputs and are not stored by the application.

## Output Contracts

`missing_metrics.xlsx` contains only applicable catalog metrics absent from the developer workbook. Its columns are:

- Metric
- Why Important / Needed
- Test Objective
- Calculation Method / Formula

`mrm_review.xlsx` contains every developer metric and uses these columns:

- Monitoring Metric
- Test Objective
- Calcution Method/Formula
- Test Objective Validation
- Test Objective Revised
- Test Objective Questions
- Calculation Method / Formula Validation
- Calculation Method / Formula Revised
- Calculation Method / Formula Questions

Each field assessment is `OK`, `IT IS EMPTY`, or `NEEDS REVISION`. A revision includes a short reason, corrected text, and zero to three questions. Proposed test objectives and calculation methods are limited by prompt and Pydantic validation to at most two short sentences.

## Runtime State and Errors

The POC keeps review state in an in-memory dictionary keyed by a random review ID. It has no authentication or database and state is lost on restart. Missing inputs, invalid workbook headers, API failures, and invalid AI metric names produce short user-facing errors without secret or traceback exposure.

## Project Shape

- `src/input_extractor/models.py`: validated domain and output models
- `src/input_extractor/files.py`: deterministic input and Excel operations
- `src/input_extractor/ai_review.py`: two direct OpenAI calls
- `src/input_extractor/review.py`: visible end-to-end workflow
- `src/input_extractor/web.py`: Flask routes and in-memory state
- `src/input_extractor/templates/index.html`: single simple page

## Tests

Tests use temporary TXT, Markdown, and XLSX files plus a fake AI implementation. No test calls the live API. Coverage includes input rules, metric catalog enforcement, developer workbook parsing, question limits, output workbooks, workflow state, and Flask happy/error paths.
