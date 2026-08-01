# AI Agent Framework

A multi-agent developer platform with a full-stack UI: a system of cooperating
agents (planner, coder, tester, debugger, security auditor, reviewer) that plans a
task, writes real code, runs real tests against it, debugs its own failures,
audits the result for security issues, and reports back — with persistent memory,
real tool-calling through a plugin registry (sandboxed filesystem + shell + HTTP),
three swappable real LLM providers (Anthropic, OpenAI, Gemini) plus a free
deterministic mock, live WebSocket streaming of workflow progress, database
migrations, structured logging, rate limiting, full observability over past runs,
and a React dashboard to drive all of it.

Author: Potha Gouni Madhav

## Why this project

Most "AI agent" repos are thin wrappers around a single chat completion call. This
one is built like a real product: a typed backend with JWT auth and a
database-backed memory layer, a provider abstraction so the agents work identically
whether they're calling a real LLM (three different vendors, interchangeably) or a
deterministic mock, a workflow engine that chains agents together with a real
retry/feedback loop instead of running them in isolation, a plugin system so new
tools can be added without touching core code, real static-analysis security
review gating what gets approved, schema-managed database migrations instead of
"just create the tables," live progress streaming instead of a single blocking
response, and a proper frontend instead of only a Swagger page.

Everything below is actually implemented and covered by tests — nothing in this
README describes planned-but-unbuilt behavior.

## Architecture

```
Browser
   |
   v
Frontend (React + TypeScript, Vite dev server :5173)
   |  JWT bearer token, CORS
   v
API (FastAPI :8000)
   |
   +-- POST /chat -----------> Planner Agent <---> persistent memory (SQLite)
   |
   +-- POST /workflow/run --\
   +-- WS   /workflow/ws/run-+-> Planner -> Coder ---> writes solution.py
   |                            ^          |          (filesystem tool, via
   |                            |          v            plugin registry)
   |                     (retry loop)   Tester ---> runs real pytest
   |                            |          |         (bash tool, via registry)
   |                            |          v
   |                            +---- Debugger        (diagnoses failure,
   |                                  (on failure)      feeds Coder's retry)
   |                                       |
   |                                       v
   |                              Security Auditor    (real AST static
   |                                       |            analysis)
   |                                       v
   |                                   Reviewer -> approved / changes_requested
   |                                       |            (blocked by unresolved
   |                                       |             HIGH security findings)
   +-- GET /workflow/runs(/id) <---- WorkflowRun history (SQLite, via Alembic-
                                      managed schema)
```

The Coder and Tester aren't just generating text — they call real tools, looked up
by name through a plugin `ToolRegistry` rather than hardcoded imports. The Coder
writes an actual `solution.py` to a per-run sandboxed workspace directory; the
Tester writes a test file and actually executes `pytest` against it via subprocess,
checking the real exit code. If the Tester rejects the code, the Debugger turns the
raw pytest failure into a structured diagnosis (heuristic in mock mode, LLM-grounded
with a real provider), and the loop goes back to the Coder with that diagnosis
attached instead of failing outright, up to a configurable number of attempts. Once
the loop ends, the Security Auditor parses the final code into a Python AST and
checks for real risks (`eval`/`exec`, `os.system`, `shell=True`, unsafe
`pickle.load`, hardcoded secrets, SQL string-building) — a HIGH severity finding
blocks the Reviewer's approval even if every test passed. The frontend can watch
this entire pipeline happen live over a WebSocket instead of waiting for one big
response at the end.

## What's implemented

- **Auth**: signup/login, bcrypt password hashing, JWT bearer tokens, protected
  routes, IP-based rate limiting on signup/login
- **Chat**: `/chat` runs a Planner agent turn with conversation history persisted
  per (user, session) in the database, rate limited per user
- **Multi-agent workflow**: `/workflow/run` chains Planner → Coder → Tester →
  Debugger (on failure) → Security Auditor → Reviewer, with a real retry loop
  when tests fail
