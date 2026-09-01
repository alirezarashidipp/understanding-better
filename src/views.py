from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from openai import APIConnectionError, APIStatusError, AuthenticationError, RateLimitError
from pydantic import ValidationError


def render_page(
    templates: Jinja2Templates,
    request: Request,
    stage: str,
    *,
    error: Exception | str | None = None,
    status_code: int = 200,
    **context: object,
) -> HTMLResponse:
    if isinstance(error, Exception):
        status_code = 400 if isinstance(error, (ValueError, ValidationError)) else 502
        error = _public_error(error)
    if error is not None:
        context["error"] = error

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"stage": stage, **context},
        status_code=status_code,
    )


def _public_error(error: Exception) -> str:
    if isinstance(error, AuthenticationError):
        return "OpenAI authentication failed. Check OPENAI_API_KEY."
    if isinstance(error, RateLimitError):
        return "OpenAI could not complete the request because of quota or rate limits."
    if isinstance(error, APIConnectionError):
        return "OpenAI could not be reached. Check the network connection and retry."
    if isinstance(error, APIStatusError):
        return f"OpenAI request failed with status {error.status_code}. Retry this step."
    if isinstance(error, (ValueError, ValidationError)):
        return str(error)
    return "An unexpected internal error occurred. Retry this step."
