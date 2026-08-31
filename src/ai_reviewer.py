import json

from openai import OpenAI

from prompt_loader import load_prompt
from schemas import LLMInput, LLMOutput

CALL_1_PROMPT = load_prompt("use_case.yml")
CALL_2_PROMPT = load_prompt("use_case_refinement.yml")
CALL_3_PROMPT = load_prompt("metric_review.yml")


class OpenAIReviewer:
    def __init__(self, client: OpenAI, model: str, temperature: float) -> None:
        self.client = client
        self.model = model
        self.temperature = temperature

    def call_1(self, data: LLMInput, *, repair_feedback: str = "") -> LLMOutput:
        return self._request(CALL_1_PROMPT, data, repair_feedback)

    def call_2(self, data: LLMInput, *, repair_feedback: str = "") -> LLMOutput:
        return self._request(CALL_2_PROMPT, data, repair_feedback)

    def call_3(self, data: LLMInput, *, repair_feedback: str = "") -> LLMOutput:
        return self._request(CALL_3_PROMPT, data, repair_feedback)

    def _request(self, prompt: str, data: LLMInput, repair_feedback: str) -> LLMOutput:
        instructions = prompt
        if repair_feedback:
            instructions += f"\n\nPrevious output validation error: {repair_feedback}"
        response = self.client.responses.parse(
            model=self.model,
            temperature=self.temperature,
            store=False,
            instructions=instructions,
            input=json.dumps(data.model_dump(mode="json", by_alias=True), ensure_ascii=False),
            text_format=LLMOutput,
        )
        if response.output_parsed is None:
            raise ValueError("OpenAI did not return a valid structured result.")
        return response.output_parsed
