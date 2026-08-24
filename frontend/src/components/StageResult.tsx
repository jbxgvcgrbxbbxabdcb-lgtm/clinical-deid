import type { Fidelity } from "@/types";

interface StageResultProps {
  originalText: string;
  outputText: string;
  resultMeta: string;
  fileLabel: string;
  downloadHint: string;
  downloadButtonLabel: string;
  fidelity?: Fidelity | null;
  onDownload: () => void;
  onAgain: () => void;
  onRestart: () => void;
}

function FidelityBanner({ fidelity }: { fidelity: Fidelity }) {
  const failures = fidelity.failing_region_count;
  return (
    <div
      className={`fidelity-banner${fidelity.passed ? " ok" : " fail"}`}
      role={fidelity.passed ? "status" : "alert"}
    >
      <strong>
        {fidelity.passed
          ? "PDF redaction verified"
          : `PDF redaction check FAILED (${failures} region${failures === 1 ? "" : "s"})`}
      </strong>
      <p>
        {fidelity.passed
          ? "All redacted regions show no residual text and are covered by an opaque box."
          : "Some redacted regions still contain selectable text or are not covered by an opaque box — review before sharing."}
      </p>
      {!fidelity.passed ? (
        <ul>
          {fidelity.regions
            .filter((region) => !region.passed)
            .slice(0, 5)
            .map((region, index) => (
              <li key={`${region.page}-${index}`}>
                page {region.page + 1}
                {region.label ? ` · ${region.label}` : ""} —{" "}
                {region.residual_text_found
                  ? `${region.residual_word_count} residual word(s)`
                  : "no visible box"}
              </li>
            ))}
        </ul>
      ) : null}
    </div>
  );
}

export function StageResult({
  originalText,
  outputText,
  resultMeta,
  fileLabel,
  downloadHint,
  downloadButtonLabel,
  fidelity,
  onDownload,
  onAgain,
  onRestart,
}: StageResultProps) {
  return (
    <section className="panel stage" id="stage-result">
      <div className="panel-head">
        <h2>Redacted result</h2>
        <span className="panel-meta">{resultMeta}</span>
      </div>
      <div className="panel-body">
        {fidelity ? <FidelityBanner fidelity={fidelity} /> : null}
        <div className="result-grid">
          <div className="result-block">
            <h3>Original (synthetic)</h3>
            <div className="result-text">{originalText}</div>
          </div>
          <div className="result-block">
            <h3>After selected redactions</h3>
            <div className="result-text out">{outputText}</div>
          </div>
        </div>
        <div className="download-card">
          <div>
            <strong>{fileLabel}</strong>
            <p>{downloadHint}</p>
          </div>
          <button type="button" className="btn-primary" onClick={onDownload}>
            {downloadButtonLabel}
          </button>
        </div>
        <div className="upload-actions">
          <button type="button" className="btn-ghost" onClick={onAgain}>
            Review again
          </button>
          <button type="button" className="btn-ghost" onClick={onRestart}>
            Start over
          </button>
        </div>
      </div>
    </section>
  );
}