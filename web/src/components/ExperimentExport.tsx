import { Archive, LoaderCircle } from "lucide-react";
import { useState } from "react";
import { downloadWorkspaceExperiment } from "../api";

export function ExperimentExport({ experimentId, disabled = false }: { experimentId: string; disabled?: boolean }) {
  const [preparing, setPreparing] = useState(false);
  const [error, setError] = useState("");

  async function download() {
    setError("");
    setPreparing(true);
    try {
      await downloadWorkspaceExperiment(experimentId);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not download the experiment ZIP.");
    } finally {
      setPreparing(false);
    }
  }

  return (
    <div className="workspace-experiment-export">
      <button type="button" className="button button--save" disabled={disabled || preparing} onClick={() => void download()}>
        {preparing ? <LoaderCircle className="spin" size={16} aria-hidden="true" /> : <Archive size={16} aria-hidden="true" />}
        {preparing ? "Preparing ZIP…" : "Export full experiment"}
      </button>
      <span className="visually-hidden" role="status">{preparing ? "Preparing the experiment ZIP." : ""}</span>
      {error && <p className="error-text" role="alert">{error}</p>}
    </div>
  );
}
