const demo = document.querySelector("[data-sample-demo]");

const nodes = {
  alice: { x: 85, y: 61 },
  bob: { x: 315, y: 61 },
  carol: { x: 200, y: 139 },
  dana: { x: 305, y: 190 },
};

const percentage = new Intl.NumberFormat("en", { style: "percent" });

function drawGraph(canvas, edges, selected) {
  const context = canvas.getContext("2d");
  if (!context) return;
  context.setTransform(2, 0, 0, 2, 0, 0);
  context.clearRect(0, 0, 400, 240);
  context.lineCap = "round";

  for (const edge of edges) {
    const from = nodes[edge.source];
    const to = nodes[edge.target];
    const kept = selected.has(edge.edge_id);
    context.beginPath();
    context.moveTo(from.x, from.y);
    context.lineTo(to.x, to.y);
    context.lineWidth = kept ? 5 : 2;
    context.strokeStyle = kept ? "#176d58" : "#a9bdba";
    context.stroke();
  }

  context.font = "600 16px system-ui, sans-serif";
  context.textAlign = "center";
  for (const [name, node] of Object.entries(nodes)) {
    context.beginPath();
    context.arc(node.x, node.y, 8, 0, 2 * Math.PI);
    context.fillStyle = "#fff";
    context.fill();
    context.lineWidth = 2;
    context.strokeStyle = "#20343d";
    context.stroke();
    context.fillStyle = "#20343d";
    context.fillText(name, node.x, node.y + 27);
  }
}

function linkName(edge) {
  return `${edge.source} and ${edge.target}`;
}

function renderPanel(panel, data) {
  const percent = Number(panel.input.value);
  const selected = new Set(data.runs[percent]);
  panel.output.value = percentage.format(percent / 100);
  panel.input.setAttribute("aria-valuetext", panel.output.value);
  const count = `${selected.size} of ${data.edges.length} links kept`;
  panel.count.textContent = count;

  const keptLinks = data.edges.filter((edge) => selected.has(edge.edge_id));
  const description = keptLinks.length ? keptLinks.map(linkName).join(", ") : "None";
  panel.canvas.setAttribute("aria-label", `${count}. Retained links: ${description}.`);
  drawGraph(panel.canvas, data.edges, selected);

  return { percent, selected };
}

function addRows(table, edges) {
  return edges.map((edge) => {
    const row = table.insertRow();
    const label = document.createElement("th");
    label.scope = "row";
    label.textContent = linkName(edge);
    row.append(label);
    row.insertCell().textContent = edge.score;
    return { edge, left: row.insertCell(), right: row.insertCell() };
  });
}

async function start() {
  const status = demo.querySelector("[data-demo-status]");
  status.hidden = false;
  try {
    const response = await fetch(new URL("./sample-demo.json", import.meta.url));
    if (!response.ok) throw new Error("Demo data unavailable");
    const data = await response.json();
    const panels = [...demo.querySelectorAll("[data-demo-panel]")].map((section) => ({
      input: section.querySelector("input"),
      output: section.querySelector("output"),
      count: section.querySelector("[data-demo-count]"),
      canvas: section.querySelector("canvas"),
    }));
    const rows = addRows(demo.querySelector("[data-demo-links]"), data.edges);
    const comparison = demo.querySelector("[data-demo-comparison]");

    function render() {
      const [a, b] = panels.map((panel) => renderPanel(panel, data));
      for (const { edge, left, right } of rows) {
        left.textContent = a.selected.has(edge.edge_id) ? "Kept" : "Removed";
        right.textContent = b.selected.has(edge.edge_id) ? "Kept" : "Removed";
      }

      if (a.percent === b.percent) {
        comparison.textContent = a.percent === 0
          ? "Both backbones are empty."
          : "Both settings keep the same links. Edge Jaccard is 100%.";
      } else {
        const first = Math.min(a.percent, b.percent);
        const second = Math.max(a.percent, b.percent);
        const value = data.jaccard[`${first}:${second}`];
        comparison.textContent = `Edge Jaccard is ${percentage.format(value)}.`;
      }
    }

    render();
    for (const { input } of panels) input.addEventListener("input", render);
    status.hidden = true;
    demo.querySelector("[data-demo-view]").hidden = false;
  } catch {
    status.textContent = "The demo could not load. Reload the page to try again.";
  }
}

if (demo) void start();
