# Clinical De-identify · Deploy

Backend API image only. Serve `frontend/dist` with nginx and proxy `/api` here.

```bash
# from repository root
docker compose -f deploy/docker-compose.yml up --build
# → http://127.0.0.1:7870  (API)
```

| File | Role |
| --- | --- |
| `Dockerfile` | Install Python deps + `openmed`; run uvicorn |
| `docker-compose.yml` | Single `app` service on port 7870 |
| `.dockerignore` | Excludes `frontend/` and caches from build context |

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
