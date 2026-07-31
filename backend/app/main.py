from fastapi import FastAPI

from app.api.routes import auth, chat
from app.db.session import Base, engine
from app.models import message, user  # noqa: F401  (registers tables before create_all)

Base.metadata.create_all(bind=engine)

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