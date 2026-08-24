# Clinical De-identify · Deploy

Backend API image only. Serve `frontend/dist` with nginx and proxy `/api` here.

## Quick start

```bash
# from repository root
docker compose -f deploy/docker-compose.yml up --build
# → http://127.0.0.1:7870  (API)
```

Frontend (dev): `cd frontend && npm run dev` → http://localhost:5173/ (proxies `/api` → `:7870`).

## Model cache

First detect loads `OpenMed/OpenMed-PII-SuperClinical-Small-44M-v1` (~550MB).

| Situation | What happens |
| --- | --- |
| `~/.cache/openmed` already has the model | Container starts in **offline** mode and uses the host cache |
| Cache empty + Docker can reach Hugging Face | First request **downloads** into `~/.cache/openmed` (persisted via bind mount) |
| Cache empty + Hub unreachable from Docker | Pre-seed on the host, then restart (see below) |

Pre-seed on the host (when Docker cannot reach the Hub):

```bash
# needs: pip install huggingface_hub
hf download OpenMed/OpenMed-PII-SuperClinical-Small-44M-v1 \
  --cache-dir ~/.cache/openmed
```

> The container mounts `~/.cache/openmed` to `/app/.cache/openmed` and sets
> `HF_HOME` **and** `HF_HUB_CACHE` to that directory, so the `--cache-dir`
> layout above is picked up directly. If your cache already exists but the
> container reports "couldn't find them in the cached files", make sure the
> bind mount target matches `HF_HUB_CACHE`.

Optional: set `HF_TOKEN` in the environment (or a `.env` next to the compose file) for higher Hub rate limits.

Startup logs indicate the mode:

- `openmed: local model cache found — offline mode`
- `openmed: no local model cache — first detect will download from Hugging Face`

| File | Role |
| --- | --- |
| `Dockerfile` | Install Python deps + `openmed`; non-root user; run uvicorn |
| `entrypoint.sh` | Offline if cache present, otherwise allow Hub download |
| `docker-compose.yml` | API on `127.0.0.1:7870`, bind-mounts `~/.cache/openmed` → `/app/.cache/openmed` |
| `../.dockerignore` | At repo root (compose build context); excludes `frontend/` and caches |

Example nginx snippet:

```nginx
server {
  listen 80;
  root /var/www/clinical-deid;   # frontend/dist contents
  index index.html;

  location /api/ {
    proxy_pass http://127.0.0.1:7870;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  }

  location / {
    try_files $uri $uri/ /index.html;
  }
}
```
