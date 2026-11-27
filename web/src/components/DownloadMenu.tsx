import { useRef } from "react";
import { ChevronDown, Download } from "lucide-react";

export interface DownloadItem {
  label: string;
  disabled?: boolean;
  onSelect: () => void;
}

/** One "Download" button that opens a short list of formats. */
export function DownloadMenu({ items, label = "Download" }: { items: DownloadItem[]; label?: string }) {
  const menu = useRef<HTMLDetailsElement>(null);
  const disabled = items.every((item) => item.disabled);
  return (
    <details className="download-menu" ref={menu} onKeyDown={(event) => { if (event.key === "Escape") menu.current?.removeAttribute("open"); }}>
      <summary className="button" aria-disabled={disabled || undefined} onClick={(event) => { if (disabled) event.preventDefault(); }}>
        <Download size={16} aria-hidden="true" /> {label} <ChevronDown size={15} aria-hidden="true" />
      </summary>
      <div className="download-menu-list" role="group" aria-label={`${label} formats`}>
        {items.map((item) => (
          <button type="button" key={item.label} disabled={item.disabled} onClick={() => { menu.current?.removeAttribute("open"); item.onSelect(); }}>
            {item.label}
          </button>
        ))}
      </div>
    </details>
  );
}
