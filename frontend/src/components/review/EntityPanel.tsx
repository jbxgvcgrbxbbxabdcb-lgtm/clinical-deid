import { useMemo } from "react";
import type { RefObject } from "react";
import { confClass, replacementPreview } from "@/lib/review";
import type { Entity, Method } from "@/types";

interface EntityPanelProps {
  entities: Entity[];
  selected: Set<string>;
  activeId: string | null;
  confMin: number;
  highConf: number;
  method: Method;
  selectAccent: string | null;
  listRef: RefObject<HTMLDivElement | null>;
  onConfMin: (value: number) => void;
  onToggle: (id: string) => void;
  onActivate: (id: string) => void;
  onReplacement: (id: string, value: string) => void;
  onSelectVisible: () => void;
  onSelectAll: () => void;
  onSelectNone: () => void;
}

export function EntityPanel({
  entities,
  selected,
  activeId,
  confMin,
  highConf,
  method,
  selectAccent,
  listRef,
  onConfMin,
  onToggle,
  onActivate,
  onReplacement,
  onSelectVisible,
  onSelectAll,
  onSelectNone,
}: EntityPanelProps) {
  const visible = useMemo(
    () => entities.filter((e) => Number(e.confidence) >= confMin),
    [entities, confMin],
  );

  const sortedVisible = useMemo(
    () =>
      [...visible].sort(
        (a, b) => Number(b.confidence) - Number(a.confidence),
      ),
    [visible],
  );

  return (
    <>
      <div className="entity-toolbar">
        <h3>Detected entities</h3>
        <div className="toolbar-actions" id="select-actions">
          <button
            type="button"
            className={`btn-sm${selectAccent === "visible" ? " accent" : ""}`}
            onClick={onSelectVisible}
          >
            Select visible
          </button>
          <button
            type="button"
            className={`btn-sm${selectAccent === "all" ? " accent" : ""}`}
            onClick={onSelectAll}
          >
            All
          </button>
          <button
            type="button"
            className={`btn-sm${selectAccent === "none" ? " accent" : ""}`}
            onClick={onSelectNone}
          >
            None
          </button>
        </div>
      </div>

      <div className="conf-filter">
        <div className="row">
          <label htmlFor="conf-slider">Confidence filter</label>
          <span className="val">≥ {confMin.toFixed(2)}</span>
        </div>
        <input
          type="range"
          id="conf-slider"
          min={50}
          max={99}
          value={Math.round(confMin * 100)}
          step={1}
          onChange={(e) => onConfMin(Number(e.target.value) / 100)}
        />
        <p className="sub">
          Showing {visible.length} / {entities.length} · ≥ threshold selected ·
          below dimmed in doc, hidden in list · edit → to customize
          replacement
        </p>
      </div>

      <div className="entity-list" role="list" ref={listRef}>
        {sortedVisible.length === 0 ? (
          <div
            style={{
              padding: "1rem",
              color: "var(--muted)",
              fontSize: "0.88rem",
            }}
          >
            No entities above this confidence.
          </div>
        ) : (
          sortedVisible.map((e) => {
            const checked = selected.has(e.id);
            const preview = replacementPreview(e, method);
            return (
              <div
                key={e.id}
                className={[
                  "entity-row",
                  checked ? "selected" : "",
                  activeId === e.id ? "active" : "",
                ]
                  .filter(Boolean)
                  .join(" ")}
                data-id={e.id}
                role="listitem"
                onClick={() => onActivate(e.id)}
              >
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={(ev) => {
                    ev.stopPropagation();
                    onToggle(e.id);
                  }}
                  onClick={(ev) => ev.stopPropagation()}
                />
                <div className="entity-main">
                  <div className="entity-text">{e.text}</div>
                  <div className="entity-meta">
                    <span className="tag">{e.label}</span>
                    <span
                      className={`conf ${confClass(Number(e.confidence), highConf)}`}
                    >
                      {(Number(e.confidence) * 100).toFixed(0)}% confidence
                    </span>
                    <span>
                      {e.start}–{e.end}
                    </span>
                  </div>
                </div>
                <div
                  className="preview-arrow"
                  onClick={(ev) => ev.stopPropagation()}
                >
                  <span className="preview-label" aria-hidden="true">
                    →
                  </span>
                  <input
                    type="text"
                    className="replacement-input"
                    value={e.replacement ?? preview}
                    placeholder={
                      method === "remove" ? "(empty)" : `[${e.label || "PII"}]`
                    }
                    aria-label={`Replacement for ${e.text}`}
                    onChange={(ev) => onReplacement(e.id, ev.target.value)}
                    onFocus={() => onActivate(e.id)}
                  />
                </div>
              </div>
            );
          })
        )}
      </div>
    </>
  );
}
