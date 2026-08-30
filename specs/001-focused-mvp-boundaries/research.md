# Research: Focused Local MVP Boundaries

## Browser upload boundary

**Decision**: Present two required file controls. `api.py` reads multipart parts and converts each
one to `UploadedFileData(filename, content)`. `input_reader.read_review_package()` receives lists
for both fields, enforces exactly one of each, and returns parsed source text, catalog, and developer
metrics before `workflow.py` calls the reviewer.

**Rationale**: The selected files are explicit and all deterministic validation completes before
the first paid provider call. Plain values keep FastAPI types out of business and file modules.

**Alternatives rejected**:

- Continue scanning `Input/`: stale or unintended files can be selected.
- Persist uploads into `Input/`: creates unnecessary lifecycle and cleanup behavior.
- Pass `UploadFile` into workflow: couples business logic to HTTP and stream lifetime.
- Bind only singular FastAPI upload parameters: duplicate form parts can bypass the business
  cardinality rule and missing parts produce framework JSON rather than the page error state.

## Input parsing and validation

**Decision**: `input_reader.py` owns filename, content, workbook, header, row, and catalog parsing.
The QM file is decoded as UTF-8 with optional BOM. The workbook is opened from `BytesIO` and is
never copied to an application temp path. The Metric name is the record boundary, so rows without
one are ignored because existing workbooks use them for thresholds, continuation text, and blank
placeholders. An empty `Any other(s)` row is also a template placeholder rather than a reviewable
Metric. Other named Metrics may keep blank Objective/Formula cells for later independent
assessment, and Metric names and catalog values are rejected when duplicated case-insensitively.

**Rationale**: One public `read_review_package()` function creates a deep, reliable boundary and
makes the pre-provider validation order obvious.

**Alternatives rejected**:

- Several public single-file reader calls in workflow: permits partial validation and makes the
  call order easier to misuse.
- Deduplicate catalog or workbook rows silently: hides invalid business input.
- Add a fixed worksheet name: the current accepted contract is the active sheet and required
  headers; no name was specified.

**Accepted limitation**: Starlette may spool large multipart parts to the operating-system temp
directory internally. The app creates no upload copy and closes received parts after reading.

## OpenAI connection boundary

**Decision**: `config.py` reads `OPENAI_API_KEY` and `OPENAI_MODEL` from the environment or
`.env.local`. `openai_connection.py` exposes one concrete function,
`create_openai_client(settings) -> OpenAI`. `api.py` composes settings, client, and
`OpenAIReviewer`; `ai_reviewer.py` contains no environment or authentication logic.

**Rationale**: A future supported token callback or workload identity change is localized to
configuration and client construction. The OpenAI SDK already accepts callable API keys, so no
custom wrapper is needed.

**Alternatives rejected**:

- Connection wrapper class, provider factory, or authentication strategy hierarchy: speculative
  abstractions with one provider and one current authentication mechanism.
- Build the client inside `OpenAIReviewer`: mixes connection lifecycle with review operations.
- Build settings eagerly when a reviewer fake is supplied: breaks deterministic local checks that
  intentionally do not need credentials.

## Provider failure ownership

**Decision**: Provider exceptions remain provider exceptions through `ai_reviewer.py` and
`workflow.py`. `api.py` maps authentication, access/model, credit, rate-limit, connection, and
timeout failures to short actionable messages for all three provider stages. Raw provider bodies,
credentials, and exception strings are not rendered.

**Rationale**: The HTTP boundary knows how to communicate with the reviewer; inner modules retain
simple logic and do not depend on UI wording.

**Alternatives rejected**:

- Catch and reword exceptions in every reviewer method: repeated code and mixed responsibilities.
- Show `str(error)`: can expose internal or sensitive provider details.

## Output pair creation

**Decision**: `output_writer.write_review_outputs()` creates both workbooks from one call and gives
them one UUID4 hexadecimal identifier:

```text
Output/mrm_review_<id>.xlsx
Output/missing_metrics_<id>.xlsx
```

Workbook bytes are built before final files are opened. Final paths use exclusive creation so an
existing result is never overwritten. If the second write fails, only the first file from that
attempt is removed. Workbook columns and values remain unchanged.

**Rationale**: The pair cannot accidentally receive unrelated identifiers and old output files
remain intact. UUID naming avoids timestamp collisions without requiring state.

**Alternatives rejected**:

- Fixed filenames: overwrite earlier reviews.
- Timestamp-only names: can collide at the chosen clock resolution.
- Per-review folders: explicitly rejected by the user.
- Database, manifest, storage adapter, or `latest` aliases: unnecessary for the local MVP.

**Accepted limitation**: Two filesystem files cannot be committed atomically. Handled write
failures are cleaned up, but a hard process or machine failure between writes can leave one orphan.

## Download and completed state

**Decision**: Keep `GET /download/{name}`. Accept only the two generated filename patterns, require
a basename-only name, resolve the path directly under `Output/`, and require an existing file.
The result page uses the names returned by `output_writer.py`. Completed reviews are represented by
their retained files; no completed-state dictionary is added.

**Rationale**: Known download links keep working after a process restart while path traversal and
unrelated file downloads remain blocked.

## Local execution model

**Decision**: Keep synchronous workbook and OpenAI work in the existing local single-user request
flow and keep only unfinished draft/refined states in process memory.

**Rationale**: Background queues, concurrency infrastructure, session persistence, and retention
jobs solve problems outside the approved scope.