- **Live WebSocket streaming**: `/workflow/ws/run` runs the identical pipeline but
  pushes each agent's step to the client the instant it completes, instead of
  blocking for the whole run
- **Debugger agent**: turns a raw pytest failure into a structured root-cause +
  fix diagnosis (deterministic heuristic in mock mode, LLM-grounded with a real
  provider) that's handed to the Coder's next attempt
- **Security Auditor agent**: real AST-based static analysis over the generated
  code — flags `eval`/`exec`, `os.system`, `subprocess(..., shell=True)`, unsafe
  `pickle.load`, hardcoded secrets, and SQL built via string concatenation.
  Unresolved HIGH severity findings block Reviewer approval regardless of test
  results
- **Plugin tool system**: a `ToolRegistry` with a `@register_tool` decorator —
  `FileSystemTool`, `BashTool`, and `HttpTool` all self-register; agents look
  tools up by name instead of hardcoded imports, so a third-party tool can plug
  in with zero changes to core code
- **Multi-provider LLM support**: a common `LLMProvider` interface with four
  implementations — `MockProvider` (default, deterministic, zero cost, still
  exercises the full real pipeline including a real pytest run), and real
  `AnthropicProvider` / `OpenAIProvider` / `GeminiProvider`, switchable via one
  `LLM_PROVIDER` setting
- **Database migrations**: schema managed with Alembic instead of ad hoc
  `create_all` — an initial migration matching every model, verified
  upgrade/downgrade, plus a regression test that fails if a model ever drifts
  from its migration
- **Structured logging**: every HTTP request and every agent step is logged as a
  single JSON line (timestamp, level, logger, message, plus structured fields
  like `run_id`, `agent`, `duration_ms`)
- **Rate limiting**: in-memory sliding-window limits on auth, chat, and workflow
  endpoints, keyed by IP (unauthenticated routes) or user id (authenticated ones)
- **Observability**: every workflow run (both REST and WebSocket) is persisted
  (`GET /workflow/runs`, `GET /workflow/runs/{run_id}`), scoped per user
- **Frontend**: a React/TypeScript dashboard — login/signup, a chat view with live
  session memory, an animated Planner → Coder → Tester → Debugger → Security
  Auditor → Reviewer pipeline visualization for workflow runs (live over
  WebSocket, with retry attempts grouped visually), and a browsable run history
  panel with a detail view
- **89 automated backend tests** across 18 files covering auth, memory, the
  orchestrator's retry logic (including the Debugger hand-off), the sandboxed
  tools and plugin registry, the Security Auditor's static analysis rules, all
  four LLM providers' error paths, Alembic migration drift, the WebSocket route,
  and the real-provider code path (via a fake injected provider, so the suite
  never needs a real API key)

## Tech stack

- Backend: Python, FastAPI, Uvicorn (WebSocket support via `uvicorn[standard]`)
- Auth: `python-jose` (JWT), `passlib` + `bcrypt`
- Database: SQLAlchemy ORM + SQLite (swappable via `DATABASE_URL`), schema
  managed with Alembic
- LLM providers: a common `LLMProvider` interface; ships with Mock, Anthropic,
  OpenAI, and Gemini — each real provider is a lazy, optional dependency
- Tool system: a `ToolRegistry` plugin pattern; ships with a sandboxed
  filesystem tool, a sandboxed shell tool, and an HTTP fetch tool
- Testing: pytest, pytest-asyncio, FastAPI's `TestClient` (including
  `websocket_connect` for the streaming route)
- Frontend: React, TypeScript, Vite, Tailwind CSS, Framer Motion (animations),
  React Router, Axios, native WebSocket

## Project layout

