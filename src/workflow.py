from collections.abc import Callable
from typing import Protocol, TypeVar

from input_reader import read_review_package
from output_writer import write_review_outputs
from schemas import (
    CatalogSelection,
    ClarificationAnswer,
    CompletedReview,
    MetricCatalogItem,
    MetricCategory,
    MetricReviewResult,
    PendingReview,
    ReadyForMetricReview,
    RefinedUseCase,
    ReviewPaths,
    UploadedFileData,
    UseCaseDraft,
)


class AIReviewer(Protocol):
    def create_draft(
        self,
        source_text: str,
        catalog: list[MetricCategory],
        *,
        repair_feedback: str = "",
    ) -> UseCaseDraft: ...

    def refine_use_case(
        self,
        pending: PendingReview,
        answers: list[ClarificationAnswer],
        *,
        repair_feedback: str = "",
    ) -> RefinedUseCase: ...

    def review_metrics(
        self,
        ready: ReadyForMetricReview,
        eligible_metrics: list[MetricCatalogItem],
        *,
        repair_feedback: str = "",
    ) -> MetricReviewResult: ...


ReviewResult = TypeVar("ReviewResult")


class AIReviewValidationError(ValueError):
    pass


def start_review(
    paths: ReviewPaths,
    reviewer: AIReviewer,
    *,
    qm_files: list[UploadedFileData],
    workbook_files: list[UploadedFileData],
) -> PendingReview:
    package = read_review_package(qm_files, workbook_files, paths.metric_catalog_file)
    draft = _call_with_one_repair(
        lambda feedback: reviewer.create_draft(
            package.source_text,
            package.catalog,
            repair_feedback=feedback,
        ),
        lambda result: _selected_category(package.catalog, result.use_case.catalog_selection),
    )

    return PendingReview(
        paths=paths,
        source_text=package.source_text,
        catalog=package.catalog,
        developer_metrics=package.developer_metrics,
        draft=draft,
    )


def refine_review(
    pending: PendingReview,
    answers: list[ClarificationAnswer],
    reviewer: AIReviewer,
) -> ReadyForMetricReview:
    _validate_answers(pending, answers)
    refined = _call_with_one_repair(
        lambda feedback: reviewer.refine_use_case(
            pending,
            answers,
            repair_feedback=feedback,
        ),
        lambda result: _selected_category(pending.catalog, result.use_case.catalog_selection),
    )
    return ReadyForMetricReview(pending=pending, refined=refined)


def finish_review(
    ready: ReadyForMetricReview,
    reviewer: AIReviewer,
) -> CompletedReview:
    pending = ready.pending
    category = _selected_category(
        pending.catalog,
        ready.refined.use_case.catalog_selection,
    )
    result = _call_with_one_repair(
        lambda feedback: reviewer.review_metrics(
            ready,
            category.metrics,
            repair_feedback=feedback,
        ),
        lambda review: _validate_metrics(pending, category.metrics, review),
    )

    developer_names = {metric.name.casefold() for metric in pending.developer_metrics}
    missing_metrics = [
        metric
        for metric in result.expected_metrics
        if metric.name.casefold() not in developer_names
    ]
    outputs = write_review_outputs(
        output_dir=pending.paths.output_dir,
        developer_metrics=pending.developer_metrics,
        metric_reviews=result.metric_reviews,
        missing_metrics=missing_metrics,
    )
    return CompletedReview(result=result, outputs=outputs)


def _selected_category(
    catalog: list[MetricCategory],
    selection: CatalogSelection,
) -> MetricCategory:
    category = next(
        (item for item in catalog if item.name.casefold() == selection.main_category.casefold()),
        None,
    )
    if category is None:
        raise ValueError(f"Category '{selection.main_category}' is not present in metrics.md.")
    subcategory = next(
        (
            item
            for item in category.subcategories
            if item.casefold() == selection.subcategory.casefold()
        ),
        None,
    )
    if subcategory is None:
        raise ValueError(
            f"Subcategory '{selection.subcategory}' does not belong to "
            f"'{category.name}' in metrics.md."
        )
    application = next(
        (
            item
            for item in category.applications
            if item.casefold() == selection.closest_application.casefold()
        ),
        None,
    )
    if application is None:
        raise ValueError(
            f"Application '{selection.closest_application}' does not belong to "
            f"'{category.name}' in metrics.md."
        )
    selection.main_category = category.name
    selection.subcategory = subcategory
    selection.closest_application = application
    return category


def _validate_answers(
    pending: PendingReview,
    answers: list[ClarificationAnswer],
) -> None:
    question_ids = {question.id for question in pending.draft.questions}
    answer_ids = [answer.question_id for answer in answers]
    if set(answer_ids) != question_ids or len(answer_ids) != len(set(answer_ids)):
        raise ValueError("Answers must cover every clarification question exactly once.")


def _validate_metrics(
    pending: PendingReview,
    eligible_metrics: list[MetricCatalogItem],
    result: MetricReviewResult,
) -> None:
    allowed_by_name = {metric.name.casefold(): metric for metric in eligible_metrics}
    developer_by_name = {metric.name.casefold(): metric for metric in pending.developer_metrics}

    for metric in result.expected_metrics:
        approved_metric = allowed_by_name.get(metric.name.casefold())
        if approved_metric is None:
            raise ValueError(
                f"Metric '{metric.name}' is not approved for the selected metrics.md category."
            )
        metric.name = approved_metric.name

    review_names = [row.metric.casefold() for row in result.metric_reviews]
    if set(review_names) != set(developer_by_name) or len(review_names) != len(set(review_names)):
        raise ValueError("Metric review rows must cover every developer metric exactly once.")

    for row in result.metric_reviews:
        developer_metric = developer_by_name[row.metric.casefold()]
        row.metric = developer_metric.name
        _validate_empty_status(
            developer_metric.test_objective,
            row.test_objective_assessment.status,
            "Test Objective",
            row.metric,
        )
        _validate_empty_status(
            developer_metric.calculation_method,
            row.calculation_method_assessment.status,
            "Calculation Method / Formula",
            row.metric,
        )


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
