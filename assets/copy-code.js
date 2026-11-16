if (navigator.clipboard) {
  document.querySelectorAll("main pre, [role=main] pre").forEach((block) => {
    const code = block.querySelector("code");
    if (!code || block.closest(".doc-signature")) return;

    const controls = document.createElement("div");
    controls.className = "code-copy";
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = "Copy";
    button.setAttribute("aria-label", "Copy code");
    button.setAttribute("aria-live", "polite");
    button.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(code.textContent);
        button.textContent = "Copied";
        button.setAttribute("aria-label", "Code copied");
      } catch {
        button.textContent = "Copy failed";
        button.setAttribute("aria-label", "Copy failed. Select the code to copy it.");
      }
    });
    controls.append(button);
    block.before(controls);
  });
}