```
backend/
  alembic.ini, alembic/            # schema migrations (env.py, versions/)
  app/
    main.py                # FastAPI app entrypoint, CORS, structured logging
    core/
      config.py             # settings (.env-driven)
      security.py            # password hashing, JWT, auth dependency
      logging.py              # JSON log formatting
      rate_limit.py           # sliding-window rate limiter + FastAPI deps
      providers/               # LLMProvider interface + mock/anthropic/openai/gemini
    api/routes/
      auth.py, chat.py, workflow.py, workflow_ws.py
    agents/
      base.py                 # BaseAgent / AgentContext / AgentResult
      planner.py, coder.py, tester.py, debugger.py, security_auditor.py, reviewer.py
      orchestrator.py          # DevWorkflow: chains the agents, retry loop, on_step streaming hook
      run_store.py             # persists/reads workflow run history
      code_extraction.py       # strips markdown fences from LLM output
    tools/
      base.py, registry.py     # BaseTool + plugin ToolRegistry
      filesystem.py, bash.py, http_tool.py   # sandboxed/registered tools
    memory/
      manager.py               # persistent per-session chat memory
    models/
      user.py, message.py, workflow_run.py
    db/
      session.py
  tests/                       # 89 tests across 18 files
  requirements.txt
  pytest.ini
.env.example

frontend/
  src/
    lib/          # API client (axios) + shared TypeScript types
    context/      # AuthContext (JWT stored in localStorage)
    components/   # Layout (nav + page transitions), AgentPipeline, ProtectedRoute
    pages/        # LoginPage, SignupPage, ChatPage, WorkflowPage (WebSocket-driven), RunHistoryPage
  .env.example
```

## Getting started

Run the backend and frontend in two separate terminals.

**Backend:**

```bash
cd backend
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows (PowerShell):
.venv\Scripts\activate

pip install -r requirements.txt
cp ../.env.example ../.env   # defaults work out of the box, no keys required

alembic upgrade head         # creates the database schema

python -m pytest -q          # 89 passed

# --reload-dir app scopes the dev-server file watcher to source code only —
# without it, files the agents write at runtime trigger unwanted restarts.
uvicorn app.main:app --reload --reload-dir app
```

**Frontend:**

```bash
cd frontend
npm install
cp .env.example .env   # points at http://127.0.0.1:8000 by default
npm run dev
```

Then open `http://localhost:5173`, sign up, and try the Chat and Workflow pages.
(The API is also browsable directly at `http://127.0.0.1:8000/docs`.)

By default everything runs on `LLM_PROVIDER=mock` — deterministic, free, and still
exercises the full real pipeline (real files written, real pytest run, real
security scan). To see actual task-specific code generation and real
conversational replies, pick a provider and set the matching key in
`backend/.env`:

| Provider  | `LLM_PROVIDER` | Install                     | Key               |
|-----------|-----------------|------------------------------|-------------------|
| Anthropic | `anthropic`     | `pip install anthropic`      | `ANTHROPIC_API_KEY` |
| OpenAI    | `openai`        | `pip install openai`         | `OPENAI_API_KEY`    |
| Gemini    | `gemini`        | `pip install google-genai`   | `GEMINI_API_KEY`    |

## Roadmap

- [x] Repo scaffold, FastAPI skeleton
- [x] Phase 1: Auth (JWT + bcrypt), SQLite-backed users
- [x] Phase 2: Planner agent, persistent chat memory
- [x] Phase 3: Multi-agent orchestration (Planner/Coder/Tester/Reviewer) with a
      real retry feedback loop
- [x] Phase 4: Real tool-calling (sandboxed filesystem + shell), workflow run
      history/observability, pluggable real LLM provider (Anthropic)
- [x] Frontend: React/TypeScript/Tailwind dashboard (auth, chat, animated
      workflow pipeline, run history)
- [x] Phase 5: Debugger + Security Auditor agents, plugin tool system, Alembic
      migrations, WebSocket live streaming, multi-provider support
      (OpenAI/Gemini), structured logging, rate limiting
- [ ] Phase 6: Distributed execution, plugin marketplace, drag-and-drop
      workflow builder

## License

MIT