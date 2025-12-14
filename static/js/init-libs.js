// static/js/init-libs.js
/**
 * Инициализация библиотек подсветки кода и диаграмм
 * - Highlight.js для code blocks
 * - Mermaid.js для UML диаграмм
 */

function initHighlightJS() {
  hljs.highlightAll();
  console.log("✓ Highlight.js инициализирован");
}

function initMermaid() {
  mermaid.initialize({
    startOnLoad: true,
    theme: "default",
    securityLevel: "loose",
  });
  console.log("✓ Mermaid.js инициализирован");
}

// Повторная инициализация после HTMX загрузки
function reinitLibsAfterHTMX(event) {
  // Подсветка новых code blocks
  event.detail.elt.querySelectorAll("pre code").forEach((block) => {
    hljs.highlightElement(block);
  });

  // Рендер новых Mermaid диаграмм
  const mermaidBlocks = event.detail.elt.querySelectorAll(".mermaid");
  if (mermaidBlocks.length > 0) {
    mermaid.run({
      querySelector: ".mermaid",
    });
  }

  // Добавляем copy-button к новым блокам
  if (window.initCopyButtons) {
    window.initCopyButtons();
  }
}

// Экспортируем функции
window.initHighlightJS = initHighlightJS;
window.initMermaid = initMermaid;
window.reinitLibsAfterHTMX = reinitLibsAfterHTMX;
