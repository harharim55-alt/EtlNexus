import { toSvg, toPng } from "html-to-image";

/**
 * Download a DOM element as .svg file.
 * Uses html-to-image to capture the full HTML rendering including divs.
 */
export async function downloadAsSVG(el: HTMLElement, filename: string): Promise<void> {
  try {
    const dataUrl = await toSvg(el, {
      backgroundColor: "#09090b",
      style: { margin: "0", padding: "16px" },
    });
    const blob = dataUrlToBlob(dataUrl);
    triggerDownload(blob, `${filename}.svg`);
  } catch (err) {
    console.error("SVG export failed:", err);
  }
}

/**
 * Download a DOM element as .png file.
 * Renders at 2x scale for crisp output.
 */
export async function downloadAsPNG(el: HTMLElement, filename: string, scale = 2): Promise<void> {
  try {
    const dataUrl = await toPng(el, {
      backgroundColor: "#09090b",
      pixelRatio: scale,
      style: { margin: "0", padding: "16px" },
    });
    const blob = dataUrlToBlob(dataUrl);
    triggerDownload(blob, `${filename}.png`);
  } catch (err) {
    console.error("PNG export failed:", err);
  }
}

/**
 * Download a DOM element as a self-contained interactive HTML file with pan/zoom.
 * Captures the full innerHTML so all nodes and edges are included.
 */
export async function downloadAsInteractiveHTML(el: HTMLElement, title: string): Promise<void> {
  try {
    // Capture as inline SVG data URL first, then embed in HTML
    const svgDataUrl = await toSvg(el, {
      backgroundColor: "#09090b",
      style: { margin: "0", padding: "16px" },
    });

    const html = `<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>${escapeHtml(title)} - Lineage</title>
<style>
  body { margin: 0; background: #09090b; overflow: hidden; font-family: system-ui; }
  #container { width: 100vw; height: 100vh; cursor: grab; display: flex; align-items: center; justify-content: center; }
  #container:active { cursor: grabbing; }
  #container img { transform-origin: 0 0; max-width: none; }
  .toolbar { position: fixed; top: 16px; right: 16px; display: flex; gap: 8px; z-index: 10; }
  .toolbar button { padding: 8px 12px; background: #18181b; color: #fff; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; cursor: pointer; font-size: 13px; }
  .toolbar button:hover { background: #27272a; }
  h1 { position: fixed; top: 16px; left: 16px; color: #e2e8f0; font-size: 14px; margin: 0; z-index: 10; }
</style></head><body>
<h1>${escapeHtml(title)}</h1>
<div class="toolbar">
  <button onclick="zoom(1.2)">+</button>
  <button onclick="zoom(0.8)">\u2212</button>
  <button onclick="resetView()">Reset</button>
</div>
<div id="container"><img src="${svgDataUrl}" /></div>
<script>
let scale=1,tx=0,ty=0;const c=document.getElementById('container'),img=c.querySelector('img');
function apply(){img.style.transform='translate('+tx+'px,'+ty+'px) scale('+scale+')';}
function zoom(f){scale*=f;apply();}function resetView(){scale=1;tx=0;ty=0;apply();}
let drag=false,sx,sy;c.onmousedown=e=>{drag=true;sx=e.clientX-tx;sy=e.clientY-ty;};
c.onmousemove=e=>{if(drag){tx=e.clientX-sx;ty=e.clientY-sy;apply();}};
c.onmouseup=()=>drag=false;c.onmouseleave=()=>drag=false;
c.onwheel=e=>{e.preventDefault();zoom(e.deltaY<0?1.1:0.9);};
</script></body></html>`;

    const blob = new Blob([html], { type: "text/html" });
    triggerDownload(blob, `${title.replace(/[^a-zA-Z0-9]/g, "_")}_lineage.html`);
  } catch (err) {
    console.error("Interactive HTML export failed:", err);
  }
}

function triggerDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function dataUrlToBlob(dataUrl: string): Blob {
  const [header, base64] = dataUrl.split(",");
  const mime = header.match(/:(.*?);/)?.[1] ?? "application/octet-stream";
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return new Blob([bytes], { type: mime });
}

function escapeHtml(str: string): string {
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
