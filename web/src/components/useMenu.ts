import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent } from "react";

/** Wiring for a menu built on <details>: it closes on Escape and on a click outside it. */
export function useMenu() {
  const ref = useRef<HTMLDetailsElement>(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    function closeOutside(event: PointerEvent) {
      if (!ref.current?.contains(event.target as Node)) ref.current?.removeAttribute("open");
    }
    document.addEventListener("pointerdown", closeOutside);
    return () => document.removeEventListener("pointerdown", closeOutside);
  }, [open]);

  function close() {
    ref.current?.removeAttribute("open");
  }

  return {
    close,
    props: {
      ref,
      onToggle: (event: { currentTarget: HTMLDetailsElement }) => {
        const details = event.currentTarget;
        setOpen(details.open);
        if (!details.open) return;
        // The list lines up with the button's right edge and opens leftward, unless that runs off the screen.
        const list = details.querySelector<HTMLElement>(".menu-list");
        const box = details.getBoundingClientRect();
        details.dataset.align = box.right - (list?.offsetWidth ?? 240) < 8 ? "start" : "end";
      },
      onKeyDown: (event: KeyboardEvent<HTMLDetailsElement>) => {
        if (event.key !== "Escape" || !ref.current?.open) return;
        // A menu inside a dialog closes alone; the dialog stays open.
        event.preventDefault();
        event.stopPropagation();
        close();
        ref.current.querySelector("summary")?.focus();
      },
    },
  };
}
