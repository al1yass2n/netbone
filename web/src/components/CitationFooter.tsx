import { Check, Copy } from "lucide-react";
import { useEffect, useRef, useState } from "react";

const doi = "10.1038/s41598-023-42076-3";
const bibtex = `@article{yassin2023netbone,
  author = {Yassin, Ali and Haidar, Abbas and Cherifi, Hocine and Seba, Hamida and Togni, Olivier},
  title = {An evaluation tool for backbone extraction techniques in weighted complex networks},
  journal = {Scientific Reports},
  year = {2023},
  volume = {13},
  number = {1},
  pages = {17000},
  doi = {${doi}}
}
`;

export function CitationFooter() {
  const [copyState, setCopyState] = useState<"ready" | "copied" | "manual">("ready");
  const manualCitation = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (copyState === "manual") {
      manualCitation.current?.focus();
    }
  }, [copyState]);

  async function copyCitation() {
    try {
      await navigator.clipboard.writeText(bibtex);
      setCopyState("copied");
    } catch {
      setCopyState("manual");
    }
  }

  return (
    <footer className="citation-footer">
      <a href={`https://doi.org/${doi}`}>Cite Netbone</a>
      <span>Yassin et al. · Scientific Reports (2023)</span>
      <button type="button" className="citation-copy" onClick={() => void copyCitation()}>
        {copyState === "copied" ? <Check size={14} aria-hidden="true" /> : <Copy size={14} aria-hidden="true" />}
        Copy BibTeX
      </button>
      <span className={copyState === "copied" ? undefined : "visually-hidden"} role="status">
        {copyState === "copied" ? "BibTeX copied" : ""}
      </span>
      {copyState === "manual" && (
        <label className="citation-manual">
          <span>Copy the BibTeX citation manually.</span>
          <textarea ref={manualCitation} aria-label="BibTeX citation" readOnly value={bibtex} rows={5} onFocus={(event) => event.currentTarget.select()} />
        </label>
      )}
    </footer>
  );
}
