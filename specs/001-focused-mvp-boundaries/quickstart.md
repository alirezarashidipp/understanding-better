# Quickstart: Focused Local MVP Verification

## Start the application

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe main.py
```

Set `OPENAI_API_KEY`, `OPENAI_MODEL`, and optionally `OPENAI_TEMPERATURE` in the process
environment or local ignored `.env.local`. Temperature defaults to `0.0` and accepts values from
`0.0` through `2.0`. Open `http://127.0.0.1:8000`.

## Happy-path smoke scenario

1. Select one non-empty file named `QM-*.txt` in the QM control.
2. Select one readable file named `MRM_*.xlsx` in the workbook control.
3. Start the review and confirm the initial understanding and integer confidence are visible.
4. Answer or Skip each question and select `Next`.
5. Confirm the refined MRM explanation and flow are visible before metric review.
6. Select exactly `OK`.
7. Download both generated workbooks.
8. Complete a second review and confirm `Output/` now contains four distinct `.xlsx` files directly
   under the directory. Each pair must share its 32-character identifier and the first pair must be
   unchanged.
9. With a fake reviewer, return one invalid result followed by a valid result at each provider
   stage. Confirm exactly two calls, non-empty repair feedback on the second call, canonical source
   spelling, and original developer Objective/Formula values in the generated workbook.
10. Make both automatic attempts fail during refinement and metric review. Confirm the same stage
    is rendered with its existing `review_id`, then retry manually without uploading files again.

## Invalid-input smoke scenario

Try a missing file, incorrect prefix, empty QM file, corrupt workbook, missing required header, and
duplicate Metric. Each attempt must render a specific input error before a provider request and
must create no output.

## Deterministic verification

Run without creating test files:

```powershell
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\python.exe -m compileall -q main.py src
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -c "from main import app; print([(r.path, sorted(getattr(r, 'methods', []) or [])) for r in app.routes])"
```

Use an in-memory fake reviewer and FastAPI HTTP client for route and upload checks so provider
credits are not consumed. Separately use one real happy-path review only when credential and model
access verification is required.

## Expected source boundaries

```text
config.py             -> environment and settings
openai_connection.py  -> OpenAI client and authentication construction
ai_reviewer.py        -> structured OpenAI calls
input_reader.py       -> review package parsing and validation
output_writer.py      -> paired Excel creation and storage
workflow.py           -> business sequence and guardrails
api.py                -> HTTP, upload transport, UI rendering, provider error messages
```
