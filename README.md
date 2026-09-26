# Intelligent Persian Resume Builder

Ø³Ø§Ù…Ø§Ù†Ù‡â€ŒÛŒ ØªÙˆÙ„ÛŒØ¯ Ø±Ø²ÙˆÙ…Ù‡â€ŒÛŒ ÙØ§Ø±Ø³ÛŒ Ø¨Ø§ FastAPIØŒ PydanticØŒ Hazm Ùˆ SDK Ø±Ø³Ù…ÛŒ Google Gen AI Ø¨Ø±Ø§ÛŒ Ø§ØªØµØ§Ù„ Ø¨Ù‡ Gemini Ø¯Ø± AI Studio.

## Ø±Ø§Ù‡â€ŒØ§Ù†Ø¯Ø§Ø²ÛŒ Ù…Ø­Ù„ÛŒ

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
```

Ø³Ù¾Ø³ Ú©Ù„ÛŒØ¯ Gemini API Ø³Ø§Ø®ØªÙ‡â€ŒØ´Ø¯Ù‡ Ø¯Ø± Google AI Studio Ø±Ø§ Ø¯Ø± `LLM_API_KEY` Ùˆ Ù…Ø¯Ù„ Ø¯Ù„Ø®ÙˆØ§Ù‡ Ø±Ø§ Ø¯Ø± `LLM_MODEL` Ø¯Ø± ÙØ§ÛŒÙ„ `.env` ØªÙ†Ø¸ÛŒÙ… Ú©Ù†ÛŒØ¯. Ø¨Ø±Ù†Ø§Ù…Ù‡ Ø§Ø² SDK Ø±Ø³Ù…ÛŒ `google-genai` Ùˆ Ù…ØªØ¯ `models.generate_content` Ø§Ø³ØªÙØ§Ø¯Ù‡ Ù…ÛŒâ€ŒÚ©Ù†Ø¯.

## Ø§Ø¬Ø±Ø§

```powershell
uvicorn app.main:app --reload
```

Ù…Ø³ØªÙ†Ø¯Ø§Øª API Ø¯Ø± `http://127.0.0.1:8000/docs` Ùˆ health check Ø¯Ø± `/health` Ø¯Ø± Ø¯Ø³ØªØ±Ø³ Ø§Ø³Øª.

## ØªØ³Øª Ùˆ lint

```powershell
pytest -q
ruff check app tests
```

## Ù‚Ø§Ø¨Ù„ÛŒØªâ€ŒÙ‡Ø§ÛŒ Ù¾ÛŒØ§Ø¯Ù‡â€ŒØ³Ø§Ø²ÛŒâ€ŒØ´Ø¯Ù‡

- Ø´Ù…Ø§ÛŒ Ù…Ø±Ú©Ø²ÛŒ Ø±Ø²ÙˆÙ…Ù‡ Ø¨Ø§ provenance Ùˆ ÙˆØ¶Ø¹ÛŒØª Ù‡Ø± ÙÛŒÙ„Ø¯
- Ù†Ø±Ù…Ø§Ù„â€ŒØ³Ø§Ø²ÛŒ Ù…ØªÙ† ÙØ§Ø±Ø³ÛŒ Ùˆ Ø­ÙØ§Ø¸Øª Ø§Ø² emailØŒ URL Ùˆ Ø´Ù…Ø§Ø±Ù‡ ØªÙ„ÙÙ†
- Ø§Ø³ØªØ®Ø±Ø§Ø¬ JSON Ø¨Ø§ Ø§Ø¹ØªØ¨Ø§Ø±Ø³Ù†Ø¬ÛŒ Pydantic Ùˆ Ø³ÛŒØ§Ø³Øª Ø¶Ø¯Ø¬Ø¹Ù„
- SDK Ø±Ø³Ù…ÛŒ Google Gen AI Ø¨Ø±Ø§ÛŒ Ø§Ø±Ø³Ø§Ù„ Ø¯Ø±Ø®ÙˆØ§Ø³Øª Ø¨Ù‡ Gemini Developer API
- ØªØ­Ù„ÛŒÙ„ Ø´Ú©Ø§Ù Ùˆ Ù…Ø­Ø§Ø³Ø¨Ù‡â€ŒÛŒ Coverage Score
- ØªÙˆÙ„ÛŒØ¯ Ø³Ø¤Ø§Ù„â€ŒÙ‡Ø§ÛŒ ØªÚ©Ù…ÛŒÙ„ÛŒ LLM Ø¨Ø§ Ø§ÙˆÙ„ÙˆÛŒØªâ€ŒØ¨Ù†Ø¯ÛŒ
- Ø°Ø®ÛŒØ±Ù‡â€ŒØ³Ø§Ø²ÛŒ Ù…ÙˆÙ‚Øª JSON Ø¨Ø§ Ù†ÙˆØ´ØªÙ† Ø§ØªÙ…ÛŒÚ© Ùˆ TTL
- endpointÙ‡Ø§ÛŒ chat Ùˆ resume
- Ø±Ù†Ø¯Ø± HTML Ø§Ù…Ù† Ùˆ Ø±Ø§Ø³Øªâ€ŒØ¨Ù‡â€ŒÚ†Ù¾ Ø±Ø²ÙˆÙ…Ù‡

## Ø¯Ø± Ø¯Ø³Øª ØªÙˆØ³Ø¹Ù‡

- Ø®Ø±ÙˆØ¬ÛŒ PDF Ùˆ DOCX
- ØªÙˆÙ„ÛŒØ¯ Ùˆ Ø§Ø±Ø²ÛŒØ§Ø¨ÛŒ Ú†Ù†Ø¯ Ù†Ø³Ø®Ù‡â€ŒÛŒ Ø±Ø²ÙˆÙ…Ù‡ Ùˆ Ø§Ù†ØªØ®Ø§Ø¨ Ø¨Ù‡ØªØ±ÛŒÙ† Ù†Ø³Ø®Ù‡
- PostgreSQL
- Ø§Ø­Ø±Ø§Ø² Ù‡ÙˆÛŒØª Ùˆ rate limiting

