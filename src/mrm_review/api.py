import logging
import re
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
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

from mrm_review.ai_reviewer import OpenAIReviewer
from mrm_review.config import AppSettings
from mrm_review.openai_connection import create_openai_client
from mrm_review.schemas import (
    ClarificationAnswer,
    PendingReview,
    ReadyForMetricReview,
    ReviewPaths,
    UploadedFileData,
)
from mrm_review.workflow import AIReviewer, finish_review, refine_review, start_review

logger = logging.getLogger(__name__)
DOWNLOAD_NAME = re.compile(r"(?:mrm_review|missing_metrics)_[0-9a-f]{32}\.xlsx")


def create_app(
    reviewer: AIReviewer | None = None,
    root: Path | None = None,
) -> FastAPI:
    project_root = (root or Path.cwd()).resolve()
    if reviewer is None:
        settings = AppSettings.from_env(project_root)
        client = create_openai_client(settings)
        active_reviewer = OpenAIReviewer(client=client, model=settings.openai_model)
    else:
        active_reviewer = reviewer
    templates = Jinja2Templates(directory=str(project_root / "templates"))
    draft_states: dict[str, PendingReview] = {}
    refined_states: dict[str, ReadyForMetricReview] = {}

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
            pending = start_review(
                ReviewPaths.from_root(project_root),
                active_reviewer,
                qm_files=qm_files,
                workbook_files=workbook_files,
            )
            review_id = uuid4().hex
            draft_states[review_id] = pending
            return render_page(
                request,
                "questions",
                review_id=review_id,
                draft=pending.draft,
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
        pending = draft_states.get(review_id)
        if pending is None:
            return render_error(request, "This review session is no longer available.")

        answers = []
        for question in pending.draft.questions:
            skipped = form.get(f"skip_{question.id}") == "on"
            raw_answer = str(form.get(f"answer_{question.id}", "")).strip()
            answers.append(
                ClarificationAnswer(
                    question_id=question.id,
                    answer="" if skipped else raw_answer,
                    skipped=skipped,
                )
            )

        try:
            ready = refine_review(pending, answers, active_reviewer)
            draft_states.pop(review_id, None)
            refined_states[review_id] = ready
            return render_page(
                request,
                "understanding",
                review_id=review_id,
                refined=ready.refined,
            )
        except OpenAIError as error:
            message, status_code = _provider_error(error)
            return render_error(request, message, status_code=status_code)
        except (ValueError, RuntimeError) as error:
            return render_error(request, str(error))
        except Exception:
            logger.exception("Use-case refinement failed")
            return render_error(
                request,
                "The final MRM understanding could not be created. Please try again.",
            )

    @app.post("/review", response_class=HTMLResponse, name="review")
    async def review(request: Request) -> HTMLResponse:
        form = await request.form()
        review_id = str(form.get("review_id", ""))
        ready = refined_states.get(review_id)
        if ready is None:
            return render_error(request, "This review session is no longer available.")

        try:
            completed = finish_review(ready, active_reviewer)
            refined_states.pop(review_id, None)
            return render_page(
                request,
                "result",
                refined=ready.refined,
                result=completed.result,
                outputs=completed.outputs,
            )
        except OpenAIError as error:
            message, status_code = _provider_error(error)
            return render_error(request, message, status_code=status_code)
        except (ValueError, RuntimeError) as error:
            return render_error(request, str(error))
        except Exception:
            logger.exception("Metric review failed")
            return render_error(
                request,
                "The metric review could not be completed. Please try again.",
            )

    @app.get("/download/{name}", name="download")
    async def download(name: str) -> FileResponse:
        output_dir = (project_root / "Output").resolve()
        path = (output_dir / name).resolve()
        if (
            Path(name).name != name
            or DOWNLOAD_NAME.fullmatch(name) is None
            or path.parent != output_dir
        ):
            raise HTTPException(status_code=404, detail="File not found")
        if not path.is_file():
            raise HTTPException(status_code=404, detail="File not found")
        return FileResponse(
            path,
            filename=name,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    app.state.project_root = project_root
    app.state.draft_states = draft_states
    app.state.refined_states = refined_states
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
