import type { Entity, Method } from "@/types";

export type DocMark =
  | { type: "text"; value: string }
  | { type: "mark"; entity: Entity };

export function buildDocumentMarks(
  sourceText: string,
  entities: Entity[],
): DocMark[] {
  const ordered = [...entities].sort(
    (a, b) => a.start - b.start || b.end - a.end,
  );
  const parts: DocMark[] = [];
  let cursor = 0;
  for (const e of ordered) {
    if (e.start < cursor) continue;
    if (e.start > cursor) {
      parts.push({ type: "text", value: sourceText.slice(cursor, e.start) });
    }
    parts.push({ type: "mark", entity: e });
    cursor = e.end;
  }
  if (cursor < sourceText.length) {
    parts.push({ type: "text", value: sourceText.slice(cursor) });
  }
  return parts;
}

export function confClass(confidence: number, highConf: number): string {
  if (confidence >= highConf) return "high";
  if (confidence >= 0.8) return "mid";
  return "low";
}

export function selectByConfidence(
  min: number,
  pool: Entity[],
): Set<string> {
  return new Set(
    pool.filter((e) => Number(e.confidence) >= min).map((e) => e.id),
  );
}

export function preserveSelectionBySpans(
  prevEntities: Entity[],
  prevSelected: Set<string>,
  nextEntities: Entity[],
  confMin: number,
): Set<string> {
  const prev = new Map(
    prevEntities.map((e) => [`${e.start}:${e.end}`, prevSelected.has(e.id)]),
  );
  const nextSelected = new Set<string>();
  for (const e of nextEntities) {
    const key = `${e.start}:${e.end}`;
    if (prev.has(key)) {
      if (prev.get(key)) nextSelected.add(e.id);
    } else if (Number(e.confidence) >= confMin) {
      nextSelected.add(e.id);
    }
  }
  return nextSelected;
}

export function fileKind(name: string): string {
  const ext = name.includes(".") ? name.split(".").pop()!.toLowerCase() : "";
  if (ext === "md" || ext === "markdown") return "MD";
  if (ext === "docx") return "DOCX";
  return (ext || "FILE").toUpperCase();
}

export function fileExt(name: string): string {
  return name.includes(".") ? name.split(".").pop()!.toLowerCase() : "";
}

export function redactedDownloadName(sourceName: string): {
  stem: string;
  textExt: ".md" | ".txt";
} {
  const stem = sourceName.replace(/\.(docx|md|markdown|txt)$/i, "");
  const textExt = /\.(md|markdown)$/i.test(sourceName) ? ".md" : ".txt";
  return { stem, textExt };
}

export function replacementPreview(entity: Entity, method: Method): string {
  if (entity.replacement != null && entity.replacement !== "") {
    return entity.replacement;
  }
  return method === "remove" ? "(empty)" : `[${entity.label || "PII"}]`;
}
