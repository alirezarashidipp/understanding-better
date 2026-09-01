from dataclasses import dataclass
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.datastructures import FormData

from ai_reviewer import OpenAIReviewer
from config import AppSettings
from metric_catalog_reader import parse_global_metrics, read_global_metrics
from schemas import ExtraInfo, LLMInput, LLMOutput, UploadedFileData
from user_input_reader import read_user_inputs
from views import render_page
from workflow import build_workflows

ReviewStage = Literal["questions", "understanding", "result"]
REVIEW_NOT_FOUND = "This review was not found. Start a new review."


@dataclass
class PendingReview:
    data: LLMInput
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

    def render_review(
        request: Request,
        review_id: str,
        pending: PendingReview,
        *,
        error: Exception | str | None = None,
        status_code: int = 200,
    ) -> HTMLResponse:
        return render_page(
            templates,
            request,
            pending.stage,
            review_id=review_id,
            result=pending.result,
            error=error,
            status_code=status_code,
        )

    app = FastAPI(title="MRM Model Review", docs_url="/api/docs", redoc_url=None)
    app.mount(
        "/static",
        StaticFiles(directory=active_settings.root / "templates"),
        name="static",
    )

    @app.get("/", response_class=HTMLResponse, name="index")
    async def index(request: Request) -> HTMLResponse:
        return render_page(templates, request, "start")

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
            return render_page(templates, request, "error", error=error)

        review_id = uuid4().hex
        reviews[review_id] = PendingReview(
            data=workflow_input,
            result=result,
            stage="questions",
        )
        return render_page(
            templates,
            request,
            "questions",
            review_id=review_id,
            result=result,
        )

    @app.post("/refine", response_class=HTMLResponse, name="refine")
    async def refine(request: Request) -> HTMLResponse:
        form = await request.form()
        review_id = str(form.get("review_id", ""))
        pending = reviews.get(review_id)
        if pending is None:
            return render_page(
                templates,
                request,
                "error",
                error=REVIEW_NOT_FOUND,
                status_code=404,
            )
        if pending.stage != "questions":
            return render_review(
                request,
                review_id,
                pending,
                error="This review has already moved past clarification.",
                status_code=409,
            )

        answers = _answered_questions(form, pending.result.questions)
        workflow_input = pending.data.model_copy(
            update={
                "system_extra_info": answers,
                "previous_output": pending.result,
            }
        )

        try:
            result = refine_workflow.invoke(workflow_input)
        except Exception as error:
            return render_review(request, review_id, pending, error=error)

        pending.result = result
        pending.stage = "understanding"
        return render_review(request, review_id, pending)

    @app.post("/review", response_class=HTMLResponse, name="review")
    async def review(request: Request) -> HTMLResponse:
        form = await request.form()
        review_id = str(form.get("review_id", ""))
        pending = reviews.get(review_id)
        if pending is None:
            return render_page(
                templates,
                request,
                "error",
                error=REVIEW_NOT_FOUND,
                status_code=404,
            )
        if pending.stage != "understanding":
            return render_review(
                request,
                review_id,
                pending,
                error="Metric review can start only after the final understanding is shown.",
                status_code=409,
            )

        workflow_input = pending.data.model_copy(update={"previous_output": pending.result})
        try:
            result = review_workflow.invoke(workflow_input)
        except Exception as error:
            return render_review(request, review_id, pending, error=error)

        pending.result = result
        pending.stage = "result"
        return render_review(request, review_id, pending)

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
