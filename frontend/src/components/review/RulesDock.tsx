import { useState } from "react";

interface RulesDockProps {
  forceTerms: string[];
  protectTerms: string[];
  onAddForce: (term: string) => void;
  onClearForce: () => void;
  onRemoveForce: (idx: number) => void;
  onAddProtect: (term: string) => void;
  onClearProtect: () => void;
  onRemoveProtect: (idx: number) => void;
}

export function RulesDock({
  forceTerms,
  protectTerms,
  onAddForce,
  onClearForce,
  onRemoveForce,
  onAddProtect,
  onClearProtect,
  onRemoveProtect,
}: RulesDockProps) {
  const [forceIn, setForceIn] = useState("");
  const [protectIn, setProtectIn] = useState("");

  return (
    <details className="rules-dock">
      <summary>
        <span>自定义脱敏规则</span>
        <span className="chev" aria-hidden="true">
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.2"
          >
            <path d="m6 9 6 6 6-6" />
          </svg>
        </span>
      </summary>
      <div className="rules-body">
        <p className="rules-note">
          仅当前会话有效 · 请只用合成词。必脱敏与勿脱敏不能有同一词。
          增删规则后会自动重新检测，通常需等待数秒（模型加载），完成前请勿点「Apply」。
        </p>
        <div className="rules-grid">
          <div className="rule-col force">
            <h4>必脱敏 · Force</h4>
            <div className="term-row">
              <input
                type="text"
                placeholder="必须脱敏…"
                value={forceIn}
                onChange={(e) => setForceIn(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    onAddForce(forceIn);
                    setForceIn("");
                  }
                }}
              />
              <button
                type="button"
                className="btn-sm accent"
                onClick={() => {
                  onAddForce(forceIn);
                  setForceIn("");
                }}
              >
                Add
              </button>
              <button type="button" className="btn-sm" onClick={onClearForce}>
                清空
              </button>
            </div>
            <div className="written">
              {forceTerms.length === 0 ? (
                <span className="empty">(空)</span>
              ) : (
                <ul className="term-list">
                  {forceTerms.map((t, i) => (
                    <li className="term-item" key={`f-${t}-${i}`}>
                      <span className="term-text">{t}</span>
                      <button
                        type="button"
                        className="term-remove"
                        aria-label={`删除 ${t}`}
                        onClick={() => onRemoveForce(i)}
                      >
                        ×
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
          <div className="rule-col protect">
            <h4>勿脱敏 · Protect</h4>
            <div className="term-row">
              <input
                type="text"
                placeholder="不要脱敏…"
                value={protectIn}
                onChange={(e) => setProtectIn(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    onAddProtect(protectIn);
                    setProtectIn("");
                  }
                }}
              />
              <button
                type="button"
                className="btn-sm accent"
                onClick={() => {
                  onAddProtect(protectIn);
                  setProtectIn("");
                }}
              >
                Add
              </button>
              <button type="button" className="btn-sm" onClick={onClearProtect}>
                清空
              </button>
            </div>
            <div className="written">
              {protectTerms.length === 0 ? (
                <span className="empty">(空)</span>
              ) : (
                <ul className="term-list">
                  {protectTerms.map((t, i) => (
                    <li className="term-item" key={`p-${t}-${i}`}>
                      <span className="term-text">{t}</span>
                      <button
                        type="button"
                        className="term-remove"
                        aria-label={`删除 ${t}`}
                        onClick={() => onRemoveProtect(i)}
                      >
                        ×
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      </div>
    </details>
  );
}
