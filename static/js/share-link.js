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
    var copied = document.execCommand('copy');
    document.body.removeChild(textarea);
    return copied ? Promise.resolve() : Promise.reject(new Error('copy failed'));
  }

  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text);
    }
    return fallbackCopy(text);
  }

  function setButtonState(button, ok) {
    const label = button.querySelector('[data-share-label]');
    const feedback = button.querySelector('[data-share-feedback]');
    const icon = button.querySelector('i');
    const original = button.dataset.originalLabel || (label ? label.textContent : button.textContent).trim();
    const originalAriaLabel = button.dataset.originalAriaLabel || (
      button.getAttribute ? button.getAttribute('aria-label') : ''
    );
    button.dataset.originalLabel = original;
    button.dataset.originalAriaLabel = originalAriaLabel;

    if (label) {
      label.textContent = ok ? 'Ссылка скопирована' : 'Не удалось скопировать';
    }
    if (feedback) {
      feedback.textContent = ok ? 'Ссылка скопирована' : 'Не удалось скопировать ссылку';
    }
    if (button.setAttribute) {
      button.setAttribute('aria-label', ok ? 'Ссылка скопирована' : 'Не удалось скопировать ссылку');
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
      if (feedback) {
        feedback.textContent = '';
      }
      if (originalAriaLabel && button.setAttribute) {
        button.setAttribute('aria-label', originalAriaLabel);
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
          function () {
            setButtonState(button, true);
            if (typeof window.trackMetrikaGoal === 'function') {
              window.trackMetrikaGoal('share_copy', {
                page_path: window.location.pathname,
                content_kind: 'post',
              });
            }
          },
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
