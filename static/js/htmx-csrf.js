// static/js/htmx-csrf.js
/**
 * Настройка CSRF токена для HTMX запросов
 */

document.body.addEventListener("htmx:configRequest", (event) => {
  const csrfToken = document.querySelector('meta[name="csrf-token"]');
  if (csrfToken) {
    event.detail.headers["X-CSRFToken"] = csrfToken.content;
  }
});

console.log("✓ HTMX CSRF настроен");
