# Input Extraction POC Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a small Python command that extracts raw TXT lines and XLSX cells into validated JSON with precise source references.

**Architecture:** A direct command discovers files, routes accepted names to two focused extractor functions, validates records with Pydantic, and writes one JSON file. The data flow stays explicit and does not call OpenAI.

**Tech Stack:** Python 3.11+, Pydantic 2, openpyxl, pytest

**Spec:** `docs/superpowers/specs/2026-08-28-input-extraction-design.md`

## Global Constraints

- Accept only `QM-*.txt` and `MRM_*.xlsx`.
- Discover files recursively under `Input/`.
- Never analyze or modify extracted content.
- Keep exact TXT line and XLSX sheet/cell references.
- Continue after individual file-reading errors and record them.

---

### Task 1: Extraction models and functions

**Files:**
- Create: `src/input_extractor/__init__.py`
- Create: `src/input_extractor/models.py`
- Create: `src/input_extractor/extractors.py`
- Test: `tests/test_extractors.py`

**Interfaces:**
- Produces: `extract_txt(path: Path) -> list[ExtractedRecord]`
- Produces: `extract_xlsx(path: Path) -> list[ExtractedRecord]`

- [ ] Write tests proving non-empty TXT lines retain one-based line numbers and non-empty XLSX cells retain sheet names and coordinates.
- [ ] Run `pytest tests/test_extractors.py -v` and confirm failure because production modules do not exist.
- [ ] Implement Pydantic source/record models and the two direct extraction functions.
- [ ] Run `pytest tests/test_extractors.py -v` and confirm all tests pass.

### Task 2: Discovery and JSON command

**Files:**
- Create: `src/input_extractor/main.py`
- Test: `tests/test_main.py`

**Interfaces:**
- Consumes: `extract_txt` and `extract_xlsx`
- Produces: `run_extraction(input_dir: Path, output_file: Path) -> ExtractionResult`

- [ ] Write tests proving recursive discovery, prefix filtering, skipped-file reporting, recoverable read errors, and validated JSON writing.
- [ ] Run `pytest tests/test_main.py -v` and confirm failure because the command module does not exist.
- [ ] Implement the linear discovery, routing, error collection, validation, and JSON writing flow.
- [ ] Run `pytest tests/test_main.py -v` and confirm all tests pass.

### Task 3: Project usage and full verification

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `AGENTS.md`
- Create: `.gitignore`
- Create: `Input/.gitkeep`
- Create: `Output/.gitkeep`

**Interfaces:**
- Produces: `python -m input_extractor.main` after editable installation

- [ ] Document setup, accepted filenames, command usage, JSON schema example, and the fact that `.env.local` and OpenAI are unused.
- [ ] Document project-specific agent constraints and source-integrity requirements.
- [ ] Run `pytest -v` and confirm the full suite passes.
- [ ] Run the CLI against an empty `Input/` directory and validate the generated JSON.
