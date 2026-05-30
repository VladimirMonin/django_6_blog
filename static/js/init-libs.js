// static/js/init-libs.js
/**
 * Инициализация библиотек подсветки кода и диаграмм.
 * Mermaid рендерит SVG, svg-pan-zoom даёт масштабирование и панорамирование
 * больших диаграмм без потери векторной чёткости.
 */

const mermaidPanZoomInstances = new WeakMap();

function initHighlightJS(root = document) {
  if (!window.hljs) return;
  root.querySelectorAll("pre code").forEach((block) => {
    hljs.highlightElement(block);
  });
  console.log("✓ Highlight.js инициализирован");
}

function initMermaidConfig() {
  if (!window.mermaid || window.__mermaidConfigured) return;
  mermaid.initialize({
    startOnLoad: false,
    theme: "default",
    securityLevel: "loose",
    flowchart: {
      useMaxWidth: false,
      htmlLabels: true,
    },
    gantt: {
      useMaxWidth: false,
    },
  });
  window.__mermaidConfigured = true;
}

function initMermaidPanZoom(root = document) {
  if (!window.svgPanZoom) return;

  root.querySelectorAll(".mermaid-panzoom-shell").forEach((shell) => {
    const svg = shell.querySelector("svg");
    if (!svg || mermaidPanZoomInstances.has(svg)) return;

    svg.removeAttribute("height");
    svg.style.width = "100%";
    svg.style.height = "100%";
    svg.setAttribute("preserveAspectRatio", "xMidYMid meet");

    const panZoom = svgPanZoom(svg, {
      zoomEnabled: true,
      panEnabled: true,
      controlIconsEnabled: false,
      dblClickZoomEnabled: true,
      mouseWheelZoomEnabled: true,
      preventMouseEventsDefault: true,
      zoomScaleSensitivity: 0.18,
      minZoom: 0.2,
      maxZoom: 24,
      fit: true,
      contain: true,
      center: true,
      refreshRate: "auto",
    });
    mermaidPanZoomInstances.set(svg, panZoom);

    shell.querySelector(".mermaid-zoom-in")?.addEventListener("click", () => panZoom.zoomIn());
    shell.querySelector(".mermaid-zoom-out")?.addEventListener("click", () => panZoom.zoomOut());
    shell.querySelector(".mermaid-reset")?.addEventListener("click", () => {
      panZoom.resetZoom();
      panZoom.center();
      panZoom.fit();
    });
    shell.querySelector(".mermaid-panzoom-fullscreen")?.addEventListener("click", () => {
      shell.classList.toggle("is-fullscreen");
      setTimeout(() => {
        panZoom.resize();
        panZoom.fit();
        panZoom.center();
      }, 80);
    });
  });
}

async function initMermaid(root = document) {
  if (!window.mermaid) return;
  initMermaidConfig();

  const diagrams = Array.from(root.querySelectorAll(".mermaid:not([data-processed='true'])"));
  if (diagrams.length === 0) return;

  try {
    await mermaid.run({ nodes: diagrams });
    initMermaidPanZoom(root);
    console.log(`✓ Mermaid.js и svg-pan-zoom инициализированы (${diagrams.length})`);
  } catch (error) {
    console.error("Mermaid render error", error);
  }
}

function reinitLibsAfterHTMX(event) {
  const root = event.detail.elt;
  initHighlightJS(root);
  initMermaid(root);

  if (window.initCopyButtons) {
    window.initCopyButtons();
  }
}

window.initHighlightJS = initHighlightJS;
window.initMermaid = initMermaid;
window.initMermaidPanZoom = initMermaidPanZoom;
window.reinitLibsAfterHTMX = reinitLibsAfterHTMX;
