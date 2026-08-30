from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class MetricCatalogItem(BaseModel):
    name: str
    guidance: str = ""


class MetricCategory(BaseModel):
    name: str
    subcategories: list[str]
    applications: list[str]
    metrics: list[MetricCatalogItem]


class CatalogSelection(BaseModel):
    main_category: str
    subcategory: str
    closest_application: str


class DeveloperMetric(BaseModel):
    name: str
    test_objective: str = ""
    calculation_method: str = ""


class ExpectedMetric(BaseModel):
    name: str
    applicability_reason: str
    test_objective: str
    calculation_method: str

    @field_validator("test_objective", "calculation_method")
    @classmethod
    def keep_explanation_short(cls, value: str) -> str:
        sentence_count = sum(value.count(mark) for mark in ".?!")
        if sentence_count > 2:
            raise ValueError("Use at most two short sentences.")
        return value


class FieldAssessment(BaseModel):
    status: Literal["OK", "IT IS EMPTY", "NEEDS REVISION"]
    reason: str = ""
    revised: str = ""
    questions: list[str] = Field(default_factory=list, max_length=3)

    @model_validator(mode="after")
    def validate_revision(self) -> "FieldAssessment":
        if self.status == "NEEDS REVISION" and (not self.reason or not self.revised):
            raise ValueError("A revision requires a reason and revised text.")
        if self.status == "IT IS EMPTY" and not self.revised:
            raise ValueError("An empty field requires proposed text.")
        if self.status == "OK" and self.revised:
            raise ValueError("An OK field must not contain revised text.")
        return self


class MetricReview(BaseModel):
    metric: str
    developer_test_objective: str = ""
    developer_calculation_method: str = ""
    test_objective_assessment: FieldAssessment
    calculation_method_assessment: FieldAssessment


SystemType = Literal["RAG", "LLM", "Traditional ML", "Agentic", "Hybrid", "Other"]


class UseCaseSummary(BaseModel):
    business_use_case: str
    system_type: SystemType
    catalog_selection: CatalogSelection
    components: list[str]
    input: str
    processing: str
    output: str


class ClarificationQuestion(BaseModel):
    id: str
    question: str = Field(max_length=200)


class ClarificationAnswer(BaseModel):
    question_id: str
    answer: str = ""
    skipped: bool = False


class UseCaseDraft(BaseModel):
    use_case: UseCaseSummary
    understanding_confidence: int = Field(ge=0, le=100)
    questions: list[ClarificationQuestion] = Field(max_length=4)


class RefinedUseCase(BaseModel):
    use_case: UseCaseSummary
    mrm_explanation: str = Field(max_length=600)
    diagram: list[str] = Field(min_length=2, max_length=6)


class MetricReviewResult(BaseModel):
    expected_metrics: list[ExpectedMetric]
    metric_reviews: list[MetricReview]


class UploadedFileData(BaseModel):
    filename: str
    content: bytes


class ReviewPackage(BaseModel):
    source_text: str
    catalog: list[MetricCategory]
    developer_metrics: list[DeveloperMetric]


class ReviewPaths(BaseModel):
    metric_catalog_file: Path
    output_dir: Path

    @classmethod
    def from_root(cls, root: Path) -> "ReviewPaths":
        return cls(
            metric_catalog_file=root / "metrics" / "metrics.md",
            output_dir=root / "Output",
        )


class PendingReview(BaseModel):
    paths: ReviewPaths
    source_text: str
    catalog: list[MetricCategory]
    developer_metrics: list[DeveloperMetric]
    draft: UseCaseDraft


class ReadyForMetricReview(BaseModel):
    pending: PendingReview
    refined: RefinedUseCase


class OutputPair(BaseModel):
    output_id: str
    review_file: Path
    missing_metrics_file: Path


class CompletedReview(BaseModel):
    result: MetricReviewResult
    outputs: OutputPair
