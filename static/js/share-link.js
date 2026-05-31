(function () {
  function getShareButtons(root) {
    return Array.from((root || document).querySelectorAll('[data-share-copy]'));
  }

  function fallbackCopy(text) {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.setAttribute('readonly', '');
    textarea.style.position = 'fixed';
    textarea.style.left = '-9999px';
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);
    return Promise.resolve();
  }

  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text);
    }
    return fallbackCopy(text);
  }

  function setButtonState(button, ok) {
    const label = button.querySelector('[data-share-label]');
    const icon = button.querySelector('i');
    const original = button.dataset.originalLabel || (label ? label.textContent : button.textContent).trim();
    button.dataset.originalLabel = original;

    if (label) {
      label.textContent = ok ? 'Ссылка скопирована' : 'Не удалось скопировать';
    }
    button.classList.toggle('is-copied', ok);
    button.classList.toggle('is-copy-error', !ok);
    if (icon) {
      icon.className = ok ? 'bi bi-check2' : 'bi bi-exclamation-triangle';
    }

    window.setTimeout(function () {
      if (label) {
        label.textContent = original;
      }
      button.classList.remove('is-copied', 'is-copy-error');
      if (icon) {
        icon.className = 'bi bi-link-45deg';
      }
    }, 1800);
  }

  function bindShareButtons(root) {
    getShareButtons(root).forEach(function (button) {
      if (button.dataset.shareBound === 'true') {
        return;
      }
      button.dataset.shareBound = 'true';
      button.addEventListener('click', function () {
        const url = button.dataset.shareUrl;
        if (!url) {
          setButtonState(button, false);
          return;
        }
        copyText(url).then(
          function () { setButtonState(button, true); },
          function () { setButtonState(button, false); }
        );
      });
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    bindShareButtons(document);
  });
  document.body.addEventListener('htmx:afterSwap', function (event) {
    bindShareButtons(event.target);
  });
})();
