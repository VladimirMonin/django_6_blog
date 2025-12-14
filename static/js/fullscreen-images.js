// static/js/fullscreen-images.js
/**
 * Фуллскрин просмотр изображений
 * Клик на изображение → оверлей на весь экран
 */

function enableFullscreenImages() {
  // Создаем оверлей контейнер
  const overlay = document.createElement("div");
  overlay.className = "fullscreen-img-container";
  document.body.appendChild(overlay);

  // Добавляем обработчики на все изображения в markdown контенте
  document.querySelectorAll(".markdown-content img").forEach((img) => {
    img.style.cursor = "pointer";
    img.addEventListener("click", () => showFullscreen(img.src, overlay));
  });

  // Закрытие по клику на оверлей
  overlay.addEventListener("click", () => {
    overlay.classList.remove("active");
  });

  console.log("✓ Fullscreen images включен");
}

function showFullscreen(src, overlay) {
  const img = new Image();
  img.src = src;

  img.onload = function () {
    const screenRatio = window.innerWidth / window.innerHeight;
    const imageRatio = this.width / this.height;

    if (imageRatio > screenRatio) {
      img.style.width = "100vw";
      img.style.height = "auto";
    } else {
      img.style.width = "auto";
      img.style.height = "100vh";
    }
  };

  overlay.innerHTML = "";
  overlay.appendChild(img);
  overlay.classList.add("active");
}

window.enableFullscreenImages = enableFullscreenImages;
