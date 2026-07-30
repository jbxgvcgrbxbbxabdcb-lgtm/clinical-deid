# Clinical De-identify（临床去标识）

本地优先的临床笔记去标识工具：React 前端 + FastAPI 后端，底层使用
[`openmed`](https://pypi.org/project/openmed/)（从 PyPI 安装）。

**仅用于合成数据 — 请勿上传真实 PHI（受保护健康信息）。**

## 目录结构

```text
frontend/   Vite + React 界面（开发时 :5173）
backend/    FastAPI API（:7870）
deploy/     Docker 镜像与 compose 配置
```

## 本地启动

### 1. 后端

在仓库根目录：

```bash
python3 -m venv .venv
source .venv/bin/activate
uv pip install -e ".[dev]"

uvicorn backend.app:app --host 127.0.0.1 --port 7870
# → http://127.0.0.1:7870  （仅 API；前端用 Vite 或 nginx）
```

### 2. 前端（另开终端）

```bash
cd frontend && npm install && npm run dev
# → http://127.0.0.1:5173  （/api 代理到 :7870）
```

## Docker 部署

镜像**只跑后端 API**。前端自行 `npm run build` 后用 nginx（或其它反向代理）托管静态资源，并把 `/api` 反代到容器的 `7870`。

```bash
docker compose -f deploy/docker-compose.yml up --build
# → http://127.0.0.1:7870  （仅 API）
```

可选环境变量 `HF_TOKEN`（拉取 Hugging Face 模型时使用）：

```bash
HF_TOKEN=hf_xxx docker compose -f deploy/docker-compose.yml up --build
```

后台运行 / 停止：

```bash
docker compose -f deploy/docker-compose.yml up --build -d
docker compose -f deploy/docker-compose.yml down
```

## 许可证

Apache-2.0。上游依赖 `openmed` 也为独立的 Apache-2.0 许可。
