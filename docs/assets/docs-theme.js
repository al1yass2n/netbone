(() => {
  const storageKey = "netbone-docs-theme";
  const choices = ["system", "light", "dark"];
  const system = window.matchMedia("(prefers-color-scheme: dark)");
  const root = document.documentElement;
  let preference = "system";

  try {
    const saved = localStorage.getItem(storageKey);
    if (choices.includes(saved)) preference = saved;
  } catch {
    // The selector still works for the current page when storage is unavailable.
  }

  function applyTheme() {
    root.dataset.docsTheme = preference;
    root.dataset.bsTheme = preference === "system" ? (system.matches ? "dark" : "light") : preference;
  }

  applyTheme();

  system.addEventListener("change", () => {
    if (preference === "system") applyTheme();
  });

  document.addEventListener("DOMContentLoaded", () => {
    const select = document.getElementById("docs-color-theme");
    if (!select) return;
    select.value = preference;
    select.parentElement.hidden = false;
    select.addEventListener("change", () => {
      preference = select.value;
      applyTheme();
      try {
        localStorage.setItem(storageKey, preference);
      } catch {
        // The current page has already adopted the selected theme.
      }
    });
  });
})();
