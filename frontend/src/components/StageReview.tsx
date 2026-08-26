import { useEffect, useMemo, useRef } from "react";
import { LimitationsCallout } from "@/components/LimitationsCallout";
import { DocPreview } from "@/components/review/DocPreview";
import { EntityPanel } from "@/components/review/EntityPanel";
import { MethodBlock } from "@/components/review/MethodBlock";
import { RulesDock } from "@/components/review/RulesDock";
import type { Entity, Method } from "@/types";

interface StageReviewProps {
  sourceText: string;
  entities: Entity[];
  selected: Set<string>;
  activeId: string | null;
  confMin: number;
  highConf: number;
  method: Method;
  uploadedName: string | null;
  forceTerms: string[];
  protectTerms: string[];
  selectAccent: string | null;
  busy: boolean;
  busyRefresh: boolean;
  onConfMin: (value: number) => void;
  onMethod: (method: Method) => void;
  onToggle: (id: string) => void;
  onActivate: (id: string) => void;
  onReplacement: (id: string, value: string) => void;
  onSelectVisible: () => void;
  onSelectAll: () => void;
  onSelectNone: () => void;
  onAddForce: (term: string) => void;
  onClearForce: () => void;
  onRemoveForce: (idx: number) => void;
  onAddProtect: (term: string) => void;
  onClearProtect: () => void;
  onRemoveProtect: (idx: number) => void;
  onBack: () => void;
  onApply: () => void;
}

export function StageReview({
  sourceText,
  entities,
  selected,
  activeId,
  confMin,
  highConf,
  method,
  uploadedName,
  forceTerms,
  protectTerms,
  selectAccent,
  busy,
  busyRefresh,
  onConfMin,
  onMethod,
  onToggle,
  onActivate,
  onReplacement,
  onSelectVisible,
  onSelectAll,
  onSelectNone,
  onAddForce,
  onClearForce,
  onRemoveForce,
  onAddProtect,
  onClearProtect,
  onRemoveProtect,
  onBack,
  onApply,
}: StageReviewProps) {
  const listRef = useRef<HTMLDivElement>(null);
  const previewRef = useRef<HTMLDivElement>(null);
  const blocked = busy || busyRefresh;

  const visibleCount = useMemo(
    () => entities.filter((e) => Number(e.confidence) >= confMin).length,
    [entities, confMin],
  );

  useEffect(() => {
    if (!activeId) return;
    const row = listRef.current?.querySelector(
      `.entity-row[data-id="${activeId}"]`,
    );
    row?.scrollIntoView({ block: "nearest", behavior: "smooth" });
    const mark = previewRef.current?.querySelector(
      `mark[data-id="${activeId}"]`,
    );
    mark?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [activeId]);

  let summary = (
    <>
      <strong>{selected.size}</strong> of {entities.length} selected ·{" "}
      {visibleCount} visible
    </>
  );
  if (method === "replace" || method === "format_preserve") {
    summary = (
      <>
        {summary} · consistent fake names
      </>
    );
  }

  return (
    <section className="panel stage" id="stage-review">
      <div className="panel-head">
        <h2>Redaction preview</h2>
        <span className="panel-meta">
          {visibleCount} visible / {entities.length} · {uploadedName || "note"}
        </span>
      </div>
      <div className="panel-body">
        <LimitationsCallout />
        {busyRefresh ? (
          <p className="refresh-banner" role="status">
            正在按新规则 / 方法重新检测，请稍候…
          </p>
        ) : null}
        <div className={`review-grid${busyRefresh ? " is-refreshing" : ""}`}>
          <DocPreview
            sourceText={sourceText}
            entities={entities}
            selected={selected}
            activeId={activeId}
            confMin={confMin}
            onToggle={onToggle}
            previewRef={previewRef}
          />

          <div>
            <EntityPanel
              entities={entities}
              selected={selected}
              activeId={activeId}
              confMin={confMin}
              highConf={highConf}
              method={method}
              selectAccent={selectAccent}
              listRef={listRef}
              onConfMin={onConfMin}
              onToggle={onToggle}
              onActivate={onActivate}
              onReplacement={onReplacement}
              onSelectVisible={onSelectVisible}
              onSelectAll={onSelectAll}
              onSelectNone={onSelectNone}
            />
            <MethodBlock method={method} onMethod={onMethod} />
            <RulesDock
              forceTerms={forceTerms}
              protectTerms={protectTerms}
              onAddForce={onAddForce}
              onClearForce={onClearForce}
              onRemoveForce={onRemoveForce}
              onAddProtect={onAddProtect}
              onClearProtect={onClearProtect}
              onRemoveProtect={onRemoveProtect}
            />
          </div>
        </div>

        <div className="summary-bar">
          <p>{summary}</p>
          <div style={{ display: "flex", gap: "0.6rem", flexWrap: "wrap" }}>
            <button type="button" className="btn-ghost" onClick={onBack}>
              Back
            </button>
            <button
              type="button"
              className={`btn-primary${blocked ? " busy" : ""}`}
              disabled={blocked}
              onClick={onApply}
            >
              {busy
                ? "Redacting…"
                : busyRefresh
                  ? "重新检测中…"
                  : "Apply redaction"}
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
