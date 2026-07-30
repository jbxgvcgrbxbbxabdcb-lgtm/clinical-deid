import { useMemo } from "react";
import type { RefObject } from "react";
import { buildDocumentMarks } from "@/lib/review";
import type { Entity } from "@/types";

interface DocPreviewProps {
  sourceText: string;
  entities: Entity[];
  selected: Set<string>;
  activeId: string | null;
  confMin: number;
  onToggle: (id: string) => void;
  previewRef: RefObject<HTMLDivElement | null>;
}

export function DocPreview({
  sourceText,
  entities,
  selected,
  activeId,
  confMin,
  onToggle,
  previewRef,
}: DocPreviewProps) {
  const marks = useMemo(
    () => buildDocumentMarks(sourceText, entities),
    [entities, sourceText],
  );

  return (
    <div>
      <div className="legend" aria-hidden="true">
        <span>
          <i style={{ background: "var(--hl-name)" }} /> Name
        </span>
        <span>
          <i style={{ background: "var(--hl-date)" }} /> Date
        </span>
        <span>
          <i style={{ background: "var(--hl-id)" }} /> ID / MRN
        </span>
        <span>
          <i style={{ background: "var(--hl-contact)" }} /> Contact
        </span>
      </div>
      <div
        className="doc-preview"
        ref={previewRef}
        aria-label="Document with highlighted entities"
      >
        {marks.map((part, i) => {
          if (part.type === "text") {
            return <span key={`t-${i}`}>{part.value}</span>;
          }
          const e = part.entity;
          const on = selected.has(e.id);
          const below = Number(e.confidence) < confMin;
          const classes = [
            !on ? "off" : "",
            below ? "dim" : "",
            activeId === e.id ? "focus" : "",
          ]
            .filter(Boolean)
            .join(" ");
          return (
            <mark
              key={e.id}
              data-id={e.id}
              data-kind={e.label}
              className={classes || undefined}
              title={`${e.label} · ${(Number(e.confidence) * 100).toFixed(0)}%`}
              onClick={() => onToggle(e.id)}
            >
              {sourceText.slice(e.start, e.end)}
            </mark>
          );
        })}
      </div>
      <p className="link-hint">Click a highlight or list row to sync selection</p>
    </div>
  );
}
