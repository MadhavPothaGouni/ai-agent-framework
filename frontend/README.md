# Agent Framework — Frontend

React + TypeScript + Tailwind + Framer Motion UI for the AI Agent Framework backend.

Covers auth (signup/login), chat with persistent session memory, the multi-agent
workflow runner (animated Planner → Coder → Tester → Reviewer pipeline with retry
visualization), and browsable run history.

## Getting started

```bash
npm install
cp .env.example .env   # points at the backend; defaults to http://127.0.0.1:8000
npm run dev
```

Requires the backend running separately (see `../backend/README.md`) with CORS
already configured for `http://localhost:5173`.

## Build

```bash
npm run build   # type-checks with tsc, then builds to dist/
npm run preview # serve the production build locally
```

## Structure

```
src/
  lib/          # API client (axios) + shared TypeScript types
  context/      # AuthContext (JWT stored in localStorage)
  components/   # Layout (sidebar nav + page transitions), AgentPipeline, ProtectedRoute
  pages/        # LoginPage, SignupPage, ChatPage, WorkflowPage, RunHistoryPage
```
