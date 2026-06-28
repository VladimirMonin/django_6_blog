// static/js/reading-progress.js
/**
 * Reading progress bar
 * Тонкая жёлтая полоса вверху страницы, заполняется при прокрутке статьи.
 * Активируется только на страницах с элементом .post-content (детальные страницы постов).
 */

class ReadingProgress {
  constructor() {
    this.content = document.querySelector(".post-content");
    if (!this.content) return; // не активируем на списке/странице «О блоге»

    this.bar = document.createElement("div");
    this.bar.className = "reading-progress-bar";
    document.body.appendChild(this.bar);

    this._ticking = false;
    this._onScroll = this._onScroll.bind(this);
    window.addEventListener("scroll", this._onScroll, { passive: true });
    window.addEventListener("resize", this._onScroll, { passive: true });

    this.update();
    console.log("✓ Reading progress bar активирован");
  }

  _onScroll() {
    if (this._ticking) return;
    this._ticking = true;
    requestAnimationFrame(() => {
      this.update();
      this._ticking = false;
    });
  }

  update() {
    const rect = this.content.getBoundingClientRect();
    const total = rect.height - window.innerHeight;
    if (total <= 0) {
      // Контент помещается в один экран
      this.bar.style.width = "100%";
      return;
    }
    const scrolled = Math.min(Math.max(-rect.top, 0), total);
    const percent = (scrolled / total) * 100;
    this.bar.style.width = percent + "%";
  }

  destroy() {
    window.removeEventListener("scroll", this._onScroll);
    window.removeEventListener("resize", this._onScroll);
    if (this.bar && this.bar.parentNode) {
      this.bar.parentNode.removeChild(this.bar);
    }
  }
}

function initReadingProgress() {
  if (!document.querySelector(".post-content")) return null;
  return new ReadingProgress();
}

window.initReadingProgress = initReadingProgress;