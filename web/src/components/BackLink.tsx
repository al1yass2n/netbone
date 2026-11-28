import { ArrowLeft } from "lucide-react";

/** The way back from Compare and Sweep to the analysis. */
export function BackLink({ onClick }: { onClick: () => void }) {
  return (
    <button type="button" className="back-link" onClick={onClick}>
      <ArrowLeft size={16} aria-hidden="true" /> Back to analysis
    </button>
  );
}
