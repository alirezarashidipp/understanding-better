# Data Model: Focused Local MVP Boundaries

## UploadedFileData

Transient value created by the HTTP boundary.

| Field | Type | Rules |
|---|---|---|
| `filename` | string | Basename only; validated against its required QM or workbook pattern |
| `content` | bytes | Must be non-empty; not retained after parsing |

## ReviewPackage

Complete deterministic input returned by `input_reader.py` before any provider request.

| Field | Type | Rules |
|---|---|---|
| `source_text` | string | Includes `SOURCE FILE: <name>` and decoded non-empty QM content |
| `catalog` | list of `MetricCategory` | Parsed only from `metrics/metrics.md`; no duplicate values |
| `developer_metrics` | list of `DeveloperMetric` | Non-empty and unique by case-insensitive Metric name |

## ReviewPaths

Stable local paths derived from the project root.

| Field | Type | Rules |
|---|---|---|
| `metric_catalog_file` | `Path` | Exactly `metrics/metrics.md` under the configured root |
| `output_dir` | `Path` | Shared flat `Output/` directory |

It does not contain `Input/` or fixed output filenames.

## PendingReview

Process-local state after a validated package and initial provider draft.

| Field | Type |
|---|---|
| `paths` | `ReviewPaths` |
| `source_text` | string |
| `catalog` | list of `MetricCategory` |
| `developer_metrics` | list of `DeveloperMetric` |
| `draft` | validated `UseCaseDraft` |

## ReadyForMetricReview

Process-local state after `Next` and refinement.

| Field | Type |
|---|---|
| `pending` | `PendingReview` |
| `refined` | validated `RefinedUseCase` |

Metric assessment is allowed only from this state after the HTTP `OK` action.

## OutputPair

The two retained files created together by `output_writer.py`.

| Field | Type | Rules |
|---|---|---|
| `output_id` | string | 32 lowercase hexadecimal UUID4 characters |
| `review_file` | `Path` | `Output/mrm_review_<output_id>.xlsx` |
| `missing_metrics_file` | `Path` | `Output/missing_metrics_<output_id>.xlsx` |

## CompletedReview

Return value of `workflow.finish_review()`.

| Field | Type |
|---|---|
| `result` | validated `MetricReviewResult` |
| `outputs` | `OutputPair` |

No completed review is stored in memory; the output files are the durable result.

## State transitions

```text
uploaded parts
  -> ReviewPackage
  -> PendingReview
  -> ReadyForMetricReview
  -> CompletedReview
```

- Invalid upload or catalog: stop before `PendingReview` and before OpenAI.
- `PendingReview` to `ReadyForMetricReview`: happens on `Next`, including skipped/no questions.
- `ReadyForMetricReview` to `CompletedReview`: happens only on exact `OK` form action.
- Provider or output failure: current unfinished state remains available for a retry in the running
  process.
