import logging
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    NotFoundError,
    OpenAIError,
    PermissionDeniedError,
    RateLimitError,
)
from starlette.datastructures import UploadFile

from ai_reviewer import OpenAIReviewer
from config import AppSettings
from openai_connection import create_openai_client
from schemas import ExtraInfo, UploadedFileData
from workflow import AIReviewer, ReviewState, continue_review, finish_review, start_review

logger = logging.getLogger(__name__)


def create_app(
    reviewer: AIReviewer | None = None,
    root: Path | None = None,
) -> FastAPI:
    project_root = (root or Path.cwd()).resolve()
    if reviewer is None:
        settings = AppSettings.from_env(project_root)
        client = create_openai_client(settings)
        active_reviewer = OpenAIReviewer(
            client=client,
            model=settings.openai_model,
            temperature=settings.openai_temperature,
        )
    else:
        active_reviewer = reviewer
    templates = Jinja2Templates(directory=str(project_root / "templates"))
    question_states: dict[str, ReviewState] = {}
    ready_states: dict[str, ReviewState] = {}

    def render_page(
        request: Request,
        stage: str,
        *,
        status_code: int = 200,
        **context: object,
    ) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"stage": stage, **context},
            status_code=status_code,
        )

    def render_error(
        request: Request,
        message: str,
        status_code: int = 400,
    ) -> HTMLResponse:
        return render_page(request, "error", status_code=status_code, error=message)

    app = FastAPI(
        title="MRM Model Review",
        version="0.3.0",
        docs_url="/api/docs",
        redoc_url=None,
    )
    app.mount(
        "/static",
        StaticFiles(directory=str(project_root / "templates")),
        name="static",
    )

    @app.get("/health", name="health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse, name="index")
    async def index(request: Request) -> HTMLResponse:
        return render_page(request, "start")

    @app.post("/start", response_class=HTMLResponse, name="start")
    async def start(request: Request) -> HTMLResponse:
        try:
            async with request.form(max_files=2) as form:
                qm_files = await _uploaded_files(form.getlist("qm_file"))
                workbook_files = await _uploaded_files(form.getlist("workbook_file"))
            state = start_review(
                project_root / "metrics" / "metrics.md",
                active_reviewer,
                qm_files=qm_files,
                workbook_files=workbook_files,
            )
            review_id = uuid4().hex
            question_states[review_id] = state
            return render_page(
                request,
                "questions",
                review_id=review_id,
                result=state[1],
            )
        except OpenAIError as error:
            message, status_code = _provider_error(error)
            return render_error(request, message, status_code=status_code)
        except (FileNotFoundError, ValueError, RuntimeError) as error:
            return render_error(request, str(error))
        except Exception:
            logger.exception("Review start failed")
            return render_error(
                request,
                "The review could not be started. Check the inputs and try again.",
            )

    @app.post("/refine", response_class=HTMLResponse, name="refine")
    async def refine(request: Request) -> HTMLResponse:
        form = await request.form()
        review_id = str(form.get("review_id", ""))
        state = question_states.get(review_id)
        if state is None:
            return render_error(request, "This review session is no longer available.")

        data, previous_output = state
        answers = []
        for index, question in enumerate(previous_output.questions):
            skipped = form.get(f"skip_{index}") == "on"
            answer = str(form.get(f"answer_{index}", "")).strip()
            if answer and not skipped:
                answers.append(ExtraInfo(question=question, answer=answer))

        try:
            ready = continue_review(data, previous_output, answers, active_reviewer)
            question_states.pop(review_id, None)
            ready_states[review_id] = ready
            return render_page(
                request,
                "understanding",
                review_id=review_id,
                result=ready[1],
            )
        except OpenAIError as error:
            message, status_code = _provider_error(error)
            return render_page(
                request,
                "questions",
                status_code=status_code,
                error=message,
                review_id=review_id,
                result=previous_output,
            )
        except (ValueError, RuntimeError) as error:
            return render_page(
                request,
                "questions",
                status_code=400,
                error=str(error),
                review_id=review_id,
                result=previous_output,
            )
        except Exception:
            logger.exception("Use-case refinement failed")
            return render_page(
                request,
                "questions",
                status_code=500,
                error="The final MRM understanding could not be created. Please try again.",
                review_id=review_id,
                result=previous_output,
            )

    @app.post("/review", response_class=HTMLResponse, name="review")
    async def review(request: Request) -> HTMLResponse:
        form = await request.form()
        review_id = str(form.get("review_id", ""))
        state = ready_states.get(review_id)
        if state is None:
            return render_error(request, "This review session is no longer available.")

        data, previous_output = state
        try:
            result = finish_review(data, previous_output, active_reviewer)
            ready_states.pop(review_id, None)
            return render_page(request, "result", result=result)
        except OpenAIError as error:
            message, status_code = _provider_error(error)
            return render_page(
                request,
                "understanding",
                status_code=status_code,
                error=message,
                review_id=review_id,
                result=previous_output,
            )
        except (ValueError, RuntimeError) as error:
            return render_page(
                request,
                "understanding",
                status_code=400,
                error=str(error),
                review_id=review_id,
                result=previous_output,
            )
        except Exception:
            logger.exception("Metric review failed")
            return render_page(
                request,
                "understanding",
                status_code=500,
                error="The metric review could not be completed. Please try again.",
                review_id=review_id,
                result=previous_output,
            )

    app.state.project_root = project_root
    app.state.question_states = question_states
    app.state.ready_states = ready_states
    return app


def _provider_error(error: OpenAIError) -> tuple[str, int]:
    if isinstance(error, AuthenticationError):
        return "OpenAI authentication failed. Check the configured API credential.", 503
    if isinstance(error, (PermissionDeniedError, NotFoundError)):
        return "OpenAI model access failed. Check the configured model and project access.", 503
    if isinstance(error, RateLimitError):
        error_body = error.body if isinstance(error.body, dict) else {}
        error_code = error_body.get("code") or getattr(error, "code", None)
        if error_code == "credit_balance_exhausted":
            return (
                "OpenAI API credits are exhausted. Add API credits or use a project key "
                "with available billing, then try again.",
                503,
            )
        return "OpenAI is temporarily rate-limiting requests. Please try again shortly.", 503
    if isinstance(error, APITimeoutError):
        return "The OpenAI request timed out. Please try again.", 503
    if isinstance(error, APIConnectionError):
        return "OpenAI could not be reached. Check the connection and try again.", 503
    if isinstance(error, APIStatusError):
        return "OpenAI could not complete the request. Please try again.", 502
    return "The OpenAI request failed. Please try again.", 502


async def _uploaded_files(values: list[object]) -> list[UploadedFileData]:
    uploads = []
    for value in values:
        if isinstance(value, UploadFile):
            uploads.append(
                UploadedFileData(
                    filename=value.filename or "",
                    content=await value.read(),
                )
            )
    return uploads
