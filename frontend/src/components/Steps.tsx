import type { Step } from "@/types";

const LABELS = ["Input", "Review & select", "Redacted result"] as const;

interface StepsProps {
  step: Step;
}

export function Steps({ step }: StepsProps) {
  return (
    <nav className="steps" aria-label="Workflow steps">
      {LABELS.map((label, i) => {
        const n = (i + 1) as Step;
        const className = [
          "step",
          n === step ? "active" : "",
          n < step ? "done" : "",
        ]
          .filter(Boolean)
          .join(" ");
        return (
          <div key={label} className={className} data-step={n}>
            <span className="num">{n}</span> {label}
          </div>
        );
      })}
    </nav>
  );
}
