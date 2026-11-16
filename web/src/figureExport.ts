function figureFilename(filename: string, extension: "png" | "svg"): string {
  const stem = filename.replace(/\.[^.]+$/, "").replace(/[^a-zA-Z0-9._-]+/g, "-");
  return `${stem || "netbone-figure"}.${extension}`;
}

function serializedSvg(svg: SVGSVGElement): string {
  const clone = svg.cloneNode(true) as SVGSVGElement;
  clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  const viewBox = clone.viewBox.baseVal;
  clone.setAttribute("width", String(viewBox.width));
  clone.setAttribute("height", String(viewBox.height));
  clone.insertAdjacentHTML("afterbegin", "<style>text{font-family:Inter,Arial,sans-serif;letter-spacing:0}</style>");
  return new XMLSerializer().serializeToString(clone);
}

function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}

export function downloadSvgFigure(svg: SVGSVGElement, filename: string): void {
  const source = serializedSvg(svg);
  downloadBlob(new Blob([source], { type: "image/svg+xml;charset=utf-8" }), figureFilename(filename, "svg"));
}

export async function downloadPngFigure(svg: SVGSVGElement, filename: string): Promise<void> {
  const source = serializedSvg(svg);
  const blob = new Blob([source], { type: "image/svg+xml;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  try {
    const image = new Image();
    image.decoding = "async";
    image.src = url;
    await image.decode();
    const viewBox = svg.viewBox.baseVal;
    const scale = 2;
    const canvas = document.createElement("canvas");
    canvas.width = Math.ceil(viewBox.width * scale);
    canvas.height = Math.ceil(viewBox.height * scale);
    const context = canvas.getContext("2d");
    if (!context) throw new Error("This browser cannot create a PNG figure.");
    context.fillStyle = "#ffffff";
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.drawImage(image, 0, 0, canvas.width, canvas.height);
    const png = await new Promise<Blob>((resolve, reject) => canvas.toBlob((result) => result ? resolve(result) : reject(new Error("PNG encoding failed.")), "image/png"));
    downloadBlob(png, figureFilename(filename, "png"));
  } finally {
    URL.revokeObjectURL(url);
  }
}
