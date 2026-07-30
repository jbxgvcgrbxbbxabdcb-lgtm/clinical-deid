import { METHOD_HINTS, METHODS } from "@/constants";
import type { Method } from "@/types";

interface MethodBlockProps {
  method: Method;
  onMethod: (method: Method) => void;
}

export function MethodBlock({ method, onMethod }: MethodBlockProps) {
  return (
    <div className="method-block">
      <span className="block-label">Method</span>
      <div className="methods" role="radiogroup" aria-label="Replacement method">
        {METHODS.map((m) => (
          <label className="method" key={m}>
            <input
              type="radio"
              name="method"
              value={m}
              checked={method === m}
              onChange={() => onMethod(m)}
            />
            <span>{m}</span>
          </label>
        ))}
      </div>
      <p className="hint">{METHOD_HINTS[method]}</p>
    </div>
  );
}
