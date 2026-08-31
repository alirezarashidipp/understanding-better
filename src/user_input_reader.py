import re
from collections.abc import Sequence
from io import BytesIO
from pathlib import Path

import yaml
from openpyxl import load_workbook

from schemas import SystemMetric, UploadedFileData

FORMAT = yaml.safe_load(
    (Path(__file__).resolve().parent.parent / "input_format.yml").read_text(encoding="utf-8")
)["user_inputs"]
QM_FILENAME = re.compile(FORMAT["qm_filename"])
WORKBOOK_FILENAME = re.compile(FORMAT["workbook_filename"])
COLUMNS = FORMAT["workbook_columns"]
EMPTY_METRICS = {value.casefold() for value in FORMAT["empty_metric_placeholders"]}


def read_user_inputs(
    qm_files: Sequence[UploadedFileData],
    workbook_files: Sequence[UploadedFileData],
) -> tuple[str, list[SystemMetric]]:
    qm_file = _only_file(qm_files, "QM text file")
    workbook_file = _only_file(workbook_files, "developer workbook")
    return _read_qm(qm_file), _read_workbook(workbook_file)


def _only_file(files: Sequence[UploadedFileData], label: str) -> UploadedFileData:
    if len(files) != 1:
        raise ValueError(f"Select exactly one {label}.")
    return files[0]


def _read_qm(upload: UploadedFileData) -> str:
    _validate_filename(upload.filename, QM_FILENAME, "QM-*.txt")
    if not upload.content:
        raise ValueError("The QM text file is empty.")
    try:
        content = upload.content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValueError("The QM text file must use UTF-8 encoding.") from None
    if not content.strip():
        raise ValueError("The QM text file contains no readable text.")
    return content


def _read_workbook(upload: UploadedFileData) -> list[SystemMetric]:
    _validate_filename(upload.filename, WORKBOOK_FILENAME, "MRM_*.xlsx")
    if not upload.content:
        raise ValueError("The developer workbook is empty.")
    try:
        workbook = load_workbook(BytesIO(upload.content), read_only=True, data_only=False)
    except Exception:
        raise ValueError("The developer workbook could not be read as XLSX.") from None

    try:
        rows = workbook.active.iter_rows(values_only=True)
        headers = next(rows, None)
        if headers is None:
            raise ValueError("The developer workbook is empty.")
        header_names = [str(value).strip() if value is not None else "" for value in headers]
        positions = {
            field: _column_position(header_names, aliases, field)
            for field, aliases in COLUMNS.items()
        }

        metrics = []
        names = set()
        for row in rows:
            name = _cell(row, positions["monitoring_metric"])
            objective = _cell(row, positions["test_objective"])
            calculation = _cell(row, positions["calculation_method"])
            normalized_name = name.casefold()

            if not name or (normalized_name in EMPTY_METRICS and not objective and not calculation):
                continue
            if normalized_name in names:
                raise ValueError(f"Developer workbook contains duplicate Metric '{name}'.")
            names.add(normalized_name)
            metrics.append(
                SystemMetric(
                    monitoring_metric=name,
                    test_objective=objective,
                    calculation_method=calculation,
                )
            )

        if not metrics:
            raise ValueError("The developer workbook contains no Metric rows.")
        return metrics
    finally:
        workbook.close()


def _validate_filename(filename: str, pattern: re.Pattern[str], expected: str) -> None:
    if Path(filename).name != filename or pattern.fullmatch(filename) is None:
        raise ValueError(f"Select a file named {expected}.")


def _column_position(headers: list[str], aliases: list[str], field: str) -> int:
    positions = [index for index, header in enumerate(headers) if header in aliases]
    if not positions:
        raise ValueError(f"Developer workbook is missing the {field} column.")
    if len(positions) > 1:
        raise ValueError(f"Developer workbook has more than one {field} column.")
    return positions[0]


def _cell(row: tuple[object, ...], position: int) -> str:
    if position >= len(row) or row[position] is None:
        return ""
    value = str(row[position]).strip()
    return "" if value == '""' else value
