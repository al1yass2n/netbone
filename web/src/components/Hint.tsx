import { useId, useLayoutEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import "./Hint.css";

interface HintProps {
  label: string;
  children: ReactNode;
}

export function Hint({ label, children }: HintProps) {
  const id = useId();
  const trigger = useRef<HTMLButtonElement>(null);
  const bubble = useRef<HTMLSpanElement>(null);
  const [hovered, setHovered] = useState(false);
  const [focused, setFocused] = useState(false);
  const [pinned, setPinned] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const visible = !dismissed && (hovered || focused || pinned);

  useLayoutEffect(() => {
    const anchor = trigger.current;
    const tooltip = bubble.current;
    if (!visible || !anchor || !tooltip) return;

    function dismiss() {
      setDismissed(true);
      setPinned(false);
    }

    function onEscape(event: KeyboardEvent) {
      if (event.key !== "Escape") return;
      event.preventDefault();
      dismiss();
    }

    const onOutsidePointerDown = (event: PointerEvent) => {
      if (event.target instanceof Node && !anchor.contains(event.target) && !tooltip.contains(event.target)) {
        dismiss();
      }
    };

    const position = () => {
      const margin = 12;
      const rect = anchor.getBoundingClientRect();
      const { clientWidth, clientHeight } = document.documentElement;
      if (rect.bottom <= 0 || rect.top >= clientHeight) {
        dismiss();
        return;
      }
      const roomBelow = clientHeight - rect.bottom - margin;
      const roomAbove = rect.top - margin;
      tooltip.style.setProperty("--hint-available-width", `${clientWidth - margin * 2}px`);
      const { width, height } = tooltip.getBoundingClientRect();
      const above = height > roomBelow && roomAbove > roomBelow;
      const left = Math.max(margin, Math.min(rect.left + (rect.width - width) / 2, clientWidth - width - margin));
      const top = above ? Math.max(margin, rect.top - height) : Math.min(rect.bottom, clientHeight - height - margin);
      tooltip.style.left = `${left}px`;
      tooltip.style.top = `${Math.max(margin, top)}px`;
    };

    // The top layer lets the hint escape scroll containers, including dialogs.
    tooltip.showPopover?.();
    position();
    window.addEventListener("resize", position);
    window.addEventListener("scroll", position, true);
    document.addEventListener("keydown", onEscape, true);
    document.addEventListener("pointerdown", onOutsidePointerDown, true);
    return () => {
      tooltip.hidePopover?.();
      window.removeEventListener("resize", position);
      window.removeEventListener("scroll", position, true);
      document.removeEventListener("keydown", onEscape, true);
      document.removeEventListener("pointerdown", onOutsidePointerDown, true);
    };
  }, [visible, children]);

  return (
    <span
      className="field-hint"
      onPointerEnter={(event) => {
        if (event.pointerType === "touch") return;
        setHovered(true);
        setDismissed(false);
      }}
      onPointerLeave={() => setHovered(false)}
    >
      <button
        ref={trigger}
        className="field-hint__trigger"
        type="button"
        aria-label={label}
        aria-describedby={id}
        onFocus={(event) => {
          if (!event.currentTarget.matches(":focus-visible")) return;
          setFocused(true);
          setDismissed(false);
        }}
        onBlur={() => {
          setFocused(false);
          setPinned(false);
        }}
        onClick={() => {
          setPinned(!pinned);
          setDismissed(pinned);
        }}
      >
        <span aria-hidden="true">?</span>
      </button>
      <span id={id} ref={bubble} className="field-hint__bubble" role="tooltip" popover="manual" hidden={!visible}>
        {children}
      </span>
    </span>
  );
}
