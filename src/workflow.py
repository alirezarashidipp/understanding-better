from collections.abc import Callable

from langchain_core.runnables import Runnable, RunnableLambda
from pydantic import ValidationError

from ai_reviewer import OpenAIReviewer
from metric_catalog_reader import SECTIONS, Catalog
from schemas import LLMInput, LLMOutput, MetricReview, SystemMetric

ReviewerCall = Callable[..., LLMOutput]
Validator = Callable[[LLMOutput], LLMOutput]

BASE_FIELDS = (
    "business_use_case",
    "main_category",
    "subcategory",
    "closest_application",
    "components",
    "input",
    "processing",
    "output",
    "understanding_confidence",
    "questions",
)


def build_workflows(
    reviewer: OpenAIReviewer,
    catalog: Catalog,
) -> tuple[
    Runnable[LLMInput, LLMOutput],
    Runnable[LLMInput, LLMOutput],
    Runnable[LLMInput, LLMOutput],
]:
    start_workflow = RunnableLambda(
        lambda data: _call_with_one_repair(
            reviewer.call_1,
            data,
            lambda output: _validate_call_1(output, catalog),
        )
    )
    refine_workflow = RunnableLambda(lambda data: _run_refinement(reviewer, catalog, data))
    review_workflow = RunnableLambda(
        lambda data: _call_with_one_repair(
            reviewer.call_4,
            data,
            lambda output: _validate_call_4(output, data, catalog),
        )
    )
    return start_workflow, refine_workflow, review_workflow


def _run_refinement(
    reviewer: OpenAIReviewer,
    catalog: Catalog,
    data: LLMInput,
) -> LLMOutput:
    previous = _require_previous_output(data)

    if data.system_extra_info:
        latest = _call_with_one_repair(
            reviewer.call_2,
            data,
            lambda output: _validate_call_2(output, previous, catalog),
        )
    else:
        latest = previous

    explanation_input = data.model_copy(update={"previous_output": latest})
    return _call_with_one_repair(
        reviewer.call_3,
        explanation_input,
        lambda output: _validate_call_3(output, latest, catalog),
    )


def _call_with_one_repair(
    call: ReviewerCall,
    data: LLMInput,
    validate: Validator,
) -> LLMOutput:
    try:
        return validate(call(data))
    except (ValidationError, ValueError) as error:
        feedback = " ".join(str(error).split())[:500]
        return validate(call(data, repair_feedback=feedback))


def _validate_call_1(output: LLMOutput, catalog: Catalog) -> LLMOutput:
    _validate_understanding(output, catalog)
    _require_empty_later_fields(output, allow_explanation=False)
    return output


def _validate_call_2(
    output: LLMOutput,
    previous: LLMOutput,
    catalog: Catalog,
) -> LLMOutput:
    _validate_understanding(output, catalog)
    if output.questions != previous.questions:
        raise ValueError("Call 2 must preserve the original clarification questions.")
    _require_empty_later_fields(output, allow_explanation=False)
    return output


def _validate_call_3(
    output: LLMOutput,
    previous: LLMOutput,
    catalog: Catalog,
) -> LLMOutput:
    _validate_understanding(output, catalog)
    _require_preserved_fields(output, previous, BASE_FIELDS, "Call 3")

    if not output.mrm_explanation.strip():
        raise ValueError("Call 3 must return the final MRM explanation.")
    if not 2 <= len(output.flow) <= 6 or any(not node.strip() for node in output.flow):
        raise ValueError("Call 3 flow must contain two to six non-blank labels.")
    if output.expected_metrics or output.metric_reviews:
        raise ValueError("Call 3 must leave metric review fields empty.")
    return output


def _validate_call_4(
    output: LLMOutput,
    data: LLMInput,
    catalog: Catalog,
) -> LLMOutput:
    previous = _require_previous_output(data)
    _validate_understanding(output, catalog)
    _require_preserved_fields(
        output,
        previous,
        (*BASE_FIELDS, "mrm_explanation", "flow"),
        "Call 4",
    )

    category_metrics = catalog[output.main_category][SECTIONS["metrics"]]
    for metric in output.expected_metrics:
        metric.name = _canonical_value(metric.name, category_metrics, "expected Metric")

    output.metric_reviews = _validate_metric_reviews(output.metric_reviews, data.system_metrics)
    return output


