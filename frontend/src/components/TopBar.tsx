import { BrandMark } from "@/components/BrandMark";

interface TopBarProps {
  themeLabel: string;
  onCycleTheme: () => void;
}

export function TopBar({ themeLabel, onCycleTheme }: TopBarProps) {
  return (
    <header className="topbar">
      <a className="brand" href="/">
        <BrandMark />
        <div>
          <div className="brand-name">Clinical</div>
          <div className="brand-tag">Review → select → redact</div>
        </div>
      </a>
      <div className="badge-row">
        <span className="pill on-device">100% on-device</span>
        <span className="pill">Synthetic only</span>
        <button
          type="button"
          className="theme-btn"
          title={`Theme: ${themeLabel} — click to switch`}
          onClick={onCycleTheme}
        >
          Theme
        </button>
      </div>
    </header>
  );
}
