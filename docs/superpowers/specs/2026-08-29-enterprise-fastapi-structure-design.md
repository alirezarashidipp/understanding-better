# Enterprise FastAPI Structure Design

## Goal

Restructure the MRM Model Review POC into a professional source-layout Python package named `mrm_review`, move prompts into version-controlled prompt modules, and replace Flask with FastAPI while keeping the current business behavior.

## Decisions

- Rename `input_extractor` to `mrm_review`.
- Remove the unused raw-extraction CLI, its JSON output, and the existing test suite.
- Use FastAPI, Jinja2 templates, StaticFiles, Form handling, and Uvicorn.
- Keep one application package without domain/application/infrastructure layering.
- Keep runtime state in memory; do not add authentication or a database.
- Keep the existing `Input/`, `Output/`, and `metrics/` contracts.
- Do not create automated tests in this migration, per explicit user instruction.

## Package Structure

- `main.py`: root ASGI entry point exposing `app` and starting Uvicorn when executed.
- `src/mrm_review/__main__.py`: enables `python -m mrm_review`.
- `src/mrm_review/cli.py`: parses `--host`, `--port`, and `--reload`, then starts Uvicorn.
- `src/mrm_review/api.py`: FastAPI application factory, routes, templates, downloads, and in-memory review state.
- `src/mrm_review/config.py`: project paths and `.env.local` OpenAI settings.
- `src/mrm_review/schemas.py`: all Pydantic input, workflow, and output contracts.
- `src/mrm_review/file_io.py`: deterministic TXT, Markdown, and XLSX input/output.
- `src/mrm_review/ai_reviewer.py`: OpenAI Responses API integration.
- `src/mrm_review/workflow.py`: explicit start-review and finish-review orchestration.
- `src/mrm_review/prompts/`: static, reviewable, version-controlled prompt constants.
- `src/mrm_review/templates/` and `static/`: one HTML template and one CSS file.

## Prompt as Code

`prompts/use_case.py` owns the use-case and clarification prompt. `prompts/metric_review.py` owns the metric selection and independent field-validation prompt. Prompts contain explicit outcome constraints, while output shape remains enforced by Pydantic schemas rather than duplicated JSON instructions.

## Dependency Management

`requirements.txt` is the runtime dependency source. `requirements-dev.txt` includes the runtime file and development tooling. `pyproject.toml` reads runtime dependencies dynamically from `requirements.txt` and retains package/build metadata plus tool configuration, preventing two independently maintained dependency lists.

## Execution

- `python main.py`
- `python -m mrm_review`
- `uvicorn main:app --host 127.0.0.1 --port 8000`

## Verification

No automated tests are added or retained in this migration. Verification consists of dependency installation, package import, configuration construction without exposing secrets, Python compilation, route inspection, dependency consistency, and an HTTP smoke test of the start page. No live OpenAI request is made without real input files.
