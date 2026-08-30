# Implementation Plan: Focused Local MVP Boundaries

**Branch**: `001-focused-mvp-boundaries` | **Date**: 2026-08-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-focused-mvp-boundaries/spec.md`

## Summary

Replace directory-based input discovery and combined file I/O with explicit browser uploads and
focused modules. `api.py` converts multipart files to plain filename/bytes values,
`input_reader.py` validates and parses the complete review package before OpenAI is called,
`openai_connection.py` constructs the configured client, `ai_reviewer.py` performs only the three
structured provider calls, `workflow.py` preserves the business gates, and `output_writer.py`
creates one non-overwriting pair of workbooks directly under `Output/`.

## Technical Context

**Language/Version**: Python >=3.11; development environment currently uses Python 3.14.6

**Primary Dependencies**: FastAPI 0.141.1, OpenAI Python SDK 2.54.0, Pydantic 2.13.4,
openpyxl 3.1.5, Jinja2, python-multipart, python-dotenv, PyYAML

**Storage**: Uploaded bytes are transient; unfinished review state is process-local; completed
results are paired `.xlsx` files directly under `Output/`

**Testing**: No automated test files for this migration; Ruff, compilation, imports, dependency
checks, deterministic in-memory fakes, route inspection, and HTTP smoke checks

**Target Platform**: Trusted local Windows machine, loopback HTTP server

**Project Type**: Local single-user FastAPI web application

**Performance Goals**: Reject invalid local files before any provider request and keep file parsing
responsive for ordinary QM text and developer workbooks; provider latency is outside local control

**Constraints**: No database, authentication, temporary application upload copies, per-review
output directories, prompt prose in Python, or secret values in responses/logs/version control

**Scale/Scope**: One active local reviewer, one QM file and one workbook per review, three
structured OpenAI calls, two output workbooks per completed review

## Constitution Check

*GATE: Passed before Phase 0 research and re-checked after Phase 1 design.*

- **Visible flow — PASS**: `api -> workflow -> input/provider/output` remains direct; there is no
  generic service or repository layer.
- **Focused responsibilities — PASS**: The seven requested modules own exactly the boundaries
  defined by the constitution; `schemas.py` remains the shared contract module.
- **Catalog guardrails — PASS**: `input_reader.py` parses the only catalog and `workflow.py`
  validates selected values and expected metrics before output writing.
- **Replaceable connection — PASS**: One `create_openai_client(settings)` function isolates client
  construction; `ai_reviewer.py` receives the client and retains external YAML prompts.
- **Minimal MVP — PASS**: The design adds no database, authentication, adapter hierarchy,
  provider factory, background job, or completed-review registry.
- **Verification — PASS**: Verification uses the established deterministic checks and creates no
  automated test directory or files.

## Project Structure

### Documentation (this feature)

```text
specs/001-focused-mvp-boundaries/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── http.md
└── tasks.md
```

### Source Code (repository root)

```text
main.py
templates/
├── index.html
├── styles.css
└── app.js
src/mrm_review/
├── __init__.py
├── __main__.py
├── cli.py
├── api.py
├── config.py
├── schemas.py
├── input_reader.py
├── output_writer.py
├── openai_connection.py
├── ai_reviewer.py
├── workflow.py
└── prompts/
```

**Structure Decision**: Keep the existing single Python package and single HTML UI. Replace the
mixed `file_io.py` with one input module and one output module, and move client construction out
of `ai_reviewer.py`. HTTP-specific upload objects stay in `api.py`; business modules receive only
Pydantic values and paths. The old `Input/` runtime convention is removed from the review flow.

## Complexity Tracking

There are no constitution violations to justify.
