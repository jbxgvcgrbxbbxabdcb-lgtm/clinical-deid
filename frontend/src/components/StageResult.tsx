interface StageResultProps {
  originalText: string;
  outputText: string;
  resultMeta: string;
  fileLabel: string;
  downloadHint: string;
  downloadButtonLabel: string;
  onDownload: () => void;
  onAgain: () => void;
  onRestart: () => void;
}

export function StageResult({
  originalText,
  outputText,
  resultMeta,
  fileLabel,
  downloadHint,
  downloadButtonLabel,
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
