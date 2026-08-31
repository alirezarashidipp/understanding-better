from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


Status = Literal["OK", "IT IS EMPTY", "NEEDS REVISION"]
SystemType = Literal["RAG", "LLM", "Traditional ML", "Agentic", "Hybrid", "Other"]


class SystemMetric(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    monitoring_metric: str = Field(serialization_alias="Monitoring Metric")
    test_objective: str = Field(default="", serialization_alias="Test Objective")
    calculation_method: str = Field(
        default="",
        serialization_alias="Calculation Method/Formula",
    )


class ExtraInfo(BaseModel):
    question: str
    answer: str


class ExpectedMetric(BaseModel):
    name: str
    applicability_reason: str
    test_objective: str
    calculation_method: str


class MetricReview(BaseModel):
    metric: str
    objective_status: Status
    objective_reason: str
    objective_revised: str
    objective_questions: list[str] = Field(max_length=3)
    formula_status: Status
    formula_reason: str
    formula_revised: str
    formula_questions: list[str] = Field(max_length=3)

    @model_validator(mode="after")
    def validate_fields(self) -> "MetricReview":
        _validate_field(self.objective_status, self.objective_reason, self.objective_revised)
        _validate_field(self.formula_status, self.formula_reason, self.formula_revised)
        return self


def _validate_field(status: Status, reason: str, revised: str) -> None:
    if status == "NEEDS REVISION" and (not reason or not revised):
        raise ValueError("NEEDS REVISION requires a reason and revised text.")
    if status == "IT IS EMPTY" and not revised:
        raise ValueError("IT IS EMPTY requires proposed text.")
    if status == "OK" and revised:
        raise ValueError("OK must not contain revised text.")


class LLMOutput(BaseModel):
    business_use_case: str
    system_type: SystemType
    main_category: str
    subcategory: str
    closest_application: str
    components: list[str]
    input: str
    processing: str
    output: str
    understanding_confidence: int | None = Field(ge=0, le=100)
    questions: list[str] = Field(max_length=4)
    mrm_explanation: str
    flow: list[str]
    expected_metrics: list[ExpectedMetric]
    metric_reviews: list[MetricReview]


class LLMInput(BaseModel):
    system_main_info: str
    global_metrics: str
    system_metrics: list[SystemMetric]
    system_extra_info: list[ExtraInfo]
    previous_output: LLMOutput | None


class UploadedFileData(BaseModel):
    filename: str
    content: bytes
