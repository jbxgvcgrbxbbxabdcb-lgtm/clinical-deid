# Clinical De-identify · Backend

FastAPI API only. Frontend is served separately (Vite in dev, nginx in prod).

## Layers

| Layer | Path | Role |
| --- | --- | --- |
| Routers | `routers/` | HTTP routes, parse request, map errors → JSON |
| Service | `services/` | Detect / refresh / apply |
| De-id + Store | `deid/`, `store/` | openmed ops, rules, in-memory sessions |

## Run

```bash
source .venv/bin/activate
uv pip install -e .
uvicorn backend.app:app --host 127.0.0.1 --port 7870
```

- API: http://127.0.0.1:7870 `/api/*`
- Dev UI: `cd frontend && npm run dev` on :5173
