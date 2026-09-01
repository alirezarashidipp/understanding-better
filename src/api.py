from dataclasses import dataclass
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from openai import APIConnectionError, APIStatusError, AuthenticationError, RateLimitError
from pydantic import ValidationError
from starlette.datastructures import FormData

from ai_reviewer import OpenAIReviewer
from config import AppSettings
from metric_catalog_reader import parse_global_metrics, read_global_metrics
from schemas import ExtraInfo, LLMInput, LLMOutput, SystemMetric, UploadedFileData
from user_input_reader import read_user_inputs
from workflow import build_workflows

ReviewStage = Literal["questions", "understanding", "result"]


@dataclass
class PendingReview:
    system_main_info: str
    global_metrics: str
    developer_metrics: list[SystemMetric]
    result: LLMOutput
    stage: ReviewStage


def create_app(
    settings: AppSettings | None = None,
    reviewer: OpenAIReviewer | None = None,
) -> FastAPI:
    active_settings = settings or AppSettings.from_env()
    active_reviewer = reviewer or OpenAIReviewer(
        api_key=active_settings.openai_api_key.get_secret_value(),
        model=active_settings.openai_model,
        temperature=active_settings.openai_temperature,
    )

    global_metrics = read_global_metrics(active_settings.root / "metrics" / "metrics.md")
    catalog = parse_global_metrics(global_metrics)
    start_workflow, refine_workflow, review_workflow = build_workflows(
        active_reviewer,
        catalog,
    )

    templates = Jinja2Templates(directory=active_settings.root / "templates")
    reviews: dict[str, PendingReview] = {}

    app = FastAPI(title="MRM Model Review", docs_url="/api/docs", redoc_url=None)
    app.mount(
        "/static",
        StaticFiles(directory=active_settings.root / "templates"),
        name="static",
    )

    @app.get("/", response_class=HTMLResponse, name="index")
    async def index(request: Request) -> HTMLResponse:
        return _page(templates, request, stage="start")

    @app.get("/health", name="health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/start", response_class=HTMLResponse, name="start")
    async def start(
        request: Request,
        qm_file: Annotated[UploadFile, File()],
        workbook_file: Annotated[UploadFile, File()],
    ) -> HTMLResponse:
        try:
            qm_upload = await _uploaded_file_data(qm_file)
            workbook_upload = await _uploaded_file_data(workbook_file)
            system_main_info, developer_metrics = read_user_inputs(
                [qm_upload],
                [workbook_upload],
            )
            workflow_input = LLMInput(
                system_main_info=system_main_info,
                global_metrics=global_metrics,
                system_metrics=developer_metrics,
                system_extra_info=[],
                previous_output=None,
            )
            result = start_workflow.invoke(workflow_input)
        except Exception as error:
            return _page(
                templates,
                request,
                stage="error",
                error=_public_error(error),
                status_code=_status_code(error),
            )

        review_id = uuid4().hex
        reviews[review_id] = PendingReview(
            system_main_info=system_main_info,
            global_metrics=global_metrics,
            developer_metrics=developer_metrics,
            result=result,
            stage="questions",
        )
        return _page(
            templates,
            request,
            stage="questions",
            review_id=review_id,
            result=result,
        )

    @app.post("/refine", response_class=HTMLResponse, name="refine")
    async def refine(request: Request) -> HTMLResponse:
        form = await request.form()
        review_id = str(form.get("review_id", ""))
        pending = reviews.get(review_id)
        if pending is None:
            return _page(
                templates,
                request,
                stage="error",
                error="This review was not found. Start a new review.",
                status_code=404,
            )
        if pending.stage != "questions":
            return _page(
                templates,
                request,
                stage=pending.stage,
                review_id=review_id,
                result=pending.result,
                error="This review has already moved past clarification.",
                status_code=409,
            )

        answers = _answered_questions(form, pending.result.questions)
        workflow_input = LLMInput(
            system_main_info=pending.system_main_info,
            global_metrics=pending.global_metrics,
            system_metrics=pending.developer_metrics,
            system_extra_info=answers,
            previous_output=pending.result,
        )

        try:
            result = refine_workflow.invoke(workflow_input)
        except Exception as error:
            return _page(
                templates,
                request,
                stage="questions",
                review_id=review_id,
                result=pending.result,
                error=_public_error(error),
                status_code=_status_code(error),
            )

        pending.result = result
        pending.stage = "understanding"
        return _page(
            templates,
            request,
            stage="understanding",
            review_id=review_id,
            result=result,
        )

    @app.post("/review", response_class=HTMLResponse, name="review")
    async def review(request: Request) -> HTMLResponse:
        form = await request.form()
        review_id = str(form.get("review_id", ""))
        pending = reviews.get(review_id)
        if pending is None:
            return _page(
                templates,
                request,
                stage="error",
                error="This review was not found. Start a new review.",
                status_code=404,
            )
        if pending.stage != "understanding":
            return _page(
                templates,
                request,
                stage=pending.stage,
                review_id=review_id,
                result=pending.result,
                error="Metric review can start only after the final understanding is shown.",
                status_code=409,
            )

        workflow_input = LLMInput(
            system_main_info=pending.system_main_info,
            global_metrics=pending.global_metrics,
            system_metrics=pending.developer_metrics,
            system_extra_info=[],
            previous_output=pending.result,
        )
        try:
            result = review_workflow.invoke(workflow_input)
        except Exception as error:
            return _page(
                templates,
                request,
                stage="understanding",
                review_id=review_id,
                result=pending.result,
                error=_public_error(error),
                status_code=_status_code(error),
            )

        pending.result = result
        pending.stage = "result"
        return _page(
            templates,
            request,
            stage="result",
            review_id=review_id,
            result=result,
        )

    return app


async def _uploaded_file_data(upload: UploadFile) -> UploadedFileData:
    try:
        return UploadedFileData(
            filename=upload.filename or "",
            content=await upload.read(),
        )
    finally:
        await upload.close()


def _answered_questions(form: FormData, questions: list[str]) -> list[ExtraInfo]:
    answers: list[ExtraInfo] = []
    for index, question in enumerate(questions):
        if f"skip_{index}" in form:
            continue
        answer = str(form.get(f"answer_{index}", "")).strip()
        if answer:
            answers.append(ExtraInfo(question=question, answer=answer))
    return answers


def _page(
    templates: Jinja2Templates,
    request: Request,
    *,
    stage: str,
    status_code: int = 200,
    **context: object,
) -> HTMLResponse:
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


def _status_code(error: Exception) -> int:
    if isinstance(error, (ValueError, ValidationError)):
        return 400
    return 502