def _validate_understanding(output: LLMOutput, catalog: Catalog) -> None:
    text_fields = (
        "business_use_case",
        "main_category",
        "subcategory",
        "closest_application",
        "input",
        "processing",
        "output",
    )
    for field in text_fields:
        if not getattr(output, field).strip():
            raise ValueError(f"{field} must not be blank.")

    if output.understanding_confidence is None or isinstance(output.understanding_confidence, bool):
        raise ValueError("understanding_confidence must be an integer from 0 to 100.")
    if not output.components or any(not component.strip() for component in output.components):
        raise ValueError("components must contain at least one non-blank value.")
    if any(not question.strip() for question in output.questions):
        raise ValueError("Clarification questions must not be blank.")

    output.main_category = _canonical_value(
        output.main_category,
        list(catalog),
        "main category",
    )
    sections = catalog[output.main_category]
    output.subcategory = _canonical_value(
        output.subcategory,
        sections[SECTIONS["subcategories"]],
        "subcategory",
    )
    output.closest_application = _canonical_value(
        output.closest_application,
        sections[SECTIONS["examples"]],
        "closest application",
    )


def _canonical_value(value: str, allowed: list[str], label: str) -> str:
    normalized = value.strip().casefold()
    for candidate in allowed:
        if candidate.casefold() == normalized:
            return candidate
    raise ValueError(f"AI returned {label} '{value}' outside the approved catalog.")


def _require_empty_later_fields(output: LLMOutput, *, allow_explanation: bool) -> None:
    if not allow_explanation and output.mrm_explanation:
        raise ValueError("This call must leave mrm_explanation empty.")
    if output.flow or output.expected_metrics or output.metric_reviews:
        raise ValueError("This call filled fields owned by a later stage.")


def _require_previous_output(data: LLMInput) -> LLMOutput:
    if data.previous_output is None:
        raise ValueError("The previous review result is required for this stage.")
    return data.previous_output


def _require_preserved_fields(
    output: LLMOutput,
    previous: LLMOutput,
    fields: tuple[str, ...],
    call_name: str,
) -> None:
    changed = [field for field in fields if getattr(output, field) != getattr(previous, field)]
    if changed:
        raise ValueError(f"{call_name} changed protected fields: {', '.join(changed)}.")


def _validate_metric_reviews(
    reviews: list[MetricReview],
    developer_metrics: list[SystemMetric],
) -> list[MetricReview]:
    developer_by_name = {
        metric.monitoring_metric.strip().casefold(): metric for metric in developer_metrics
    }
    review_by_name: dict[str, MetricReview] = {}

    for review in reviews:
        key = review.metric.strip().casefold()
        if key in review_by_name:
            raise ValueError(f"Call 4 returned duplicate review for Metric '{review.metric}'.")
        developer_metric = developer_by_name.get(key)
        if developer_metric is None:
            raise ValueError(f"Call 4 reviewed unknown Metric '{review.metric}'.")

        review.metric = developer_metric.monitoring_metric
        _validate_field_review(
            review.objective_status,
            review.objective_reason,
            review.objective_revised,
            developer_metric.test_objective,
            "Test Objective",
            review.metric,
        )
        _validate_field_review(
            review.formula_status,
            review.formula_reason,
            review.formula_revised,
            developer_metric.calculation_method,
            "Calculation Method / Formula",
            review.metric,
        )
        review_by_name[key] = review

    missing = [
        metric.monitoring_metric
        for metric in developer_metrics
        if metric.monitoring_metric.strip().casefold() not in review_by_name
    ]
    if missing:
        raise ValueError(f"Call 4 did not review Metrics: {', '.join(missing)}.")

    return [
        review_by_name[metric.monitoring_metric.strip().casefold()] for metric in developer_metrics
    ]


def _validate_field_review(
    status: str,
    reason: str,
    revised: str,
    developer_value: str,
    field_name: str,
    metric_name: str,
) -> None:
    is_empty = not developer_value.strip()
    if is_empty and status != "IT IS EMPTY":
        raise ValueError(f"{field_name} for '{metric_name}' is empty in the workbook.")
    if not is_empty and status == "IT IS EMPTY":
        raise ValueError(f"{field_name} for '{metric_name}' is not empty in the workbook.")

    if status == "NEEDS REVISION" and (not reason.strip() or not revised.strip()):
        raise ValueError(
            f"NEEDS REVISION for {field_name} '{metric_name}' requires a reason and correction."
        )
    if status == "IT IS EMPTY" and not revised.strip():
        raise ValueError(f"IT IS EMPTY for {field_name} '{metric_name}' requires proposed text.")
    if status == "OK" and revised.strip():
        raise ValueError(f"OK for {field_name} '{metric_name}' must not include revised text.")
