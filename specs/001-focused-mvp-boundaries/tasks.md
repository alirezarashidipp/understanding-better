---
description: "Implementation tasks for focused local MVP module boundaries"
---

# Tasks: Focused Local MVP Boundaries

**Input**: Design documents from `specs/001-focused-mvp-boundaries/`

**Tests**: Automated test files are intentionally out of scope. Every story includes a deterministic
verification checkpoint using compile, lint, in-memory fakes, route inspection, or HTTP smoke calls.

## Phase 1: Setup

**Purpose**: Confirm the planned migration fits the existing local project.

- [X] T001 Verify dependencies, ignore rules, and the live source tree against `requirements.txt`, `.gitignore`, and `src/`

---

## Phase 2: Foundational Contracts

**Purpose**: Define the small shared values needed by the input and output seams.

- [X] T002 Add uploaded package, output pair, completed review, and revised path contracts in `src/schemas.py`

**Checkpoint**: Shared Pydantic contracts are importable without adding architectural layers.

---

## Phase 3: User Story 1 - Upload a Review Package (Priority: P1) 🎯 MVP

**Goal**: Read and validate only the QM text and developer workbook selected on the page.

**Independent Test**: A valid in-memory `QM-*.txt` and `MRM_*.xlsx` reaches the initial draft;
missing, misnamed, empty, corrupt, malformed, or duplicate input stops before the fake reviewer is
called.

- [X] T003 [US1] Implement the single review-package parsing boundary in `src/input_reader.py`
- [X] T004 [US1] Change the workflow entry to accept selected upload values in `src/workflow.py`
- [X] T005 [US1] Add the two-file multipart transport and upload cleanup in `src/api.py`
- [X] T006 [US1] Render required QM and workbook file controls in `templates/index.html`
- [X] T007 [US1] Run deterministic valid/invalid upload checks without provider calls or test files against `src/input_reader.py` and `src/api.py`

**Checkpoint**: User Story 1 works without reading review inputs from `Input/`.

---

## Phase 4: User Story 2 - Complete the Existing Gated Review (Priority: P2)

**Goal**: Preserve questions/Skip, `Next`, refined explanation and flow, and exact `OK` gate.

**Independent Test**: A fake reviewer completes zero-question and skipped-question flows and does
not perform metric review before the `OK` submission.

- [X] T008 [US2] Preserve the explicit refinement and metric guardrails around the new boundaries in `src/workflow.py`
- [X] T009 [US2] Run a deterministic fake-reviewer HTTP flow through `/start`, `/refine`, and `/review` without creating test files in `src/api.py`

**Checkpoint**: The established MRM control flow is unchanged.

---

## Phase 5: User Story 3 - Retain Distinct Review Outputs (Priority: P3)

**Goal**: Create and download one uniquely named, non-overwriting output pair per completed review.

**Independent Test**: Two completions create four direct children of a temporary `Output/`, each
pair shares one identifier, and the first pair bytes remain unchanged.

- [X] T010 [US3] Implement paired in-memory workbook creation and exclusive storage in `src/output_writer.py`
- [X] T011 [US3] Return `CompletedReview` with one `OutputPair` from `src/workflow.py`
- [X] T012 [US3] Validate generated download names and render returned links in `src/api.py` and `templates/index.html`
- [X] T013 [US3] Run deterministic two-review output and download checks without creating test files against `src/output_writer.py` and `src/api.py`

**Checkpoint**: Earlier output files remain intact and no review subdirectory exists.

---

## Phase 6: User Story 4 - Change the Provider Connection Safely (Priority: P4)

**Goal**: Isolate configuration/client authentication from structured review operations and show
safe actionable provider errors.

**Independent Test**: Client construction changes are confined to one module, a supplied fake
reviewer requires no environment settings, and representative provider failures render no raw
provider details or credentials.

- [X] T014 [US4] Clarify environment-or-local-file configuration errors in `src/config.py`
- [X] T015 [US4] Add the concrete OpenAI client constructor in `src/openai_connection.py`
- [X] T016 [US4] Remove settings and client construction from `src/ai_reviewer.py`
- [X] T017 [US4] Compose the default reviewer and map safe provider messages for every review stage in `src/api.py`
- [X] T018 [US4] Run deterministic construction and provider-error checks without credentials or test files against `src/openai_connection.py` and `src/api.py`

**Checkpoint**: Authentication construction is independently replaceable without a provider
factory or wrapper.

---

## Phase 7: Polish and Cross-Cutting Verification

**Purpose**: Remove the stale combined seam, align documentation, and verify the integrated MVP.

- [X] T019 Remove the superseded combined module `src/file_io.py` after all imports move
- [X] T020 [P] Update usage and output naming in `README.md`
- [X] T021 [P] Update runtime flow and module ownership in `docs/architecture.md`
- [X] T022 Run Ruff, compilation, import, dependency, route, deterministic harness, and live HTTP smoke checks from `specs/001-focused-mvp-boundaries/quickstart.md`

---

## Dependencies and Execution Order

- Phase 1 precedes all implementation.
- T002 precedes the four user-story phases.
- User Story 1 establishes selected-file input and precedes the end-to-end User Story 2 check.
- User Story 3 depends on the existing `OK`-gated workflow from User Story 2.
- User Story 4 can be implemented after T002, but its final API composition check follows the HTTP
  changes from User Stories 1 and 3.
- T019 follows every import migration. T020 and T021 can proceed in parallel after source behavior
  stabilizes. T022 is last.

## Parallel Opportunities

- T020 and T021 affect separate documentation files and can run in parallel.
- Source tasks are intentionally sequential because this is one small package and several tasks
  touch `workflow.py` or `api.py`; parallel edits would add merge risk without useful speed.

## Implementation Strategy

1. Establish the small shared contracts.
2. Deliver explicit uploads and pre-provider validation as the first usable increment.
3. Reconfirm the established `Next -> refined explanation -> OK` gate.
4. Add unique paired outputs and safe downloads.
5. Isolate the connection and normalize provider failures.
6. Delete the obsolete combined module, update documentation, and run all deterministic checks.

No task adds a database, authentication, repository/service layer, provider factory, background
job, or automated test file.

---

## Phase 8: Flat Source and Temperature

- [X] T023 Move focused production modules directly under `src/` and remove `src/mrm_review/`
- [X] T024 Move provider YAML files to root `prompts/` and create `src/prompt_loader.py`
- [X] T025 Add validated `OPENAI_TEMPERATURE` configuration and pass it to all three calls in `src/config.py`, `src/ai_reviewer.py`, and `src/api.py`
- [X] T026 Update flat-module packaging and execution paths in `pyproject.toml`, `main.py`, and `src/cli.py`
- [X] T027 Align `AGENTS.md`, `README.md`, `docs/architecture.md`, and active Spec Kit artifacts with the flat layout
- [X] T028 Run deterministic verification, restart the server, commit, and push `main`
