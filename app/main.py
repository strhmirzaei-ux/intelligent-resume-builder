from fastapi import FastAPI

from app.api.routes.chat import router as chat_router

app = FastAPI(
    title="Intelligent Persian Resume Builder",
    version="0.1.0",
)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(chat_router, prefix="/api/v1")
