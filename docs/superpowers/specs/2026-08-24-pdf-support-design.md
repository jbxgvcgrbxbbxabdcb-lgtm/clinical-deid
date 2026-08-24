# PDF（非扫描件）脱敏支持 — 设计文档

日期：2026-08-24
状态：已批准（用户确认黑框+删文本层、前后端全链路、输出后跑 fidelity 校验、扫描件本期仅报错预留）

## 背景与目标

现有临床去标识工具仅支持 `.docx` / `.md` / 粘贴文本，检测→审查→批准→下载四步流。
本期为 **非扫描件 PDF** 增加同等能力：上传 PDF → 提取文本并检测 PII → 审查勾选 → 产出去标识 PDF 下载。

明确不在本期范围：扫描件（图片型、无文本层 PDF）。对这类输入返回明确报错提示，接口预留。

## 现状调研结论

- 依赖 `openmed>=2.0` 已内置完整非扫描 PDF 读取侧能力：
  - `openmed.multimodal.extract_pdf`（pdfplumber 提取文本 + 每词 SourceSpan，含 page/bbox）
  - `openmed.multimodal.project_text_spans`（检测到的字符 span → (page, bbox) 矩形，自动处理跨行）
  - `openmed.multimodal.verify_redacted_pdf`（fidelity 校验：文本层泄漏 + 是否真的画了框）
- 写回层（画黑框 + 物理删除文本层）在现有依赖中无高层 API：
  - `pikepdf 10.10.0` 无 `Redactor` / `add_redaction`（需手撕 content stream，风险高）
  - 因此新增 `pymupdf` 作为写回层：`page.add_redact_annot(rect)` + `page.apply_redactions()` 一步完成"盖黑框 + 删除文本层"
- **关键 spike 验证结论（2026-08-24 实测）**：
  - PyMuPDF redaction 画的是内容流 `re f` 填充路径；pdfplumber（pdfminer.six 内核）把它解析为 `curve`/`char`，不会落入 `rects` 数组 → openmed 的 `verify_redacted_pdf` 对 PyMuPDF 写回输出会误报 "no visible box"
  - 该问题不会影响实际脱敏正确性：像素级验证 redaction 后区域 100% 黑色覆盖、文本层已物理删除
  - 因此自建基于 PyMuPDF 的轻量 verifier：`page.get_text("words", clip=rect)` 检查文本层残留 + 区域像素 diff 检查视觉变更（两者都已实测通过），不再依赖 pdfplumber rects 解析
- 扫描件 OCR 链路（`openmed.multimodal.ocr` + `redact_image`）存在但当前零 OCR 后端安装，中文还需额外模型，本期不做。

## 架构

沿用现有 DOCX 流程同构扩展，无独立新页面：

```text
上传 PDF → extract_pdf（文本+span）→ deidentify（entities）→ project_text_spans（(page,bbox)）
                                                                      │
        SelectiveRedactionView ← _verify_pdf_fidelity（PyMuPDF verifier） ← write_redacted_pdf（PyMuPDF）
                                                                      │
                                                    download（store.put_download 现有逻辑）
```

## 模块改动

### 1. `backend/deid/ops.py` 新增

- `run_pdf_review(upload_path, method, custom_recognizer, surrogate_vault) -> ReviewView`
  - 后缀校验 `.pdf`
  - `extract_pdf` → 若提取文本为空/无词 → 视为扫描件，报错
  - 复用 `run_review(text, ...)`
- `apply_selected_pdf_redaction(upload_path, method, selected_spans, ...) -> SelectiveRedactionView`
  - 前缀校验 `.pdf`
  - 先通过 `apply_selected_redaction` 拿到 `applied_entities`
  - `extract_pdf` → `project_text_spans(doc, applied_entities)` → 矩形列表
  - 空矩形跳过；无任何矩形 → 原样拷贝源文件
  - `_write_redacted_pdf(source, output_path, rectangles)`
  - 产出后 `_verify_pdf_fidelity(source, output_path, rectangles)`（自建 PyMuPDF verifier），结果写入视图
