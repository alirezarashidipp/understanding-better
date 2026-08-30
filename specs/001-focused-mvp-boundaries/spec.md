# Feature Specification: Focused Local MVP Boundaries

**Feature Branch**: Not created; Git extension is disabled

**Created**: 2026-08-30

**Status**: Ready for planning

**Input**: Turn the existing proof of concept into a focused local MVP. A reviewer uploads one
QM text file and one developer workbook from the page. Input reading, output creation, and the
OpenAI connection must be independently changeable without adding unnecessary architectural
layers.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Upload a Review Package (Priority: P1)

An MRM reviewer selects exactly one approved QM text file and one developer workbook from the
page and starts a review without manually copying files into an input directory.

**Why this priority**: The review cannot begin reliably until the intended files are explicit and
validated at the user boundary.

**Independent Test**: Select one valid QM file and one valid workbook and confirm that the initial
understanding is shown. Repeat with an invalid or missing file and confirm that the review stops
before any external review request or output creation.

**Acceptance Scenarios**:

1. **Given** one valid `QM-*.txt` and one valid `MRM_*.xlsx`, **When** the reviewer starts the
   review, **Then** the application reads only those two uploaded files and shows the initial
   understanding and confidence.
2. **Given** a missing, incorrectly named, empty, unreadable, or structurally invalid file,
   **When** the reviewer starts the review, **Then** the application identifies the invalid input
   and performs no external review request and writes no output workbook.

---

### User Story 2 - Complete the Existing Gated Review (Priority: P2)

The reviewer answers or skips any material clarification questions, selects `Next`, reviews the
refined MRM explanation and flow, and selects exactly `OK` before metric assessment begins.

**Why this priority**: The current approval gate is a core business control and must survive the
MVP restructuring.

**Independent Test**: Complete a valid review with zero questions, with answered questions, and
with all questions skipped; in every case confirm that metric review begins only after `OK`.

**Acceptance Scenarios**:

1. **Given** a valid initial understanding, **When** the reviewer selects `Next`, **Then** the
   refined explanation and business/risk flow are shown even when no answer was supplied.
2. **Given** a refined explanation, **When** the reviewer has not selected `OK`, **Then** no metric
   assessment or output workbook exists.
3. **Given** a refined explanation, **When** the reviewer selects `OK`, **Then** every developer
   Metric receives independent Objective and Formula assessments.

---

### User Story 3 - Retain Distinct Review Outputs (Priority: P3)

After each completed review, the reviewer can download two output workbooks and earlier review
outputs remain available in the shared output directory.

**Why this priority**: A usable MVP must not silently destroy a previous review result.

**Independent Test**: Complete two reviews and confirm that four files exist directly under the
output directory, with each review's two files sharing an identifier and no earlier file changed.

**Acceptance Scenarios**:

1. **Given** a completed review, **When** outputs are created, **Then** one review workbook and one
   missing-metrics workbook are stored directly under the output directory with a shared unique
   identifier.
2. **Given** outputs from an earlier review, **When** another review completes, **Then** the earlier
   files remain unchanged and no per-review subdirectory is created.

---

### User Story 4 - Change the Provider Connection Safely (Priority: P4)

A maintainer can change the supported OpenAI authentication or client-construction mechanism
without changing review rules, prompts, input handling, or output handling.

**Why this priority**: Connection details change for operational reasons and must not create risk
in the MRM business workflow.

**Independent Test**: Substitute a valid alternative connection configuration and confirm that
the same three structured review operations can run without changes to business rules or files.

**Acceptance Scenarios**:

1. **Given** a supported connection configuration, **When** its authentication mechanism changes,
   **Then** input validation, review sequencing, prompts, and output behavior remain unchanged.
2. **Given** an authentication, quota, access, or transient rate-limit failure, **When** a review
   request is attempted, **Then** the reviewer receives a specific actionable message and no
   secret value is displayed or logged.

### Edge Cases

- The reviewer selects more or fewer than two required files.
- A file has an approved extension but the required filename prefix is missing.
- The QM file is empty or cannot be decoded as text.
- The workbook is corrupt, empty, has the wrong active sheet, or lacks required columns.
- The workbook contains blank placeholder rows or duplicate Metric names.
- The approved catalog is missing, malformed, or contains duplicate values.
- The external provider rejects credentials, has exhausted credits, denies model access, or
  temporarily rate-limits requests.
