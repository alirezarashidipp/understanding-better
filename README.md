# MRM Model Review

A local, single-user FastAPI MVP for understanding use cases and reviewing Metrics from an MRM perspective.

## Simple structure

```text
QM-*.txt + MRM_*.xlsx + metrics/metrics.md
                    ↓
                 LLMInput
                    ↓
       Call 1 → optional Call 2 → Call 3 → OK → Call 4
                    ↓
                 LLMOutput
                    ↓
                  Browser
```

The main modules live directly under `src/`:

- `user_input_reader.py`: reads the TXT file and the three workbook columns
- `metric_catalog_reader.py`: reads the raw `metrics.md` text and performs minimal parsing for validation
- `schemas.py`: defines `LLMInput`, `LLMOutput`, and their row models
- `ai_reviewer.py`: creates the OpenAI client and owns the four calls that share one schema
- `workflow.py`: uses three `langchain-core` Runnables to coordinate four calls and validation
- `api.py`: owns the routes and temporary in-process state
- `views.py`: renders HTML responses and converts exceptions into safe public errors
- `templates/`: contains the minimal application page and frontend assets

The prompts for the four calls are stored in four YAML files under `prompts/`; provider prompt text is not written inside Python code.
See `docs/architecture.md` for the runtime flow and file boundaries.

## Inputs

- Exactly one `QM-*.txt` file
- Exactly one `MRM_*.xlsx` file
- The fixed catalog at `metrics/metrics.md`
- `OPENAI_API_KEY`, `OPENAI_MODEL`, and `OPENAI_TEMPERATURE` configured in the environment or `.env.local`

The TXT content is placed unchanged in `system_main_info`. The complete Markdown catalog is placed in
`global_metrics` without reconstruction. Each workbook row in `system_metrics` contains only these three keys:

| Monitoring Metric | Test Objective | Calculation Method/Formula |
|---|---|---|

The legacy column names `Metric`, `Calcution Method/Formula`, and `Calculation Method / Formula` are also
accepted when reading the workbook, but JSON always uses the canonical names shown above.

## Review flow

1. Call 1 receives the exact source information, complete catalog, and workbook Metrics. It returns an initial understanding, a confidence score, and zero to four questions.
2. The reviewer may answer or skip each question. Call 2 is skipped when no non-blank answer exists.
3. Call 3 always receives the latest understanding and creates the final product explanation and flow from an MRM perspective.
4. The Call 3 result is shown in the browser. Only a button labelled exactly `OK` starts Call 4.
5. Call 4 independently assesses each workbook Objective and Formula and proposes additional catalog Metrics.

All four calls use the same `LLMInput` and `LLMOutput` models. Fields owned by later stages remain empty
until their stage runs. An invalid structured result receives at most one repair attempt. Provider authentication,
billing, rate-limit, and connection errors are never repaired automatically.

## Installation and startup

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe main.py
```

Then open `http://127.0.0.1:8000`. API documentation is available at `/api/docs`, and the health check is at `/health`.

## Output

The complete result is displayed only in the browser. The application does not create Excel or JSON output files.

## Intentional MVP limitations

- No authentication or database
- Temporary in-process state
- No multi-agent flow or PDF input
- No automated test suite in the current migration, by project decision