- `_write_redacted_pdf`：内部懒加载 `pymupdf`；按页分组矩形；每矩形
  `page.add_redact_annot(rect, fill=(0,0,0), cross_out=False)`，全部 add 后再统一 `apply_redactions()`；
  `doc.save` 到输出路径
- `_verify_pdf_fidelity`：自建轻量 verifier，逻辑与 openmed `verify_redacted_pdf` 一致但不依赖
  pdfplumber rects 解析：
  - 对每个区域：`page.get_text("words", clip=rect)` 检查文本层残留
  - 区域像素 diff（渲染 150dpi crop 对比原/脱敏）确认视觉变更
  - 产出 `passed` / 各区域明细，写入 `SelectiveRedactionView.fidelity`

### 2. `backend/deid/constants.py`

- 新增 `PDF_SCANNED_HINT`：未检测到可提取文本层时的明确报错（提示可能是扫描件，本期不支持）

### 3. `backend/services/review.py`

- `detect_pdf(*, file_bytes, filename, method, force_terms, protect_terms)`
  - 与 `detect_docx` 同构；session `kind="pdf"`、扩展名校验
  - 复用异常包装（PDF/扫描件/依赖错误 → 追加 hint）
- `apply_redaction`：`session["kind"] == "pdf"` 分支 → `apply_selected_pdf_redaction`
- 响应 `session_kind` 反映 `"pdf"`；`fidelity` 字段透出校验结果

### 4. `backend/routers/review.py`

- 新增 `POST /api/detect/pdf`（`UploadFile` + Form，与 `/api/detect/docx` 同构）

### 5. `pyproject.toml`

- dependencies 追加 `pymupdf`（写回层核心，最新版）

### 6. 前端（最小改动）

- `frontend/src/constants.ts`：`ALLOWED_EXTS` 增加 `"pdf"`
- `frontend/src/lib/review.ts`：`fileKind` 增加 `PDF`；`redactedDownloadName` 支持 `.pdf` 产出 `_redacted.pdf`
- `frontend/src/api/client.ts`：新增 `detectPdf`（同 `detectDocx`）
- `frontend/src/hooks/useDeidFlow.ts`：`runDetectFile` 增加 PDF 分支；`acceptFile` 文案更新
- `frontend/src/components/StageUpload.tsx`：上传区文案/accept 属性加 `.pdf`
- 完成页（`useDeidFlow.handleApply`）：收到 `fidelity` 字段时展示校验结果；失败则警告并阻止下载（fail-closed）

## 数据流与错误处理

| 场景 | 处理 |
|---|---|
| 非 `.pdf` 后缀 | 400，与 docx 一致 |
| 扫描件 / 空文本层 | 400 + `PDF_SCANNED_HINT` |
| 单页无词 / 跨页实体 / 空矩形 | 跳过，不中断 |
| fidelity 校验失败 | 响应 `fidelity.passed=false` + 区域明细，前端警告 + 阻止下载 |
| 下载过期 | 现有 `store.get_download` 404 逻辑 |

## 测试计划

- 后端单元测试：`run_pdf_review` / `apply_selected_pdf_redaction`（含空文本层报错、跨行实体、空选择、fidelity 失败路径）
- 端到端验证：用真实合成 PDF（文本层）跑通全链路，检查输出 PDF 文本层确实删除、黑框覆盖正确
- 前端：上传 PDF → 检测 → 审查 → 下载

## 依赖与风险

- 新增 `pymupdf`：与 pdfplumber 职责正交，无版本冲突
- 自建 `_verify_pdf_fidelity` 为 fail-closed 校验：任何未覆盖区域都会拦下下载，避免文本层泄漏
- **verifier 不依赖 pdfplumber rects 解析**：改用 PyMuPDF `get_text("words", clip=)` + 区域像素 diff（实测通过），从根因避免与 openmed 的 pdfplumber 内核误判冲突