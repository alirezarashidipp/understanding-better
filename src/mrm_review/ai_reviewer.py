import json

from openai import OpenAI

from mrm_review.prompts import load_prompt
from mrm_review.schemas import (
    ClarificationAnswer,
    MetricCatalogItem,
    MetricCategory,
    MetricReviewResult,
    PendingReview,
    ReadyForMetricReview,
    RefinedUseCase,
    UseCaseDraft,
)

USE_CASE_PROMPT = load_prompt("use_case.yml")
USE_CASE_REFINEMENT_PROMPT = load_prompt("use_case_refinement.yml")
METRIC_REVIEW_PROMPT = load_prompt("metric_review.yml")


class OpenAIReviewer:
    def __init__(self, client: OpenAI, model: str) -> None:
        self.client = client
        self.model = model

    def create_draft(
        self,
        source_text: str,
        catalog: list[MetricCategory],
    ) -> UseCaseDraft:
        payload = {
            "source_text": source_text,
            "approved_catalog": [item.model_dump(mode="json") for item in catalog],
        }
        response = self.client.responses.parse(
            model=self.model,
            store=False,
            instructions=USE_CASE_PROMPT,
            input=json.dumps(payload, ensure_ascii=False),
            text_format=UseCaseDraft,
        )
        if response.output_parsed is None:
            raise RuntimeError("OpenAI did not return a valid use-case draft.")
        return response.output_parsed

    def refine_use_case(
        self,
        pending: PendingReview,
        answers: list[ClarificationAnswer],
    ) -> RefinedUseCase:
        payload = {
            "source_text": pending.source_text,
            "draft": pending.draft.model_dump(mode="json"),
            "clarification_answers": [answer.model_dump(mode="json") for answer in answers],
            "approved_catalog": [category.model_dump(mode="json") for category in pending.catalog],
        }
        response = self.client.responses.parse(
            model=self.model,
            store=False,
            instructions=USE_CASE_REFINEMENT_PROMPT,
            input=json.dumps(payload, ensure_ascii=False),
            text_format=RefinedUseCase,
        )
        if response.output_parsed is None:
            raise RuntimeError("OpenAI did not return a valid refined use case.")
        return response.output_parsed

    def review_metrics(
        self,
        ready: ReadyForMetricReview,
        eligible_metrics: list[MetricCatalogItem],
    ) -> MetricReviewResult:
        payload = {
            "refined_use_case": ready.refined.model_dump(mode="json"),
            "eligible_metrics": [metric.model_dump(mode="json") for metric in eligible_metrics],
            "developer_metrics": [
                metric.model_dump(mode="json") for metric in ready.pending.developer_metrics
            ],
        }
        response = self.client.responses.parse(
            model=self.model,
            store=False,
            instructions=METRIC_REVIEW_PROMPT,
            input=json.dumps(payload, ensure_ascii=False),
            text_format=MetricReviewResult,
        )
        if response.output_parsed is None:
            raise RuntimeError("OpenAI did not return a valid metric review.")
        return response.output_parsed
