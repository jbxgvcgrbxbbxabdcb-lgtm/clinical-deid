# Clinical De-identify · React frontend

Vite + React + TypeScript. Talks to `backend/` via `/api`.

## Layout

```text
src/
  api/           HTTP client
  components/    UI (review/ for step-2 subviews)
  hooks/         Theme + de-id workflow state
  lib/           Pure helpers
  styles/        Global CSS
  App.tsx        Page composition
  main.tsx       Entry
```

Imports use the `@/` alias (`src/`).

## Prerequisites

```bash
# repo root
source .venv/bin/activate
uvicorn backend.app:app --host 127.0.0.1 --port 7870
```

## Dev

```bash
cd frontend
npm install
npm run dev         # :5173, proxies /api → :7870
```

## Production build

Build static assets for nginx (or any static host). The Docker image does **not**
bundle the frontend — reverse-proxy `/api` to the backend on `:7870`.

```bash
npm run build
# → frontend/dist
```
