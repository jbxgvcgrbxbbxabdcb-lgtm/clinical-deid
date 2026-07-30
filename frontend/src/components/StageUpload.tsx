import { useRef, useState, type DragEvent, type KeyboardEvent } from "react";
import { fileKind } from "@/lib/review";
import type { InputMode } from "@/types";

interface StageUploadProps {
  inputMode: InputMode;
  uploadedName: string | null;
  pasteText: string;
  busy: boolean;
  onInputMode: (mode: InputMode) => void;
  onAcceptFile: (file: File) => void;
  onPasteText: (text: string) => void;
  onDetect: () => void;
  onSample: () => void;
}

export function StageUpload({
  inputMode,
  uploadedName,
  pasteText,
  busy,
  onInputMode,
  onAcceptFile,
  onPasteText,
  onDetect,
  onSample,
}: StageUploadProps) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const canScan =
    inputMode === "paste" ? Boolean(pasteText.trim()) : Boolean(uploadedName);

  function openPicker() {
    fileRef.current?.click();
  }

  function onKeyDown(e: KeyboardEvent<HTMLDivElement>) {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      openPicker();
    }
  }

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files?.[0];
    if (f) onAcceptFile(f);
  }

  return (
    <section className="panel stage" id="stage-upload">
      <div className="panel-head">
        <h2>Input</h2>
        <span className="panel-meta">
          {inputMode === "paste" ? "Paste text" : ".docx · .md · paste"}
        </span>
      </div>
      <div className="panel-body">
        <div className="input-tabs" role="tablist" aria-label="Input method">
          <button
            type="button"
            className={`input-tab${inputMode === "file" ? " active" : ""}`}
            role="tab"
            aria-selected={inputMode === "file"}
            onClick={() => onInputMode("file")}
          >
            File upload
          </button>
          <button
            type="button"
            className={`input-tab${inputMode === "paste" ? " active" : ""}`}
            role="tab"
            aria-selected={inputMode === "paste"}
            onClick={() => onInputMode("paste")}
          >
            Paste text
          </button>
        </div>

        {inputMode === "file" ? (
          <div className="input-pane" role="tabpanel">
            <div
              className={`dropzone${dragging ? " drag" : ""}`}
              tabIndex={0}
              role="button"
              aria-label="Upload .docx or .md file"
              onClick={openPicker}
              onKeyDown={onKeyDown}
              onDragEnter={(e) => {
                e.preventDefault();
                setDragging(true);
              }}
              onDragOver={(e) => {
                e.preventDefault();
                setDragging(true);
              }}
              onDragLeave={(e) => {
                e.preventDefault();
                setDragging(false);
              }}
              onDrop={onDrop}
            >
              <div className="icon-wrap">
                <svg
                  width="26"
                  height="26"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.8"
                >
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <path d="M14 2v6h6M12 18v-6M9 15l3-3 3 3" />
                </svg>
              </div>
              <strong>Drop a .docx or .md here</strong>
              <p>or click to browse — Word and Markdown notes</p>
              <div className="accept-row" aria-hidden="true">
                <span>.docx</span>
                <span>.md</span>
              </div>
            </div>
            {uploadedName ? (
              <div className="file-chip show">
                <span className="dot" />
                <span>{uploadedName}</span>
                <span className="kind">{fileKind(uploadedName)}</span>
              </div>
            ) : null}
            <input
              ref={fileRef}
              type="file"
              accept=".docx,.md,text/markdown,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              hidden
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) onAcceptFile(f);
                e.target.value = "";
              }}
            />
          </div>
        ) : (
          <div className="input-pane" role="tabpanel">
            <div className="paste-box">
              <label className="sr-only" htmlFor="text-input">
                Clinical note text
              </label>
              <textarea
                id="text-input"
                placeholder="Paste a synthetic clinical note here…"
                value={pasteText}
                onChange={(e) => onPasteText(e.target.value)}
              />
              <p className="paste-hint">
                Plain text or Markdown content — no file required.
              </p>
            </div>
          </div>
        )}

        <div className="upload-actions">
          <button
            type="button"
            className={`btn-primary${busy ? " busy" : ""}`}
            disabled={!canScan || busy}
            onClick={onDetect}
          >
            {busy ? "Detecting…" : "Detect entities"}
          </button>
          <button
            type="button"
            className="btn-ghost"
            disabled={busy}
            onClick={onSample}
          >
            Use sample discharge note
          </button>
        </div>
      </div>
    </section>
  );
}
