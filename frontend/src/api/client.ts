import type { ApplyPayload, Method, ReviewPayload } from "@/types";

async function readJson<T>(res: Response): Promise<T> {
  const data = (await res.json()) as T & { error?: string; status?: string };
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
