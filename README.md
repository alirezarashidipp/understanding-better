# MRM Model Review

یک MVP محلی و تک‌کاربره با FastAPI برای فهم Use Case و بررسی Metrics از دید MRM است.

## ساختار ساده

```text
QM-*.txt + MRM_*.xlsx + metrics/metrics.md
                    ↓
                 LLMInput
                    ↓
       Call 1 → Call 2 اختیاری → OK → Call 3
                    ↓
                 LLMOutput
                    ↓
                  Browser
```

کدهای اصلی مستقیماً زیر `src/` هستند:

- `user_input_reader.py`: خواندن TXT و سه ستون Excel
- `metric_catalog_reader.py`: خواندن متن خام `metrics.md` و parse حداقلی برای validation
- `schemas.py`: تعریف `LLMInput`، `LLMOutput` و ردیف‌های ساده آن‌ها
- `ai_reviewer.py`: سه فراخوانی OpenAI با schema یکسان
- `workflow.py`: ترتیب خطی سه مرحله و validation
- `api.py`: routeها و state موقت داخل process
- `templates/`: صفحه ساده برنامه

Promptها در سه فایل YAML زیر `prompts/` هستند و داخل کد Python نوشته نشده‌اند.

## ورودی‌ها

- دقیقاً یک `QM-*.txt`
- دقیقاً یک `MRM_*.xlsx`
- catalog ثابت `metrics/metrics.md`
- تنظیمات `OPENAI_API_KEY`، `OPENAI_MODEL` و `OPENAI_TEMPERATURE` در environment یا `.env.local`

متن TXT بدون تغییر در `system_main_info` قرار می‌گیرد. متن کامل Markdown بدون بازسازی در
`global_metrics` قرار می‌گیرد. هر ردیف Excel در `system_metrics` فقط این سه کلید را دارد:

| Monitoring Metric | Test Objective | Calculation Method/Formula |
|---|---|---|

نام‌های قدیمی `Metric`، `Calcution Method/Formula` و `Calculation Method / Formula` نیز هنگام
خواندن Excel پذیرفته می‌شوند، اما JSON همیشه نام‌های canonical بالا را دارد.

## جریان بررسی

1. Call 1 اطلاعات اصلی، catalog کامل و metrics فایل Excel را می‌گیرد و درک اولیه، confidence و صفر تا چهار سؤال را برمی‌گرداند.
2. Reviewer می‌تواند سؤال‌ها را جواب دهد یا Skip کند. اگر هیچ جواب واقعی وجود نداشته باشد، Call 2 اجرا نمی‌شود.
3. نتیجه فعلی نمایش داده می‌شود. فقط دکمه‌ای با متن دقیق `OK` Call 3 را شروع می‌کند.
4. Call 3 expected metrics و بررسی مستقل Objective و Formula را برمی‌گرداند.

هر سه Call همان `LLMInput` و `LLMOutput` را استفاده می‌کنند. فیلدهای مرحله‌های آینده تا زمان
خود آن مرحله خالی می‌مانند. خروجی نامعتبر فقط یک repair attempt می‌گیرد؛ خطاهای provider مثل
authentication، billing، rate limit و connection به‌صورت خودکار repair نمی‌شوند.

## نصب و اجرا

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe main.py
```

سپس `http://127.0.0.1:8000` را باز کنید. مستندات API در `/api/docs` و health check در `/health` است.

## خروجی

نتیجه کامل فقط در صفحه مرورگر نمایش داده می‌شود. برنامه هیچ فایل Excel یا JSON خروجی نمی‌سازد.

## محدودیت‌های آگاهانه MVP

- بدون Authentication و Database
- state موقت داخل process
- بدون Multi-Agent و PDF
- بدون automated test در migration فعلی، مطابق تصمیم پروژه
