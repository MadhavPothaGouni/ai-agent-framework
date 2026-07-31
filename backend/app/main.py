"""FastAPI application entrypoint."""
from fastapi import FastAPI

from app.api.routes import auth, chat

app = FastAPI(
    title="AI Agent Framework",
    description="Multi-agent developer platform API",
    version="0.1.0",
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
