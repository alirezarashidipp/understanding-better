from typing import Protocol

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
    ) -> UseCaseDraft: ...

    def refine_use_case(
        self,
        pending: PendingReview,
        answers: list[ClarificationAnswer],
    ) -> RefinedUseCase: ...

    def review_metrics(
        self,
        ready: ReadyForMetricReview,
        eligible_metrics: list[MetricCatalogItem],
    ) -> MetricReviewResult: ...


def start_review(
    paths: ReviewPaths,
    reviewer: AIReviewer,
    *,
    qm_files: list[UploadedFileData],
    workbook_files: list[UploadedFileData],
) -> PendingReview:
    package = read_review_package(qm_files, workbook_files, paths.metric_catalog_file)
    draft = reviewer.create_draft(package.source_text, package.catalog)
    _selected_category(package.catalog, draft.use_case.catalog_selection)

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
    refined = reviewer.refine_use_case(pending, answers)
    _selected_category(pending.catalog, refined.use_case.catalog_selection)
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
    result = reviewer.review_metrics(ready, category.metrics)
    _validate_metrics(pending, category.metrics, result)

    developer_names = {metric.name.casefold() for metric in pending.developer_metrics}
    missing_metrics = [
        metric
        for metric in result.expected_metrics
        if metric.name.casefold() not in developer_names
    ]
    outputs = write_review_outputs(
        output_dir=pending.paths.output_dir,
        metric_reviews=result.metric_reviews,
        missing_metrics=missing_metrics,
    )
    return CompletedReview(result=result, outputs=outputs)


def _selected_category(
    catalog: list[MetricCategory],
    selection: CatalogSelection,
) -> MetricCategory:
    category = next(
        (item for item in catalog if item.name == selection.main_category),
        None,
    )
    if category is None:
        raise ValueError(f"Category '{selection.main_category}' is not present in metrics.md.")
    if selection.subcategory not in category.subcategories:
        raise ValueError(
            f"Subcategory '{selection.subcategory}' does not belong to "
            f"'{category.name}' in metrics.md."
        )
    if selection.closest_application not in category.applications:
        raise ValueError(
            f"Application '{selection.closest_application}' does not belong to "
            f"'{category.name}' in metrics.md."
        )
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
    allowed_names = {metric.name.casefold() for metric in eligible_metrics}
    developer_by_name = {metric.name.casefold(): metric for metric in pending.developer_metrics}

    for metric in result.expected_metrics:
        if metric.name.casefold() not in allowed_names:
            raise ValueError(
                f"Metric '{metric.name}' is not approved for the selected metrics.md category."
            )

    review_names = [row.metric.casefold() for row in result.metric_reviews]
    if set(review_names) != set(developer_by_name) or len(review_names) != len(set(review_names)):
        raise ValueError("Metric review rows must cover every developer metric exactly once.")

    for row in result.metric_reviews:
        developer_metric = developer_by_name[row.metric.casefold()]
        if row.developer_test_objective != developer_metric.test_objective:
            raise ValueError(f"Test Objective changed for '{row.metric}'.")
        if row.developer_calculation_method != developer_metric.calculation_method:
            raise ValueError(f"Calculation Method changed for '{row.metric}'.")
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
