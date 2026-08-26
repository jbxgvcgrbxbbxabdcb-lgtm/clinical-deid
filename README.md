# Clinical De-identify（临床去标识）

本地优先的临床笔记去标识工具：React 前端 + FastAPI 后端，底层使用
[`openmed`](https://pypi.org/project/openmed/)（从 PyPI 安装）。

支持输入：粘贴文本 / Markdown / Word（`.docx`）/ **PDF（非扫描件，需文本层）**。
PDF 输出以黑色遮罩覆盖并物理移除文本层中的 PHI，并附 fidelity 泄漏校验。

| 格式 | 支持 | 说明 |
| --- | --- | --- |
| 粘贴文本 / Markdown | ✅ | |
| Word（`.docx`） | ✅ | 含页眉页脚、表格；**文本框**经 OOXML 补扫可检测并写回 |
| PDF（有文本层） | ✅ | 黑框 + 文本层移除 + fidelity 校验 |
| PDF（扫描件 / 纯图片） | ❌ | 无 OCR；上传后会提示需文本层 |
| 中文文档 | ⚠️ | 模型仅支持英文文件脱敏；中文主要靠系统规则与自定义（必脱敏） |

**仅用于合成数据 — 请勿上传真实 PHI（受保护健康信息）。**

## 目录结构

```text
frontend/   Vite + React 界面（开发时 :5173）
backend/    FastAPI API（:7870）
deploy/     Docker 镜像与 compose 配置
```

## 本地启动

需要 Python ≥ 3.10、Node.js（前端）。

### 1. 后端

在仓库根目录：

```bash
python3 -m venv .venv
source .venv/bin/activate
uv pip install -e ".[dev]"

uvicorn backend.app:app --host 127.0.0.1 --port 7870
# → http://127.0.0.1:7870  （仅 API；前端用 Vite 或 nginx）
```

依赖为精简版：`openmed[hf]` + `pdfplumber` / `python-docx` / `pymupdf`（无 OCR 栈）。
模型权重在首次 detect 时下载到 `~/.cache/openmed`（约 550MB），不在 `.venv` 里。

### 2. 前端（另开终端）

```bash
cd frontend && npm install && npm run dev
# → http://127.0.0.1:5173  （/api 代理到 :7870）
```

## Docker 部署

镜像**只跑后端 API**。前端自行 `npm run build` 后用 nginx（或其它反向代理）托管静态资源，并把 `/api` 反代到容器的 `7870`。

```bash
docker compose -f deploy/docker-compose.yml up --build
# → http://127.0.0.1:7870  （仅 API，默认只绑定本机）
# 更新代码后需 --build 重建镜像（依赖或 Dockerfile 变更时尤其如此）
```

首次 detect 会加载 `OpenMed/OpenMed-PII-SuperClinical-Small-44M-v1`（约 550MB）。模型缓存挂载到宿主机 `~/.cache/openmed`；若 Docker 访问不了 Hugging Face，可先在宿主机预下载：

```bash
hf download OpenMed/OpenMed-PII-SuperClinical-Small-44M-v1 \
  --cache-dir ~/.cache/openmed
```

可选环境变量 `HF_TOKEN`（提高 Hub 限流额度）：

```bash
HF_TOKEN=hf_xxx docker compose -f deploy/docker-compose.yml up --build
```

后台运行 / 停止：

```bash
docker compose -f deploy/docker-compose.yml up --build -d
docker compose -f deploy/docker-compose.yml down
```

更细的缓存与 nginx 说明见 [`deploy/README.md`](deploy/README.md)。

## 许可证

Apache-2.0。上游依赖 `openmed` 也为独立的 Apache-2.0 许可。
