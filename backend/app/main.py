"""FastAPI application entrypoint."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, chat, workflow
from app.db.session import Base, engine
from app.models import message, user, workflow_run  # noqa: F401  (registers tables before create_all)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Agent Framework",
    description="Multi-agent developer platform API",
    version="0.1.0",
)

# Allows the local Vite dev server (and a same-machine production build) to
# call this API from the browser. Tighten this to your real frontend origin
# before deploying anywhere public.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(workflow.router, prefix="/workflow", tags=["workflow"])


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}