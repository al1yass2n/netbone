(() => {
  const languages = {
    bash: "Shell",
    console: "Shell",
    shell: "Shell",
    python: "Python",
    pycon: "Python",
    bibtex: "BibTeX",
    json: "JSON",
    text: "Text",
    yaml: "YAML",
    csv: "CSV",
    toml: "TOML",
  };

  document.querySelectorAll("main .codehilite, [role=main] .codehilite").forEach((block) => {
    const code = block.querySelector("pre > code");
    if (!code || block.closest(".doc-signature")) return;

    const languageClass = [...block.classList].find((name) => name.startsWith("language-"));
    const language = languageClass ? languageClass.slice("language-".length) : "";

    const header = document.createElement("div");
    header.className = "code-header";
    const label = document.createElement("span");
    label.textContent = languages[language] || "";
    header.append(label);

    if (navigator.clipboard) {
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
      header.append(button);
    }
    block.prepend(header);
  });
})();
