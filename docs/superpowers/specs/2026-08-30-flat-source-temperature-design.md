# Flat Source and OpenAI Temperature Design

## Goal

Remove the redundant `src/mrm_review/` package directory, keep focused Python modules directly
under `src/`, move provider YAML files to root `prompts/`, and configure one validated OpenAI
temperature for all three structured calls.

## Structure

```text
src/
├── api.py
├── workflow.py
├── input_reader.py
├── output_writer.py
├── openai_connection.py
├── ai_reviewer.py
├── config.py
├── schemas.py
├── prompt_loader.py
└── cli.py
prompts/
├── use_case.yml
├── use_case_refinement.yml
└── metric_review.yml
```

There is no compatibility package or pass-through wrapper. All internal imports use the flat
module names. `main.py` imports `api` and `cli`, while the console command points to `cli:main`.

## Prompt loading

`prompt_loader.py` resolves the repository-root `prompts/` directory relative to its own file.
YAML validation stays unchanged: each file must contain non-empty `version` and `instructions`
fields. Provider prompt prose remains outside Python.

## Temperature

`config.py` reads optional `OPENAI_TEMPERATURE`; omission means `0.0`. The value must parse as a
float from `0.0` through `2.0`. `api.py` passes the validated value to `OpenAIReviewer`, which sends
it explicitly in each of the three `responses.parse` calls. `.env.example` documents the setting.

## Packaging and execution

Setuptools declares the ten flat modules under `src/`. Supported execution paths are
`python main.py`, `uvicorn main:app`, and the installed `mrm-review` command. The removed
`python -m mrm_review` command is not preserved because the package no longer exists.

## Verification

No automated test files are added. Verification uses Ruff, compilation, editable reinstall,
dependency checking, flat-module import checks, prompt loading, config boundary checks, a fake
OpenAI client that captures all three temperatures, deterministic HTTP flow, and live health.