- Two reviews finish within the same timestamp resolution and would otherwise receive the same
  output name.
- The local process restarts during an unfinished review; unfinished in-memory state is lost and
  the reviewer starts again.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow a local reviewer to select exactly one `QM-*.txt` file and
  exactly one `MRM_*.xlsx` file from the review page.
- **FR-002**: The system MUST validate filenames, readable content, workbook structure, required
  headers, and duplicate Metric names before an external review request, and MUST ignore workbook
  rows that have no Metric name and empty `Any other(s)` placeholder rows.
- **FR-003**: The system MUST read use-case content only from the selected QM file and developer
  Metrics only from the selected workbook.
- **FR-004**: The system MUST treat `metrics/metrics.md` as the only approved catalog and reject
  category, subcategory, application, or expected Metric values outside it.
- **FR-005**: The system MUST preserve the existing initial understanding, zero-to-four material
  clarification questions with Skip, `Next`, refined explanation and flow, and exact `OK` gate.
- **FR-006**: The system MUST validate all external structured results before using them in the
  workflow or writing files.
- **FR-007**: The system MUST assess Test Objective and Calculation Method / Formula independently
  for every developer Metric using only the approved field statuses and question limits.
- **FR-008**: The system MUST write only absent required Metrics to the missing-metrics workbook.
- **FR-009**: Each completed review MUST create two uniquely paired workbook names directly under
  `Output/` without overwriting or modifying earlier results.
- **FR-010**: Input reading, output creation, provider connection, provider review operations,
  business sequencing, data contracts, and HTTP handling MUST remain independently changeable.
- **FR-011**: A supported provider authentication change MUST require no change to review rules,
  prompts, input handling, or output handling.
- **FR-012**: Provider failures MUST produce a specific user-facing message while preventing
  secrets and raw credentials from appearing in responses or logs.
- **FR-013**: The MVP MUST remain local and single-user with process-local unfinished state and
  MUST NOT require a database or user authentication.
- **FR-014**: Existing validated review behavior and catalog guardrails MUST remain unchanged
  unless explicitly modified by this specification.
- **FR-015**: The system MUST load one OpenAI temperature from local configuration, validate it
  from `0.0` through `2.0`, default it to `0.0`, and apply it to all three structured calls.

### Key Entities

- **Review Package**: The selected QM source file, developer workbook, and approved catalog used
  for one review.
- **Review Session**: The temporary initial and refined review state identified for one browser
  flow; unfinished state lasts only for the running process.
- **Output Pair**: The review workbook and missing-metrics workbook created by the same completed
  review and linked by one unique identifier.
- **Provider Connection**: Runtime credentials and client settings required to perform structured
  review operations without containing business rules.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A reviewer can select the two required files and reach the initial understanding in
  one browser flow without manually editing an input directory.
- **SC-002**: All invalid review packages in the documented edge cases are rejected before an
  external review request or output creation.
- **SC-003**: In every review scenario, metric assessment starts only after the refined explanation
  is shown and the reviewer selects `OK`.
- **SC-004**: Two consecutive completed reviews produce four distinct workbook files, with zero
  overwritten earlier outputs and no per-review directories.
- **SC-005**: Every developer Metric appears exactly once in the review output with two independent
  field assessments.
- **SC-006**: A supported connection-mechanism change can be completed without modifying input,
  output, prompt, or business-rule behavior.
- **SC-007**: No API key or token appears in page responses, application logs, output workbooks, or
  version-controlled files during the complete review flow.
- **SC-008**: A maintainer can trace the main flow from selected inputs to downloads through a
  small set of clearly owned responsibilities without encountering pass-through layers.
- **SC-009**: All three OpenAI calls receive the same validated configured temperature.

## Assumptions

- The MVP runs on one trusted local machine for one reviewer at a time.
- Exactly one QM file describes exactly one use case per review.
- The developer workbook uses its active sheet and the documented current or legacy headers.
- Completed output files are retained until the local user removes them manually.
- Existing prompt YAML files, schemas, catalog rules, and the three-stage review flow remain the
  behavioral baseline.
- Provider latency is external to the local file-selection experience.
- Automated test files remain out of scope; deterministic verification commands and smoke
  scenarios provide acceptance evidence for this migration.
