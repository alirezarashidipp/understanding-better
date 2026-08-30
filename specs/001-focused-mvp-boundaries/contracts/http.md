# HTTP Contract: Focused Local MVP

## `GET /`

Renders the start page with one required QM file control and one required workbook control.

## `POST /start`

Content type: `multipart/form-data`

| Field | Cardinality | Rules |
|---|---:|---|
| `qm_file` | exactly 1 | Basename matches `QM-*.txt`; non-empty UTF-8/UTF-8-SIG text |
| `workbook_file` | exactly 1 | Basename matches `MRM_*.xlsx`; readable workbook with required columns |

Success renders the `questions` stage with the validated initial understanding,
`understanding_confidence`, and zero to four questions. Invalid input renders the page error state
and performs no provider request or output write.

## `POST /refine`

Content type: `application/x-www-form-urlencoded`

Receives `review_id` and, for every displayed question, its answer and/or Skip control. Success
renders the refined explanation and flow. This stage does not write workbooks.

## `POST /review`

Content type: `application/x-www-form-urlencoded`

Receives `review_id` only from the button labelled exactly `OK`. Success performs metric review,
writes the unique output pair, removes the refined process state, and renders direct download links
for the generated names.

## `GET /download/{name}`

Accepted basename forms:

```regex
^(?:mrm_review|missing_metrics)_[0-9a-f]{32}\.xlsx$
```

The resolved file must exist directly under `Output/`. Invalid, missing, nested, or unrelated names
return HTTP 404. Successful responses use the XLSX media type and original generated filename.

## `GET /health`

Returns:

```json
{"status": "ok"}
```

## Provider failure responses

Provider failures render the page error state without a raw provider body or credential:

- invalid authentication: check the local API credential;
- access or model denial: check configured model/project access;
- exhausted credits: add credits or use a funded project key;
- temporary rate limit: retry shortly;
- timeout or connection failure: check connection and retry;
- other provider status failure: provider request failed and may be retried.
