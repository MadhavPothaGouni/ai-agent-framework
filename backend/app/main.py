import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, budget, chat, workflow, workflow_approvals, workflow_ws
from app.core.logging import configure_logging, get_logger
from app.db.session import Base, engine
from app.models import approval, budget as budget_model, message, usage, user, workflow_run  # noqa: F401  (registers tables before create_all)

configure_logging()
logger = get_logger("http")

# create_all() is additive-only (it never alters or drops existing
# columns/tables), so it's safe to keep here purely for zero-friction local
# dev / a first run against a brand-new empty DB. It is NOT how schema
# changes should be made from here on — that's what alembic/ is for. Once
# the first migration has run, use `alembic revision --autogenerate` +
# `alembic upgrade head` for every future schema change; see README.md.
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


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)

    logger.info(
        "http_request",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "client": request.client.host if request.client else None,
        },
    )
    return response


app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(workflow.router, prefix="/workflow", tags=["workflow"])
app.include_router(workflow_ws.router, prefix="/workflow", tags=["workflow"])
app.include_router(workflow_approvals.router, prefix="/workflow", tags=["workflow"])
app.include_router(budget.router, prefix="/budget", tags=["budget"])


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}