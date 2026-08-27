import type { ApplyPayload, Method, ReviewPayload } from "@/types";

async function readJson<T>(res: Response): Promise<T> {
  const raw = await res.text();
  if (!raw.trim()) {
    throw new Error(
      res.ok
        ? "Server closed the connection with an empty response (often OOM on large PDFs). Check Docker memory (≥ 8 GB) and container logs for exit 137."
        : `Request failed (${res.status}) with an empty response.`,
    );
  }
  let data: T & { error?: string; status?: string };
  try {
    data = JSON.parse(raw) as T & { error?: string; status?: string };
  } catch {
    throw new Error(
      `Server returned non-JSON (${res.status}). The API may have crashed mid-request — check Docker logs (exit 137 = out of memory).`,
    );
  }
  if (!res.ok) {
    throw new Error(
      data.error || data.status || `Request failed (${res.status})`,
    );
  }
  return data;
}

export async function fetchSampleText(): Promise<string | null> {
  try {
    const res = await fetch("/api/sample");
    if (!res.ok) return null;
    const data = (await res.json()) as { text?: string };
    return data.text || null;
  } catch {
    return null;
  }
}

export async function detectText(opts: {
  text: string;
  method: Method;
  filename?: string;
  force_terms: string[];
  protect_terms: string[];
}): Promise<ReviewPayload> {
  const res = await fetch("/api/detect/text", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      text: opts.text,
      method: opts.method,
      filename: opts.filename || "pasted_note.txt",
      force_terms: opts.force_terms,
      protect_terms: opts.protect_terms,
    }),
  });
  return readJson<ReviewPayload>(res);
}

export async function detectDocx(opts: {
  file: File;
  method: Method;
  force_terms: string[];
  protect_terms: string[];
}): Promise<ReviewPayload> {
  const form = new FormData();
  form.append("file", opts.file, opts.file.name);
  form.append("method", opts.method);
  form.append("force_terms", JSON.stringify(opts.force_terms));
  form.append("protect_terms", JSON.stringify(opts.protect_terms));
  const res = await fetch("/api/detect/docx", { method: "POST", body: form });
  return readJson<ReviewPayload>(res);
}

export async function detectPdf(opts: {
  file: File;
  method: Method;
  force_terms: string[];
  protect_terms: string[];
}): Promise<ReviewPayload> {
  const form = new FormData();
  form.append("file", opts.file, opts.file.name);
  form.append("method", opts.method);
  form.append("force_terms", JSON.stringify(opts.force_terms));
  form.append("protect_terms", JSON.stringify(opts.protect_terms));
  const res = await fetch("/api/detect/pdf", { method: "POST", body: form });
  return readJson<ReviewPayload>(res);
}

export async function refreshReview(opts: {
  session_id: string;
  method: Method;
  force_terms: string[];
  protect_terms: string[];
}): Promise<ReviewPayload> {
  const res = await fetch("/api/review/refresh", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(opts),
  });
  return readJson<ReviewPayload>(res);
}

export async function applyRedaction(opts: {
  session_id: string;
  method: Method;
  selected_spans: Array<Record<string, unknown>>;
  force_terms: string[];
  protect_terms: string[];
}): Promise<ApplyPayload> {
  const res = await fetch("/api/apply", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(opts),
  });
  return readJson<ApplyPayload>(res);
}
