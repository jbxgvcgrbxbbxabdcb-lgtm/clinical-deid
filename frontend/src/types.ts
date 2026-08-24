export type ThemeName = "mist" | "paper" | "night";
export type InputMode = "file" | "paste";
export type Step = 1 | 2 | 3;
export type Method =
  | "mask"
  | "replace"
  | "hash"
  | "remove"
  | "shift_dates"
  | "format_preserve";

export interface Entity {
  id: string;
  label: string;
  text: string;
  start: number;
  end: number;
  confidence: number;
  replacement?: string | null;
}

export interface ReviewPayload {
  session_id: string;
  kind?: string;
  filename?: string;
  text?: string;
  method?: string;
  high_confidence_threshold?: number;
  default_confidence_filter?: number;
  entities?: Entity[];
  error?: string;
}

export interface FidelityRegion {
  page: number;
  bbox: number[];
  label?: string | null;
  residual_text_found: boolean;
  residual_word_count: number;
  pixels_changed: boolean;
  passed: boolean;
}

export interface Fidelity {
  check: string;
  passed: boolean;
  region_count: number;
  failing_region_count: number;
  regions: FidelityRegion[];
}

export interface ApplyPayload {
  text?: string;
  original_text?: string;
  filename?: string;
  applied_count?: number;
  session_kind?: string;
  download_url?: string;
  download_filename?: string;
  fidelity?: Fidelity;
  error?: string;
  status?: string;
}
