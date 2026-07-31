# AI Agent Framework

A production-style, multi-agent developer platform: a system of cooperating agents
(planner, coder, tester, debugger, reviewer) that can understand a codebase, plan
changes, write and test code, and report back — with pluggable LLM providers, tool
calling, and persistent memory.

## Why this project

Most "AI agent" repos are thin wrappers around a single chat completion call. This
one is built like a real backend service: typed API, auth, a database-backed memory
layer, provider abstraction (swap OpenAI/Anthropic/Gemini/Ollama without touching
business logic), and a workflow engine that chains agents together with a feedback
loop instead of running them in isolation.

## Architecture

```
User -> API Gateway -> Planner Agent -> Coding Agent -> Test Agent -> Review Agent
                              |               |
                          Memory Agent   Knowledge Base
```

## Status

Early development — see [Roadmap](#roadmap) below. This README is updated as each
phase lands.

## Tech stack

- Backend: Python, FastAPI
- LLM providers: OpenAI SDK, Anthropic SDK, Ollama (local), pluggable via a common
  provider interface
- Memory: PostgreSQL + pgvector for long-term/semantic memory, Redis for
  short-term/session state
- Auth: JWT-based, role-based access control
- Infra: Docker, GitHub Actions CI (Kubernetes manifests later)

## Project layout

```
backend/
  app/
    main.py          # FastAPI app entrypoint
    core/            # settings, config
    api/routes/       # HTTP route handlers
    agents/           # agent base class + implementations
    tools/            # tool-calling interfaces (git, bash, fs, http, ...)
    models/           # pydantic / ORM models
    db/               # database session + migrations
  tests/
```

## Getting started

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env   # fill in provider keys
uvicorn app.main:app --reload
```

## Roadmap

- [x] Repo scaffold, FastAPI skeleton
- [ ] Phase 1: Auth (JWT), basic chat endpoint, single tool call
- [ ] Phase 2: Planner + Coding agent, persistent memory
- [ ] Phase 3: Multi-agent orchestration, retrieval / document indexing
- [ ] Phase 4: Distributed execution, monitoring/observability
- [ ] Phase 5: Plugin marketplace, workflow builder UI

## License

TBD
