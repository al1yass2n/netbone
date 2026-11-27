import { useState } from "react";
import { ChevronDown, Download, LoaderCircle } from "lucide-react";
import { useMenu } from "./useMenu";

export interface DownloadItem {
  label: string;
  disabled?: boolean;
  onSelect: () => void | Promise<void>;
}

/** The one Download button on a screen. It lists every file the screen can save. */
export function DownloadMenu({ items, label = "Download" }: { items: DownloadItem[]; label?: string }) {
  const menu = useMenu();
  const [preparing, setPreparing] = useState(false);
  const [error, setError] = useState("");
  const disabled = preparing || items.every((item) => item.disabled);

  async function select(item: DownloadItem) {
    menu.close();
    setError("");
    const pending = item.onSelect();
    if (!pending) return;
    setPreparing(true);
    try {
      await pending;
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The download failed.");
    } finally {
      setPreparing(false);
    }
  }

  return (
    <div className="download-menu-wrap">
      <details className="download-menu" {...menu.props}>
        <summary className="button" aria-disabled={disabled || undefined} onClick={(event) => { if (disabled) event.preventDefault(); }}>
          {preparing ? <LoaderCircle className="spin" size={16} aria-hidden="true" /> : <Download size={16} aria-hidden="true" />}
          {preparing ? "Preparing…" : label}
          <ChevronDown size={15} aria-hidden="true" />
        </summary>
        <div className="menu-list download-menu-list" role="group" aria-label={`${label} options`}>
          {items.map((item) => (
            <button type="button" key={item.label} disabled={item.disabled} onClick={() => void select(item)}>
              {item.label}
            </button>
          ))}
        </div>
      </details>
      <span className="visually-hidden" role="status">{preparing ? "Preparing the download." : ""}</span>
      {error && <p className="error-text" role="alert">{error}</p>}
    </div>
  );
}
