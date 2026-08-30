from io import BytesIO
from pathlib import Path
from uuid import uuid4

from openpyxl import Workbook

from schemas import DeveloperMetric, ExpectedMetric, FieldAssessment, MetricReview, OutputPair


def write_review_outputs(
    *,
    output_dir: Path,
    developer_metrics: list[DeveloperMetric],
    metric_reviews: list[MetricReview],
    missing_metrics: list[ExpectedMetric],
) -> OutputPair:
    review_bytes = _review_workbook_bytes(metric_reviews, developer_metrics)
    missing_bytes = _missing_metrics_workbook_bytes(missing_metrics)
    output_dir.mkdir(parents=True, exist_ok=True)

    for _ in range(10):
        output_id = uuid4().hex
        pair = OutputPair(
            output_id=output_id,
            review_file=output_dir / f"mrm_review_{output_id}.xlsx",
            missing_metrics_file=output_dir / f"missing_metrics_{output_id}.xlsx",
        )
        if _write_pair_exclusively(pair, review_bytes, missing_bytes):
            return pair

    raise RuntimeError("Could not create unique output filenames.")


def _write_pair_exclusively(
    pair: OutputPair,
    review_bytes: bytes,
    missing_bytes: bytes,
) -> bool:
    created: list[Path] = []
    try:
        _write_exclusively(pair.review_file, review_bytes, created)
        _write_exclusively(pair.missing_metrics_file, missing_bytes, created)
        return True
    except FileExistsError:
        _remove_created_files(created)
        return False
    except OSError:
        _remove_created_files(created)
        raise RuntimeError("The review output files could not be saved.") from None


def _write_exclusively(path: Path, content: bytes, created: list[Path]) -> None:
    file = path.open("xb")
    created.append(path)
    with file:
        file.write(content)


def _remove_created_files(paths: list[Path]) -> None:
    for path in paths:
        path.unlink(missing_ok=True)


def _review_workbook_bytes(
    rows: list[MetricReview],
    developer_metrics: list[DeveloperMetric],
) -> bytes:
    developer_by_name = {metric.name.casefold(): metric for metric in developer_metrics}
    values = [
        [
            row.metric,
            developer_by_name[row.metric.casefold()].test_objective,
            developer_by_name[row.metric.casefold()].calculation_method,
            _validation_text(row.test_objective_assessment),
            row.test_objective_assessment.revised,
            _questions_text(row.test_objective_assessment.questions),
            _validation_text(row.calculation_method_assessment),
            row.calculation_method_assessment.revised,
            _questions_text(row.calculation_method_assessment.questions),
        ]
        for row in rows
    ]
    return _workbook_bytes(
        [
            "Monitoring Metric",
            "Test Objective",
            "Calculation Method/Formula",
            "Test Objective Validation",
            "Test Objective Revised",
            "Test Objective Questions",
            "Calculation Method / Formula Validation",
            "Calculation Method / Formula Revised",
            "Calculation Method / Formula Questions",
        ],
        values,
    )


def _missing_metrics_workbook_bytes(metrics: list[ExpectedMetric]) -> bytes:
    rows = [
        [
            metric.name,
            metric.applicability_reason,
            metric.test_objective,
            metric.calculation_method,
        ]
        for metric in metrics
    ]
    return _workbook_bytes(
        [
            "Metric",
            "Why Important / Needed",
            "Test Objective",
            "Calculation Method / Formula",
        ],
        rows,
    )


def _workbook_bytes(headers: list[str], rows: list[list[object]]) -> bytes:
    workbook = Workbook()
    try:
        sheet = workbook.active
        sheet.title = "MRM Review"
        sheet.append(headers)
        for row in rows:
            sheet.append(row)
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions

        stream = BytesIO()
        workbook.save(stream)
        return stream.getvalue()
    finally:
        workbook.close()


def _validation_text(assessment: FieldAssessment) -> str:
    if assessment.status == "NEEDS REVISION":
        return f"NEEDS REVISION: {assessment.reason}"
    return assessment.status


def _questions_text(questions: list[str]) -> str:
    return "\n".join(f"{number}. {question}" for number, question in enumerate(questions, start=1))
