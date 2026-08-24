import { useCallback, useEffect, useRef, useState } from "react";
import {
  applyRedaction,
  detectDocx,
  detectPdf,
  detectText,
  fetchSampleText,
  refreshReview,
} from "@/api/client";
import { ALLOWED_EXTS, FALLBACK_SAMPLE } from "@/constants";
import {
  fileExt,
  preserveSelectionBySpans,
  redactedDownloadName,
  selectByConfidence,
} from "@/lib/review";
import type {
  ApplyPayload,
  Entity,
  Fidelity,
  InputMode,
  Method,
  ReviewPayload,
  Step,
} from "@/types";

function showError(message: string) {
  window.alert(message || "Request failed");
}

/** Orchestrates detect → review → apply for the three-step flow. */
export function useDeidFlow() {
  const [step, setStep] = useState<Step>(1);
  const [inputMode, setInputMode] = useState<InputMode>("file");
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [uploadedName, setUploadedName] = useState<string | null>(null);
  const [pasteText, setPasteText] = useState("");
  const [method, setMethod] = useState<Method>("mask");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sourceText, setSourceText] = useState("");
  const [entities, setEntities] = useState<Entity[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [activeId, setActiveId] = useState<string | null>(null);
  const [confMin, setConfMin] = useState(0.7);
  const [highConf, setHighConf] = useState(0.9);
  const [forceTerms, setForceTerms] = useState<string[]>([]);
  const [protectTerms, setProtectTerms] = useState<string[]>([]);
  const [selectAccent, setSelectAccent] = useState<string | null>(null);
  const [busyDetect, setBusyDetect] = useState(false);
  const [busyApply, setBusyApply] = useState(false);

  const [originalText, setOriginalText] = useState("");
  const [outputText, setOutputText] = useState("");
  const [resultMeta, setResultMeta] = useState("Ready");
  const [fileLabel, setFileLabel] = useState("note_redacted.txt");
  const [downloadHint, setDownloadHint] = useState(
    "Download the redacted file, or copy the text above",
  );
  const [downloadButtonLabel, setDownloadButtonLabel] = useState(
    "Download redacted text",
  );
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [downloadFilename, setDownloadFilename] = useState<string | null>(null);
  const [fidelity, setFidelity] = useState<Fidelity | null>(null);

  const refreshTimer = useRef<number | null>(null);
  const skipMethodRefresh = useRef(false);
  const entitiesRef = useRef<Entity[]>([]);
  const selectedRef = useRef<Set<string>>(new Set());
  const confMinRef = useRef(confMin);
  const uploadedNameRef = useRef<string | null>(null);
  /** User-edited replacements keyed by `start:end` (survives force/protect refresh). */
  const replacementOverridesRef = useRef<Map<string, string>>(new Map());
  const methodRef = useRef(method);

  useEffect(() => {
    entitiesRef.current = entities;
  }, [entities]);
  useEffect(() => {
    selectedRef.current = selected;
  }, [selected]);
  useEffect(() => {
    confMinRef.current = confMin;
  }, [confMin]);
  useEffect(() => {
    uploadedNameRef.current = uploadedName;
  }, [uploadedName]);

  const ingestReview = useCallback(
    (data: ReviewPayload, resetSelection: boolean) => {
      setSessionId(data.session_id);
      setSourceText(data.text || "");
      setUploadedName(data.filename || uploadedNameRef.current || "note");
      if (typeof data.high_confidence_threshold === "number") {
        setHighConf(data.high_confidence_threshold);
      }
      let nextConf = confMinRef.current;
      if (
        typeof data.default_confidence_filter === "number" &&
        resetSelection
      ) {
        nextConf = data.default_confidence_filter;
        setConfMin(nextConf);
      }
      const nextEntities = Array.isArray(data.entities) ? data.entities : [];
      if (resetSelection) {
        replacementOverridesRef.current.clear();
        setSelected(selectByConfidence(nextConf, nextEntities));
        setActiveId(null);
        setSelectAccent(null);
        setEntities(nextEntities);
      } else {
        const overrides = replacementOverridesRef.current;
        const merged = nextEntities.map((e) => {
          const override = overrides.get(`${e.start}:${e.end}`);
          return override !== undefined ? { ...e, replacement: override } : e;
        });
        setSelected(
          preserveSelectionBySpans(
            entitiesRef.current,
            selectedRef.current,
            merged,
            nextConf,
          ),
        );
        setEntities(merged);
      }
      setStep(2);
    },
    [],
  );

  async function runDetectText(text: string, filename: string) {
    const data = await detectText({
      text,
      method,
      filename,
      force_terms: forceTerms,
      protect_terms: protectTerms,
    });
    setUploadedFile(null);
    skipMethodRefresh.current = true;
    ingestReview(data, true);
  }

  async function runDetectFile(file: File) {
    const ext = fileExt(file.name);
    if (ext === "md" || ext === "markdown" || ext === "txt") {
      const text = await file.text();
      await runDetectText(text, file.name);
      return;
    }
    if (ext === "pdf") {
      const data = await detectPdf({
        file,
        method,
        force_terms: forceTerms,
        protect_terms: protectTerms,
      });
      skipMethodRefresh.current = true;
      ingestReview(data, true);
      return;
    }
    const data = await detectDocx({
      file,
      method,
      force_terms: forceTerms,
      protect_terms: protectTerms,
    });
    skipMethodRefresh.current = true;
    ingestReview(data, true);
  }

  async function handleDetect() {
    setBusyDetect(true);
    try {
      if (inputMode === "paste") {
        const text = pasteText.trim();
        if (!text) {
          throw new Error(
            "Paste some synthetic text first, or use the sample note.",
          );
        }
        await runDetectText(text, "pasted_note.txt");
      } else {
        if (!uploadedFile) {
          throw new Error(
            "Upload a .docx or .md file first, or use the sample note.",
          );
        }
        await runDetectFile(uploadedFile);
      }
    } catch (err) {
      showError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusyDetect(false);
    }
  }

  async function handleSample() {
    setBusyDetect(true);
    try {
      const sample = (await fetchSampleText()) || FALLBACK_SAMPLE;
      await runDetectText(sample, "synthetic_discharge_note.txt");
    } catch (err) {
      showError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusyDetect(false);
    }
  }

  function acceptFile(file: File) {
    const ext = fileExt(file.name || "upload.docx");
    if (!ALLOWED_EXTS.has(ext)) {
      showError("Only .docx, .md, and .pdf files are supported.");
      return;
    }
    setUploadedFile(file);
    setUploadedName(file.name || "upload.docx");
  }

  const refreshMethod = useCallback(async () => {
    if (!sessionId || step !== 2) return;
    try {
      const data = await refreshReview({
        session_id: sessionId,
        method,
        force_terms: forceTerms,
        protect_terms: protectTerms,
      });
      skipMethodRefresh.current = true;
      ingestReview(data, false);
    } catch (err) {
      showError(err instanceof Error ? err.message : String(err));
    }
  }, [forceTerms, ingestReview, method, protectTerms, sessionId, step]);

  useEffect(() => {
    if (skipMethodRefresh.current) {
      skipMethodRefresh.current = false;
      return;
    }
    if (!sessionId || step !== 2) return;
    // Method change → drop custom replacements; force/protect keep them.
    if (methodRef.current !== method) {
      replacementOverridesRef.current.clear();
      methodRef.current = method;
    }
    if (refreshTimer.current) window.clearTimeout(refreshTimer.current);
    refreshTimer.current = window.setTimeout(() => {
      void refreshMethod();
    }, 150);
    return () => {
      if (refreshTimer.current) window.clearTimeout(refreshTimer.current);
    };
  }, [method, forceTerms, protectTerms, refreshMethod, sessionId, step]);

  function onConfChange(value: number) {
    setConfMin(value);
    setSelected(selectByConfidence(value, entities));
    setSelectAccent(null);
  }

  function toggleEntity(id: string) {
    setActiveId(id);
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function updateReplacement(id: string, replacement: string) {
    setActiveId(id);
    setEntities((prev) => {
      const next = prev.map((e) => {
        if (e.id !== id) return e;
        replacementOverridesRef.current.set(
          `${e.start}:${e.end}`,
          replacement,
        );
        return { ...e, replacement };
      });
      return next;
    });
    setSelected((prev) => {
      if (prev.has(id)) return prev;
      const next = new Set(prev);
      next.add(id);
      return next;
    });
  }

  function addTerm(
    list: string[],
    setList: (v: string[]) => void,
    other: string[],
    term: string,
  ) {
    const cleaned = term.trim();
    if (!cleaned) return;
    if (other.some((t) => t.toLowerCase() === cleaned.toLowerCase())) {
      showError("Term appears in both Force and Protect lists.");
      return;
    }
    if (list.some((t) => t.toLowerCase() === cleaned.toLowerCase())) return;
    setList([...list, cleaned]);
  }

  async function handleApply() {
    if (!sessionId) {
      showError("No review session. Detect entities first.");
      return;
    }
    setBusyApply(true);
    try {
      const selectedSpans = entities
        .filter((e) => selected.has(e.id))
        .map((e) => ({
          id: e.id,
          start: e.start,
          end: e.end,
          label: e.label,
          text: e.text,
          confidence: e.confidence,
          // Always send replacement so apply uses client edits ("" is valid).
          replacement:
            e.replacement != null
              ? e.replacement
              : method === "remove"
                ? ""
                : `[${e.label || "PII"}]`,
        }));
      const data: ApplyPayload = await applyRedaction({
        session_id: sessionId,
        method,
        selected_spans: selectedSpans,
        force_terms: forceTerms,
        protect_terms: protectTerms,
      });
      setOriginalText(data.original_text || sourceText);
      setOutputText(data.text || "");
      setResultMeta(
        `${data.applied_count || selectedSpans.length} spans · ${method}`,
      );
      setDownloadUrl(data.download_url || null);
      setDownloadFilename(data.download_filename || null);
      setFidelity(data.fidelity || null);
      const sourceName = data.filename || uploadedName || "note";
      const { stem, textExt } = redactedDownloadName(sourceName);
      const isPdf = /\.pdf$/i.test(sourceName);
      if (data.download_url) {
        setFileLabel(
          data.download_filename || `${stem}_redacted${textExt}`,
        );
        if (isPdf) {
          setDownloadHint(
            "Redacted PDF ready for download" +
              (data.fidelity && !data.fidelity.passed
                ? " — fidelity check FAILED, review warnings"
                : ""),
          );
          setDownloadButtonLabel("Download redacted PDF");
        } else {
          setDownloadHint("Redacted DOCX ready for download");
          setDownloadButtonLabel("Download redacted DOCX");
        }
      } else {
        setFileLabel(`${stem}_redacted${textExt}`);
        setDownloadHint(
          textExt === ".md"
            ? "Markdown session — download a .md of the redacted note"
            : textExt === ".pdf"
              ? "PDF session — download a .pdf of the redacted note"
              : "Text session — download a .txt of the redacted note",
        );
        setDownloadButtonLabel(
          textExt === ".pdf" ? "Download redacted PDF" : "Download redacted text",
        );
      }
      setStep(3);
    } catch (err) {
      showError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusyApply(false);
    }
  }

  function handleDownload() {
    if (downloadUrl) {
      const a = document.createElement("a");
      a.href = downloadUrl;
      if (downloadFilename) a.download = downloadFilename;
      a.click();
      return;
    }
    const blob = new Blob([outputText], { type: "text/plain;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    const sourceName = uploadedName || "note";
    const { stem, textExt } = redactedDownloadName(sourceName);
    a.download = `${stem}_redacted${textExt}`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  function handleRestart() {
    setUploadedFile(null);
    setUploadedName(null);
    setPasteText("");
    setSessionId(null);
    setSelected(new Set());
    setEntities([]);
    setActiveId(null);
    setDownloadUrl(null);
    setDownloadFilename(null);
    setFidelity(null);
    setForceTerms([]);
    setProtectTerms([]);
    replacementOverridesRef.current.clear();
    setInputMode("file");
    setStep(1);
  }

  function selectVisible() {
    setSelected(
      new Set(
        entities
          .filter((e) => Number(e.confidence) >= confMin)
          .map((e) => e.id),
      ),
    );
    setSelectAccent("visible");
  }

  function selectAll() {
    setSelected(new Set(entities.map((e) => e.id)));
    setSelectAccent("all");
  }

  function selectNone() {
    setSelected(new Set());
    setSelectAccent("none");
  }

  return {
    step,
    setStep,
    inputMode,
    setInputMode,
    uploadedName,
    pasteText,
    setPasteText,
    method,
    setMethod,
    sourceText,
    entities,
    selected,
    activeId,
    setActiveId,
    confMin,
    highConf,
    forceTerms,
    protectTerms,
    selectAccent,
    busyDetect,
    busyApply,
    originalText,
    outputText,
    resultMeta,
    fileLabel,
    downloadHint,
    downloadButtonLabel,
    fidelity,
    acceptFile,
    handleDetect,
    handleSample,
    onConfChange,
    toggleEntity,
    updateReplacement,
    selectVisible,
    selectAll,
    selectNone,
    addForceTerm: (term: string) =>
      addTerm(forceTerms, setForceTerms, protectTerms, term),
    clearForceTerms: () => setForceTerms([]),
    removeForceTerm: (idx: number) =>
      setForceTerms((prev) => prev.filter((_, i) => i !== idx)),
    addProtectTerm: (term: string) =>
      addTerm(protectTerms, setProtectTerms, forceTerms, term),
    clearProtectTerms: () => setProtectTerms([]),
    removeProtectTerm: (idx: number) =>
      setProtectTerms((prev) => prev.filter((_, i) => i !== idx)),
    handleApply,
    handleDownload,
    handleRestart,
  };
}
