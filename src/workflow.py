from collections.abc import Callable, Sequence

from langchain_core.runnables import Runnable, RunnableLambda
from pydantic import ValidationError

from ai_reviewer import OpenAIReviewer
from metric_catalog_reader import SECTIONS, Catalog
from schemas import LLMInput, LLMOutput, MetricReview, SystemMetric


def build_workflows(
    reviewer: OpenAIReviewer,
    catalog: Catalog,
) -> tuple[Runnable, Runnable, Runnable]:
    return (
        RunnableLambda(lambda data: _call(reviewer.call_1, data, catalog, 1)),
        RunnableLambda(lambda data: _refine(reviewer, catalog, data)),
        RunnableLambda(lambda data: _call(reviewer.call_4, data, catalog, 4)),
    )


def _refine(
    reviewer: OpenAIReviewer,
    catalog: Catalog,
    data: LLMInput,
) -> LLMOutput:
    previous = data.previous_output
    if previous is None:
        raise ValueError("The previous review result is required for refinement.")

    latest = previous
    if data.system_extra_info:
        latest = _call(reviewer.call_2, data, catalog, 2)

    call_3_input = data.model_copy(update={"previous_output": latest})
    return _call(reviewer.call_3, call_3_input, catalog, 3)


def _call(
    call: Callable[..., LLMOutput],
    data: LLMInput,
    catalog: Catalog,
    call_number: int,
) -> LLMOutput:
    if call_number != 1 and data.previous_output is None:
        raise ValueError(f"Call {call_number} requires the previous output.")

    try:
        output = call(data)
        _validate(output, data, catalog, call_number)
    except (ValidationError, ValueError) as error:
        output = call(data, repair_feedback=" ".join(str(error).split())[:500])
        _validate(output, data, catalog, call_number)
    return output


def _validate(
    output: LLMOutput,
    data: LLMInput,
    catalog: Catalog,
    call_number: int,
) -> None:
    previous = data.previous_output
    text_values = (
        output.business_use_case,
        output.input,
        output.processing,
        output.output,
        *output.components,
        *output.questions,
    )
    if not output.components or any(not value.strip() for value in text_values):
        raise ValueError("The AI returned a blank understanding field.")
    if output.understanding_confidence is None or isinstance(output.understanding_confidence, bool):
        raise ValueError("understanding_confidence is required.")

    output.main_category = _canonical(output.main_category, list(catalog), "main category")
    category = catalog[output.main_category]
    output.subcategory = _canonical(
        output.subcategory,
        category[SECTIONS["subcategories"]],
        "subcategory",
    )
    output.closest_application = _canonical(
        output.closest_application,
        category[SECTIONS["examples"]],
        "closest application",
    )

    if call_number in (1, 2):
        if (
            output.mrm_explanation
            or output.flow
            or output.expected_metrics
            or output.metric_reviews
        ):
            raise ValueError(f"Call {call_number} filled fields owned by a later call.")
        if call_number == 2 and previous and output.questions != previous.questions:
            raise ValueError("Call 2 changed the original clarification questions.")
        return

    if previous is None:
        raise ValueError(f"Call {call_number} requires the previous output.")

    if call_number == 3:
        _require_same_except(
            output,
            previous,
            {"mrm_explanation", "flow"},
            call_number,
        )
        if not output.mrm_explanation.strip():
            raise ValueError("Call 3 must return the final MRM explanation.")
        if not 2 <= len(output.flow) <= 6 or any(not value.strip() for value in output.flow):
            raise ValueError("Call 3 flow must contain two to six non-blank labels.")
        return

    _require_same_except(
        output,
        previous,
        {"expected_metrics", "metric_reviews"},
        call_number,
    )
    allowed_metrics = category[SECTIONS["metrics"]]
    for metric in output.expected_metrics:
        metric.name = _canonical(metric.name, allowed_metrics, "expected Metric")
    output.metric_reviews = _validate_reviews(output.metric_reviews, data.system_metrics)


def _canonical(value: str, allowed: Sequence[str], label: str) -> str:
    normalized = value.strip().casefold()
    match = next((item for item in allowed if item.casefold() == normalized), None)
    if match is None:
        raise ValueError(f"AI returned {label} '{value}' outside the approved catalog.")
    return match


def _require_same_except(
    output: LLMOutput,
    previous: LLMOutput,
    excluded: set[str],
    call_number: int,
) -> None:
    current_values = output.model_dump(exclude=excluded)
    previous_values = previous.model_dump(exclude=excluded)
    if current_values != previous_values:
        raise ValueError(f"Call {call_number} changed protected fields.")


def _validate_reviews(
    reviews: list[MetricReview],
    metrics: list[SystemMetric],
) -> list[MetricReview]:
    expected = {metric.monitoring_metric.strip().casefold(): metric for metric in metrics}
    received = {review.metric.strip().casefold(): review for review in reviews}
    if len(received) != len(reviews) or received.keys() != expected.keys():
        raise ValueError("Call 4 must return exactly one review for every workbook Metric.")

    for key, metric in expected.items():
        review = received[key]
        review.metric = metric.monitoring_metric
        _validate_field(
            "Test Objective",
            review.objective_status,
            review.objective_reason,
            review.objective_revised,
            metric.test_objective,
            review.metric,
        )
        _validate_field(
            "Calculation Method / Formula",
            review.formula_status,
            review.formula_reason,
            review.formula_revised,
            metric.calculation_method,
            review.metric,
        )
    return [received[key] for key in expected]


def _validate_field(
    label: str,
    status: str,
    reason: str,
    revised: str,
    original: str,
    metric: str,
) -> None:
    if (status == "IT IS EMPTY") != (not original.strip()):
        raise ValueError(f"{label} status does not match workbook Metric '{metric}'.")
    if status == "NEEDS REVISION" and not reason.strip():
        raise ValueError(f"NEEDS REVISION for {label} '{metric}' requires a reason.")
    if status in ("NEEDS REVISION", "IT IS EMPTY") and not revised.strip():
        raise ValueError(f"{status} for {label} '{metric}' requires corrected text.")
    if status == "OK" and revised.strip():
        raise ValueError(f"OK for {label} '{metric}' must not include revised text.")
