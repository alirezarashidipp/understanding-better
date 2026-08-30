# MRM Model Review

یک MVP محلی و تک‌کاربره با FastAPI برای فهم Use Case مدل، پرسیدن سؤال‌های ضروری از MRM Reviewer، انتخاب Metrics تأییدشده و بررسی مستقل Test Objective و Calculation Method / Formula است.

## ساختار

```text
main.py
requirements.txt
requirements-dev.txt
templates/
├── index.html
├── styles.css
└── app.js
src/
├── cli.py
├── api.py
├── config.py
├── schemas.py
├── input_reader.py
├── output_writer.py
├── openai_connection.py
├── ai_reviewer.py
├── prompt_loader.py
└── workflow.py
prompts/
├── use_case.yml
├── use_case_refinement.yml
└── metric_review.yml
```

شرح کامل مرز ماژول‌ها در [docs/architecture.md](docs/architecture.md) قرار دارد.

## فرایند توسعه

تغییرات MVP با Spec Kit مدیریت می‌شوند. قواعد ثابت پروژه در
`.specify/memory/constitution.md` قرار دارند و هر feature از مسیر specification، plan، tasks،
implementation و convergence عبور می‌کند. این فرایند نباید باعث اضافه‌شدن لایه‌های غیرضروری به
کد برنامه شود.

## ورودی‌ها

- دقیقاً یک فایل `QM-*.txt` که Reviewer داخل صفحه انتخاب می‌کند
- دقیقاً یک فایل `MRM_*.xlsx` که Reviewer داخل صفحه انتخاب می‌کند
- فایل catalog در `metrics/metrics.md`
- تنظیمات `OPENAI_API_KEY`، `OPENAI_MODEL` و `OPENAI_TEMPERATURE` در environment یا `.env.local`
- مقدار پیش‌فرض `OPENAI_TEMPERATURE` برابر `0.0` است و باید بین `0.0` و `2.0` باشد

فایل‌های انتخاب‌شده در `Input/` کپی نمی‌شوند. برنامه فقط همان دو فایل همان Review را می‌خواند.

ستون‌های اصلی Excel توسعه‌دهنده:

| Monitoring Metric | Test Objective | Calculation Method/Formula |
|---|---|---|

نام‌های قدیمی `Metric`، `Calcution Method/Formula` و `Calculation Method / Formula` نیز برای سازگاری پذیرفته می‌شوند.

## جریان بررسی

1. Reviewer یک QM و یک workbook را در صفحه انتخاب می‌کند؛ برنامه آن‌ها و ساختار کامل `metrics.md` را اعتبارسنجی می‌کند.
2. LLM یکی از شش دسته اصلی، نزدیک‌ترین زیرشاخه و نزدیک‌ترین Application موجود در catalog را انتخاب می‌کند.
3. LLM میزان اطمینان خود به درک اولیه محصول را با یک عدد صحیح از صفر تا صد اعلام می‌کند.
4. در صورت نیاز به درک بهتر سیستم، صفر تا چهار سؤال قابل پاسخ یا `Skip` نمایش داده می‌شود.
5. پس از `Next`، توضیح نهایی و Flow از نگاه MRM نمایش داده می‌شود.
6. فقط بعد از زدن `OK`، Metrics همان دسته بررسی و فایل‌های Excel نوشته می‌شوند.

## Prompt as YAML

- `prompts/use_case.yml`: فهم Use Case و حداکثر چهار سؤال
- `prompts/use_case_refinement.yml`: توضیح نهایی و Flow از نگاه MRM
- `prompts/metric_review.yml`: انتخاب Metrics و بررسی مستقل Objective و Formula

هر Prompt یک `version` ثابت و یک فیلد `instructions` دارد و قابل review و version control است.

## نصب

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip install -e .
```

برای ساخت محیط جدید:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip install -e .
```

## اجرا

روش‌های معتبر اجرا:

```powershell
.\.venv\Scripts\python.exe main.py
.\.venv\Scripts\uvicorn.exe main:app --host 127.0.0.1 --port 8000
mrm-review
```

سپس `http://127.0.0.1:8000` را باز کنید. مستندات API در `http://127.0.0.1:8000/api/docs` و health check در `/health` است.

## خروجی‌ها

هر Review دو فایل با یک شناسهٔ مشترک مستقیماً داخل `Output/` می‌سازد:

- `Output/mrm_review_<id>.xlsx`: سه ستون اصلی کاربر و سه ستون Validation/Revised/Questions برای هر یک از Objective و Formula
- `Output/missing_metrics_<id>.xlsx`: فقط Metrics ضروری غایب همراه دلیل نیاز، Objective و Formula پیشنهادی

Review بعدی فایل‌های قبلی را overwrite نمی‌کند و پوشهٔ جداگانه نیز نمی‌سازد.

## محدودیت‌های آگاهانه MVP

- بدون Authentication و Database
- state موقت داخل process
- بدون Multi-Agent و PDF
- بدون automated test در migration فعلی، مطابق تصمیم پروژه
