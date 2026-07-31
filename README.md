# AI Agent Framework

A multi-agent developer platform: a system of cooperating agents (planner, coder,
tester, reviewer) that plans a task, writes real code, runs real tests against it,
and reports back — with persistent memory, real tool-calling (sandboxed filesystem +
shell), a pluggable LLM provider (mock by default, real Claude on request), and full
observability over past runs.

Author: Potha Gouni Madhav

## Why this project

Most "AI agent" repos are thin wrappers around a single chat completion call. This
one is built like a real backend service: JWT auth with hashed passwords, a
database-backed memory layer, a provider abstraction so the agents work identically
whether they're calling a real LLM or a deterministic mock, and a workflow engine
that chains agents together with a real retry/feedback loop instead of running them
in isolation.

Everything below is actually implemented and covered by tests — nothing in this
README describes planned-but-unbuilt behavior.

## Architecture

```
User (JWT) -> API
                |
                +-- POST /chat --------> Planner Agent <---> persistent memory (SQLite)
                |
                +-- POST /workflow/run -> Planner -> Coder ---> writes solution.py
                |                            ^          |       (FileSystemTool, sandboxed)
                |                            |          v
                |                     (retry loop)   Tester ---> runs real pytest
                |                            |          |        (BashTool, sandboxed)
                |                            +----------+
                |                                       v
                |                                   Reviewer -> approved / changes_requested
                |                                       |
                +-- GET /workflow/runs(/id) <---- WorkflowRun history (SQLite)
```

The Coder and Tester aren't just generating text — they call real tools. The Coder
writes an actual `solution.py` to a per-run sandboxed workspace directory; the Tester
writes a test file and actually executes `pytest` against it via subprocess, checking
the real exit code. If the Tester rejects the code, the loop goes back to the Coder
(with the failure reason attached) instead of failing outright, up to a configurable
number of attempts.

## What's implemented

- **Auth**: signup/login, bcrypt password hashing, JWT bearer tokens, protected routes
- **Chat**: `/chat` runs a Planner agent turn with conversation history persisted
  per (user, session) in the database
- **Multi-agent workflow**: `/workflow/run` chains Planner → Coder → Tester →
  Reviewer, with a real retry loop when tests fail
- **Real tool-calling**: sandboxed `FileSystemTool` (read/write/list, blocks path
  traversal) and `BashTool` (subprocess runner with timeout, cwd locked to the
  workspace)
- **Pluggable LLM provider**: `MockProvider` (default — deterministic, zero API
  keys, zero cost, still exercises the full real pipeline including a real pytest
  run) and `AnthropicProvider` (real Claude-generated code, plus real
  Claude-generated tests tailored to that code)
- **Observability**: every workflow run is persisted (`GET /workflow/runs`,
  `GET /workflow/runs/{run_id}`), scoped per user
- **38 automated tests** covering auth, memory, the orchestrator's retry logic,
  the sandboxed tools, and the real-provider code path (via a fake injected
  provider, so the test suite never needs a real API key)

## Tech stack

- Backend: Python, FastAPI, Uvicorn
- Auth: `python-jose` (JWT), `passlib` + `bcrypt`
- Database: SQLAlchemy ORM + SQLite (swappable via `DATABASE_URL`)
- LLM providers: a common `LLMProvider` interface; ships with Mock and Anthropic,
  designed to add OpenAI/Gemini/Ollama the same way
- Testing: pytest, pytest-asyncio, FastAPI's `TestClient`

## Project layout

```
backend/
  app/
    main.py                # FastAPI app entrypoint
    core/
      config.py             # settings (.env-driven)
      security.py            # password hashing, JWT, auth dependency
      providers/              # LLMProvider interface + mock/anthropic implementations
    api/routes/
      auth.py, chat.py, workflow.py
    agents/
      base.py                 # BaseAgent / AgentContext / AgentResult
      planner.py, coder.py, tester.py, reviewer.py
      orchestrator.py          # DevWorkflow: chains the agents + retry loop
      run_store.py             # persists/reads workflow run history
      code_extraction.py       # strips markdown fences from LLM output
    tools/
      base.py, filesystem.py, bash.py   # sandboxed tool-calling
    memory/
      manager.py               # persistent per-session chat memory
    models/
      user.py, message.py, workflow_run.py
    db/
      session.py
  tests/                       # 38 tests across 11 files
  requirements.txt
  pytest.ini
.env.example
```

## Getting started

```bash
cd backend
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows (PowerShell):
.venv\Scripts\activate

pip install -r requirements.txt
cp ../.env.example ../.env   # defaults work out of the box, no keys required

python -m pytest -q          # 38 passed

# --reload-dir app scopes the dev-server file watcher to source code only —
# without it, files the agents write at runtime trigger unwanted restarts.
uvicorn app.main:app --reload --reload-dir app
```

Then open `http://127.0.0.1:8000/docs`, sign up, authorize with the token, and try
`POST /workflow/run` with a task like `{"task": "build a calculator"}`.

By default this runs entirely on `LLM_PROVIDER=mock` — deterministic, free, and still
exercises the full real pipeline (real files written, real pytest run). To see actual
task-specific code generation, get an API key from console.anthropic.com,
`pip install anthropic`, and set `ANTHROPIC_API_KEY` + `LLM_PROVIDER=anthropic` in
`.env`.

## Roadmap

- [x] Repo scaffold, FastAPI skeleton
- [x] Phase 1: Auth (JWT + bcrypt), SQLite-backed users
- [x] Phase 2: Planner agent, persistent chat memory
- [x] Phase 3: Multi-agent orchestration (Planner/Coder/Tester/Reviewer) with a
      real retry feedback loop
- [x] Phase 4: Real tool-calling (sandboxed filesystem + shell), workflow run
      history/observability, pluggable real LLM provider (Anthropic)
- [ ] Phase 5: Distributed execution, plugin marketplace, workflow builder UI

## License

TBD