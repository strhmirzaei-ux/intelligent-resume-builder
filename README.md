# Intelligent Persian Resume Builder

سامانه‌ی تولید رزومه‌ی فارسی با FastAPI، Pydantic، Hazm و یک endpoint سازگار با OpenAI.

## راه‌اندازی محلی

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
```

سپس مقادیر `LLM_API_KEY`، `LLM_BASE_URL` و `LLM_MODEL` را در `.env` تنظیم کنید.

## اجرا

```powershell
uvicorn app.main:app --reload
```

مستندات API در `http://127.0.0.1:8000/docs` و health check در `/health` در دسترس است.

## تست و lint

```powershell
pytest -q
ruff check app tests
```

## قابلیت‌های پیاده‌سازی‌شده

- شمای مرکزی رزومه با provenance و وضعیت هر فیلد
- نرمال‌سازی متن فارسی و حفاظت از email، URL و شماره تلفن
- استخراج JSON با اعتبارسنجی Pydantic و سیاست ضدجعل
- client سازگار با OpenAI برای InferX
- تحلیل شکاف و محاسبه‌ی Coverage Score
- تولید سؤال‌های تکمیلی rule-based با اولویت‌بندی
- ذخیره‌سازی موقت JSON با نوشتن اتمیک و TTL
- endpointهای chat و resume
- رندر HTML امن و راست‌به‌چپ رزومه

## در دست توسعه

- خروجی PDF و DOCX
- تولید و ارزیابی چند نسخه‌ی رزومه و انتخاب بهترین نسخه
- PostgreSQL
- احراز هویت و rate limiting
