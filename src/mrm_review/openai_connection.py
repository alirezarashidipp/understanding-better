from openai import OpenAI

from mrm_review.config import AppSettings


def create_openai_client(settings: AppSettings) -> OpenAI:
    return OpenAI(api_key=settings.openai_api_key.get_secret_value())
