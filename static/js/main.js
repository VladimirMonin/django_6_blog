// static/js/main.js
/**
 * Главный инициализатор всех frontend модулей
 */

document.addEventListener("DOMContentLoaded", function () {
  console.log("🚀 Инициализация frontend модулей...");

  // Инициализация библиотек
  if (window.initHighlightJS) initHighlightJS();
  if (window.initMermaid) initMermaid();

  // Проверяем наличие markdown контента
  const markdownContent = document.querySelector(".markdown-content");
  if (!markdownContent) {
    console.log("ℹ️ Markdown контент не найден на странице");
    return;
  }

  // Инициализируем модули для markdown страниц
  if (window.enableFullscreenImages) enableFullscreenImages();
  if (window.initMediaPlayers) initMediaPlayers();
  if (window.generateTableOfContents) generateTableOfContents();
  if (window.initDynamicBreadcrumbs) initDynamicBreadcrumbs();

  console.log("✨ Frontend модули инициализированы");
});

// HTMX интеграция
document.body.addEventListener("htmx:afterSwap", function (event) {
  console.log("🔄 HTMX контент обновлен, реинициализация...");
  if (window.reinitLibsAfterHTMX) {
    reinitLibsAfterHTMX(event);
  }
});
