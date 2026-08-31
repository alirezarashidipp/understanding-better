from collections.abc import Callable
from pathlib import Path
from typing import Protocol, TypeVar

from metric_catalog_reader import parse_global_metrics, read_global_metrics
from schemas import ExtraInfo, LLMInput, LLMOutput, UploadedFileData
from user_input_reader import read_user_inputs


class AIReviewer(Protocol):
    def call_1(self, data: LLMInput, *, repair_feedback: str = "") -> LLMOutput: ...

    def call_2(self, data: LLMInput, *, repair_feedback: str = "") -> LLMOutput: ...

    def call_3(self, data: LLMInput, *, repair_feedback: str = "") -> LLMOutput: ...


ReviewState = tuple[LLMInput, LLMOutput]
ReviewResult = TypeVar("ReviewResult")


class AIReviewValidationError(ValueError):
    pass


def start_review(
    catalog_path: Path,
    reviewer: AIReviewer,
    *,
    qm_files: list[UploadedFileData],
    workbook_files: list[UploadedFileData],
) -> ReviewState:
    system_main_info, system_metrics = read_user_inputs(qm_files, workbook_files)
    data = LLMInput(
        system_main_info=system_main_info,
        global_metrics=read_global_metrics(catalog_path),
        system_metrics=system_metrics,
        system_extra_info=[],
        previous_output=None,
    )
    result = _call_with_one_repair(
        lambda feedback: reviewer.call_1(data, repair_feedback=feedback),
        lambda output: _validate_output(data, output, stage=1),
    )
    return data, result


def continue_review(
    data: LLMInput,
    previous_output: LLMOutput,
    answers: list[ExtraInfo],
    reviewer: AIReviewer,
) -> ReviewState:
    next_input = data.model_copy(
        update={"system_extra_info": answers, "previous_output": previous_output}
    )
    if not answers:
        return next_input, previous_output

    result = _call_with_one_repair(
        lambda feedback: reviewer.call_2(next_input, repair_feedback=feedback),
        lambda output: _validate_output(next_input, output, stage=2),
    )
    return next_input, result


def finish_review(
    data: LLMInput,
    previous_output: LLMOutput,
    reviewer: AIReviewer,
) -> LLMOutput:
    final_input = data.model_copy(update={"previous_output": previous_output})
    return _call_with_one_repair(
        lambda feedback: reviewer.call_3(final_input, repair_feedback=feedback),
        lambda output: _validate_output(final_input, output, stage=3),
    )


def _validate_output(data: LLMInput, output: LLMOutput, stage: int) -> None:
    catalog = parse_global_metrics(data.global_metrics)
    category = _canonical_key(catalog, output.main_category, "Category")
    sections = catalog[category]
    output.main_category = category
    output.subcategory = _canonical_value(
        sections["Main Subcategories"], output.subcategory, "Subcategory"
    )
    output.closest_application = _canonical_value(
        sections["Exmaples"], output.closest_application, "Application"
    )

    required_text = (
        output.business_use_case,
        output.main_category,
        output.subcategory,
        output.closest_application,
        output.input,
        output.processing,
        output.output,
    )
    if any(not value.strip() for value in required_text):
        raise ValueError("The system understanding fields must not be empty.")
    if output.understanding_confidence is None:
        raise ValueError("The result requires understanding_confidence.")

    if stage == 1:
        if output.mrm_explanation or output.flow or output.expected_metrics or output.metric_reviews:
            raise ValueError("Call 1 fields for later stages must be empty.")
        return

    if data.previous_output is None:
        raise ValueError("Later calls require previous_output.")
    if output.questions != data.previous_output.questions:
        raise ValueError("Later calls must preserve the Call 1 questions.")
    if stage == 2:
        if not output.mrm_explanation or not 2 <= len(output.flow) <= 6:
            raise ValueError("The final understanding requires an explanation and 2-6 flow labels.")
        if output.expected_metrics or output.metric_reviews:
            raise ValueError("Call 2 metric fields must be empty.")
        return

    preserved_fields = (
        "business_use_case",
        "system_type",
        "main_category",
        "subcategory",
        "closest_application",
        "components",
        "input",
        "processing",
        "output",
        "understanding_confidence",
        "questions",
        "mrm_explanation",
        "flow",
    )
    if any(
        getattr(output, field) != getattr(data.previous_output, field)
        for field in preserved_fields
    ):
        raise ValueError("Call 3 must preserve the latest system understanding.")
    _validate_metric_results(data, sections["Metrics"], output)


def _validate_metric_results(
    data: LLMInput,
    approved_metrics: list[str],
    output: LLMOutput,
) -> None:
    expected_names = []
    for metric in output.expected_metrics:
        metric.name = _canonical_value(approved_metrics, metric.name, "Metric")
        expected_names.append(metric.name.casefold())
    if len(expected_names) != len(set(expected_names)):
        raise ValueError("Expected metrics must not contain duplicates.")

    system_by_name = {metric.monitoring_metric.casefold(): metric for metric in data.system_metrics}
    review_names = [row.metric.casefold() for row in output.metric_reviews]
    if set(review_names) != set(system_by_name) or len(review_names) != len(set(review_names)):
        raise ValueError("Metric review rows must cover every system metric exactly once.")

    for row in output.metric_reviews:
        system_metric = system_by_name[row.metric.casefold()]
        row.metric = system_metric.monitoring_metric
        _validate_empty_status(
            system_metric.test_objective,
            row.objective_status,
            "Test Objective",
            row.metric,
        )
        _validate_empty_status(
            system_metric.calculation_method,
            row.formula_status,
            "Calculation Method / Formula",
            row.metric,
        )


def _canonical_key(values: dict[str, object], returned: str, label: str) -> str:
    match = next((name for name in values if name.casefold() == returned.casefold()), None)
    if match is None:
        raise ValueError(f"{label} '{returned}' is not present in metrics.md.")
    return match


def _canonical_value(values: list[str], returned: str, label: str) -> str:
    match = next((value for value in values if value.casefold() == returned.casefold()), None)
    if match is None:
        raise ValueError(f"{label} '{returned}' is not present in metrics.md.")
    return match


def _validate_empty_status(value: str, status: str, field: str, metric: str) -> None:
    if not value and status != "IT IS EMPTY":
        raise ValueError(f"Empty {field} for '{metric}' must be marked IT IS EMPTY.")
    if value and status == "IT IS EMPTY":
        raise ValueError(f"Non-empty {field} for '{metric}' cannot be marked IT IS EMPTY.")


def _call_with_one_repair(
    call: Callable[[str], ReviewResult],
    validate: Callable[[ReviewResult], object],
) -> ReviewResult:
    try:
        result = call("")
        validate(result)
        return result
    except ValueError as error:
        feedback = str(error).strip()[:2000] or "The previous structured output was invalid."

    try:
        repaired_result = call(feedback)
        validate(repaired_result)
        return repaired_result
    except ValueError as error:
        raise AIReviewValidationError(
            "OpenAI returned an invalid structured result after one repair attempt. "
            "Please retry this step."
        ) from error
