// static/js/fullscreen-images.js
/**
 * Lightbox — полноценный просмотр изображений
 * Клик по картинке в .markdown-content → открытие лайтбокса с:
 *   • плавной анимацией открытия/закрытия
 *   • навигацией с клавиатуры (← → Esc)
 *   • кнопками prev / next / close
 *   • счётчиком "2 / 5"
 *   • кликом по фону для закрытия
 *   • циклическим перебором всех картинок страницы
 */

function enableFullscreenImages() {
  const images = Array.from(document.querySelectorAll(".markdown-content img"));
  if (images.length === 0) {
    console.log("ℹ️ Изображения для lightbox не найдены");
    return;
  }

  const lightbox = new Lightbox(images);
  lightbox.attach();

  console.log(`✓ Lightbox включён, изображений: ${images.length}`);
}

class Lightbox {
  constructor(images) {
    this.images = images;
    this.currentIndex = 0;
    this.isOpen = false;
    this._lastFocused = null;
    this._onKeydown = this._onKeydown.bind(this);

    this._build();
  }

  /* ---------- DOM ---------- */

  _build() {
    const overlay = document.createElement("div");
    overlay.className = "lightbox-overlay";
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", "true");
    overlay.setAttribute("aria-label", "Просмотр изображения");
    overlay.tabIndex = -1;

    overlay.innerHTML = `
      <button type="button" class="lightbox-close" aria-label="Закрыть">
        <svg viewBox="0 0 24 24" width="28" height="28" aria-hidden="true">
          <path fill="currentColor" d="M18.3 5.7L12 12l6.3 6.3-1.4 1.4L10.6 13.4 4.3 19.7 2.9 18.3 9.2 12 2.9 5.7 4.3 4.3l6.3 6.3 6.3-6.3 1.4 1.4z"/>
        </svg>
      </button>
      <button type="button" class="lightbox-prev" aria-label="Предыдущее изображение">
        <svg viewBox="0 0 24 24" width="32" height="32" aria-hidden="true">
          <path fill="currentColor" d="M15.4 7.4L10.8 12l4.6 4.6-1.4 1.4L8 12l6.6-6.6z"/>
        </svg>
      </button>
      <button type="button" class="lightbox-next" aria-label="Следующее изображение">
        <svg viewBox="0 0 24 24" width="32" height="32" aria-hidden="true">
          <path fill="currentColor" d="M8.6 7.4L13.2 12l-4.6 4.6 1.4 1.4L16 12 9.4 5.4z"/>
        </svg>
      </button>
      <figure class="lightbox-container">
        <img class="lightbox-img" alt="" />
        <figcaption class="lightbox-caption"></figcaption>
      </figure>
      <div class="lightbox-counter"></div>
    `;

    document.body.appendChild(overlay);

    this.overlay = overlay;
    this.imgEl = overlay.querySelector(".lightbox-img");
    this.captionEl = overlay.querySelector(".lightbox-caption");
    this.counterEl = overlay.querySelector(".lightbox-counter");
    this.closeBtn = overlay.querySelector(".lightbox-close");
    this.prevBtn = overlay.querySelector(".lightbox-prev");
    this.nextBtn = overlay.querySelector(".lightbox-next");
    this.container = overlay.querySelector(".lightbox-container");
  }

  /* ---------- Bind ---------- */

  attach() {
    this.images.forEach((img, idx) => {
      img.style.cursor = "pointer";
      img.dataset.lightboxIndex = idx;
      img.addEventListener("click", () => this.open(idx));
    });

    this.closeBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      this.close();
    });
    this.prevBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      this.prev();
    });
    this.nextBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      this.next();
    });

    // Клик по фону закрывает, клик по картинке/контейнеру — нет
    this.overlay.addEventListener("click", (e) => {
      if (
        e.target === this.overlay ||
        e.target === this.imgEl ||
        e.target === this.container
      ) {
        // клик прямо по картинке тоже закрываем как в популярных лайтбоксах
        if (e.target === this.imgEl) return;
        this.close();
      }
    });
  }

  /* ---------- Open / Close ---------- */

  open(index) {
    this._lastFocused = document.activeElement;
    this.currentIndex = index;
    this.isOpen = true;
    this._render();

    this.overlay.classList.add("active");
    document.body.style.overflow = "hidden";
    document.addEventListener("keydown", this._onKeydown);

    // фокус на overlay для доступности
    requestAnimationFrame(() => this.overlay.focus());
  }

  close() {
    if (!this.isOpen) return;
    this.isOpen = false;

    this.overlay.classList.remove("active");
    this.overlay.classList.add("closing");
    document.body.style.overflow = "";
    document.removeEventListener("keydown", this._onKeydown);

    const finish = () => {
      this.overlay.classList.remove("closing");
      this.overlay.removeEventListener("transitionend", finish);
      if (this._lastFocused && this._lastFocused.focus) this._lastFocused.focus();
    };
    this.overlay.addEventListener("transitionend", finish);
    // Подстраховка, если transitionend не сработает
    setTimeout(finish, 320);
  }

  /* ---------- Navigation ---------- */

  prev() {
    this.currentIndex =
      (this.currentIndex - 1 + this.images.length) % this.images.length;
    this._render();
  }

  next() {
    this.currentIndex = (this.currentIndex + 1) % this.images.length;
    this._render();
  }

  /* ---------- Render ---------- */

  _render() {
    const img = this.images[this.currentIndex];
    const src = img.dataset.fullSrc || img.src;
    const alt = img.alt || img.title || "";
    const caption = img.title || img.getAttribute("data-caption") || "";

    this.imgEl.src = src;
    this.imgEl.alt = alt;
    this.captionEl.textContent = caption;
    this.captionEl.style.display = caption ? "" : "none";

    this.counterEl.textContent = `${this.currentIndex + 1} / ${this.images.length}`;

    // Скрываем кнопки, если всего одно изображение
    const single = this.images.length <= 1;
    this.prevBtn.style.display = single ? "none" : "";
    this.nextBtn.style.display = single ? "none" : "";
  }

  /* ---------- Keyboard ---------- */

  _onKeydown(e) {
    switch (e.key) {
      case "ArrowLeft":
        e.preventDefault();
        this.prev();
        break;
      case "ArrowRight":
        e.preventDefault();
        this.next();
        break;
      case "Escape":
        e.preventDefault();
        this.close();
        break;
    }
  }
}

window.enableFullscreenImages = enableFullscreenImages;