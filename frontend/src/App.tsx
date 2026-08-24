import { Hero } from "@/components/Hero";
import { StageResult } from "@/components/StageResult";
import { StageReview } from "@/components/StageReview";
import { StageUpload } from "@/components/StageUpload";
import { Steps } from "@/components/Steps";
import { TopBar } from "@/components/TopBar";
import { useDeidFlow } from "@/hooks/useDeidFlow";
import { useTheme } from "@/hooks/useTheme";

export default function App() {
  const { themeLabel, cycleTheme } = useTheme();
  const flow = useDeidFlow();

  return (
    <>
      <div className="atmosphere" aria-hidden="true" />
      <div className="shell">
        <TopBar themeLabel={themeLabel} onCycleTheme={cycleTheme} />
        <Hero />
        <Steps step={flow.step} />

        {flow.step === 1 ? (
          <StageUpload
            inputMode={flow.inputMode}
            uploadedName={flow.uploadedName}
            pasteText={flow.pasteText}
            busy={flow.busyDetect}
            onInputMode={flow.setInputMode}
            onAcceptFile={flow.acceptFile}
            onPasteText={flow.setPasteText}
            onDetect={() => void flow.handleDetect()}
            onSample={() => void flow.handleSample()}
          />
        ) : null}

        {flow.step === 2 ? (
          <StageReview
            sourceText={flow.sourceText}
            entities={flow.entities}
            selected={flow.selected}
            activeId={flow.activeId}
            confMin={flow.confMin}
            highConf={flow.highConf}
            method={flow.method}
            uploadedName={flow.uploadedName}
            forceTerms={flow.forceTerms}
            protectTerms={flow.protectTerms}
            selectAccent={flow.selectAccent}
            busy={flow.busyApply}
            onConfMin={flow.onConfChange}
            onMethod={flow.setMethod}
            onToggle={flow.toggleEntity}
            onActivate={flow.setActiveId}
            onReplacement={flow.updateReplacement}
            onSelectVisible={flow.selectVisible}
            onSelectAll={flow.selectAll}
            onSelectNone={flow.selectNone}
            onAddForce={flow.addForceTerm}
            onClearForce={flow.clearForceTerms}
            onRemoveForce={flow.removeForceTerm}
            onAddProtect={flow.addProtectTerm}
            onClearProtect={flow.clearProtectTerms}
            onRemoveProtect={flow.removeProtectTerm}
            onBack={() => flow.setStep(1)}
            onApply={() => void flow.handleApply()}
          />
        ) : null}

        {flow.step === 3 ? (
          <StageResult
            originalText={flow.originalText}
            outputText={flow.outputText}
            resultMeta={flow.resultMeta}
            fileLabel={flow.fileLabel}
            downloadHint={flow.downloadHint}
            downloadButtonLabel={flow.downloadButtonLabel}
            fidelity={flow.fidelity}
            onDownload={flow.handleDownload}
            onAgain={() => flow.setStep(2)}
            onRestart={flow.handleRestart}
          />
        ) : null}

        <p className="footer-note">
          React frontend · proxies <code>/api</code> to{" "}
          <code>uvicorn backend.app:app</code> on port 7870
        </p>
      </div>
    </>
  );
}
