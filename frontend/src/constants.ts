import type { Method, ThemeName } from "@/types";

export const THEMES: ThemeName[] = ["mist", "paper", "night"];
export const THEME_NAMES: Record<ThemeName, string> = {
  mist: "Mist",
  paper: "Paper",
  night: "Night",
};
export const THEME_STORAGE_KEY = "openmed-deid-theme";

export const FALLBACK_SAMPLE =
  "Synthetic note: John Doe (MRN 123456) was seen on 01/15/2023 by " +
  "Dr. Alice Smith. Reach John Doe at john.doe@example.com or " +
  "(415) 555-0142.";

export const METHOD_HINTS: Record<Method, string> = {
  mask: "mask: replace with [LABEL] placeholders",
  replace: "replace: same name → same fake identity (consistent)",
  hash: "hash: stable hashed tokens for linking",
  remove: "remove: delete the span entirely",
  shift_dates: "shift_dates: move dates by a stable offset",
  format_preserve: "format_preserve: keep phone/ID shape with synthetic digits",
};

export const METHODS: Method[] = [
  "mask",
  "replace",
  "hash",
  "remove",
  "shift_dates",
  "format_preserve",
];

export const ALLOWED_EXTS = new Set(["docx", "md", "markdown", "pdf"]);
