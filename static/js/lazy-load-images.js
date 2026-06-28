/**
 * Lazy-load images inside .markdown-content.
 * Adds loading="lazy" + decoding="async" and fades in on load.
 */
function initLazyLoadImages() {
  var images = document.querySelectorAll('.markdown-content img');
  if (!images.length) return;

  images.forEach(function(img) {
    // Skip already-processed or SVG data URIs
    if (img.dataset.lazyProcessed) return;
    img.dataset.lazyProcessed = 'true';

    // Set native lazy loading
    img.setAttribute('loading', 'lazy');
    img.setAttribute('decoding', 'async');

    // Fade in on load
    if (img.complete) {
      img.classList.add('loaded');
    } else {
      img.addEventListener('load', function() {
        img.classList.add('loaded');
      });
      img.addEventListener('error', function() {
        img.classList.add('loaded'); // show broken image anyway
      });
    }
  });
}

// Expose for main.js
window.initLazyLoadImages = initLazyLoadImages;