# Input Extraction POC Design

## Goal

Extract raw information from approved TXT and XLSX files without AI analysis and preserve a precise source reference for every extracted value.

## Accepted Inputs

- TXT files whose names start with `QM-`
- XLSX files whose names start with `MRM_`
- Files are discovered recursively under `Input/`

All other files are listed in `skipped_files` with a reason.

## Extraction Rules

- Each non-empty TXT line becomes one record. Its source contains the file name and one-based line number.
- Each non-empty XLSX cell becomes one record. Its source contains the file name, sheet name, and cell coordinate.
- No OpenAI API or other AI model is called.
- Input values are not summarized, classified, corrected, or judged.

## Output

The command writes `Output/extracted_data.json`. Pydantic validates the output structure before it is written. Each record contains `value` and `source`; unused source fields are `null`.

## Error Handling

An unreadable accepted file is reported in `errors`. Processing continues for the remaining files. A missing `Input/` directory is a command error; an empty directory produces a valid empty JSON result.

## Project Shape

Production code lives in `src/input_extractor/`, tests in `tests/`, input files in `Input/`, and generated output in `Output/`. The project includes `README.md`, `AGENTS.md`, `.gitignore`, and `pyproject.toml`.

## Verification

Automated tests cover discovery, TXT line references, Excel sheet/cell references, skipped files, and JSON generation. A local smoke test runs the command against sample input created by the tests.
