document.querySelectorAll("[data-docs-disclosure]").forEach((disclosure) => {
  const button = disclosure.querySelector("button");
  const panel = document.getElementById(button.getAttribute("aria-controls"));

  function close() {
    button.setAttribute("aria-expanded", "false");
  }

  button.hidden = false;
  disclosure.classList.add("docs-disclosure-ready");
  button.addEventListener("click", () => {
    button.setAttribute("aria-expanded", button.getAttribute("aria-expanded") === "false");
  });
  disclosure.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && button.offsetParent && button.getAttribute("aria-expanded") === "true") {
      close();
      button.focus();
    }
  });

  if (panel.id === "docs-outline") {
    panel.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => {
        if (button.offsetParent) {
          close();
          const heading = document.getElementById(decodeURIComponent(link.hash.slice(1)));
          if (heading) {
            heading.tabIndex = -1;
            heading.focus({ preventScroll: true });
          }
        }
      });
    });
  }
});

const outlineEntries = [...document.querySelectorAll("#docs-outline a")].map((link) => ({
  link,
  heading: document.getElementById(decodeURIComponent(link.hash.slice(1))),
})).filter(({ heading }) => heading);

if (outlineEntries.length) {
  let current;
  let pending = false;
  function markVisibleSection() {
    pending = false;
    const offset = document.querySelector(".navbar").getBoundingClientRect().bottom + 48;
    const active = outlineEntries.findLast(({ heading }) => heading.getBoundingClientRect().top <= offset);
    if (active === current) return;
    current?.link.removeAttribute("aria-current");
    active?.link.setAttribute("aria-current", "location");
    current = active;
  }

  window.addEventListener("scroll", () => {
    if (!pending) {
      pending = true;
      requestAnimationFrame(markVisibleSection);
    }
  }, { passive: true });
  window.addEventListener("resize", markVisibleSection);
  markVisibleSection();
}

document.addEventListener("keydown", (event) => {
  if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey ||
      event.target.closest("input, textarea, select, [contenteditable], .modal")) return;

  const key = event.key.toUpperCase().charCodeAt(0);
  const direction = key === shortcuts.previous ? "prev" : key === shortcuts.next ? "next" : null;
  if (!direction || event.key.length !== 1) return;
  const link = document.querySelector(`.docs-pagination a[rel="${direction}"]`);
  if (link) {
    event.preventDefault();
    link.click();
  }
});

// MkDocs attaches its search input listener after the index is ready.
document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("mkdocs-search-query");
  window.searchWorker?.addEventListener("message", ({ data }) => {
    if (data.allowSearch && input?.value) {
      input.dispatchEvent(new KeyboardEvent("keyup"));
    }
  });
});
