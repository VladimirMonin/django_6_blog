// static/js/back-to-top.js
/**
 * Detail-only progressive enhancement for the SSR return-to-top anchor.
 * The link remains a normal #post-start navigation target without JavaScript.
 */
(function () {
  "use strict";

  function rectsIntersect(first, second) {
    return (
      first.left < second.right &&
      first.right > second.left &&
      first.top < second.bottom &&
      first.bottom > second.top
    );
  }

  function initBackToTop() {
    const control = document.querySelector("[data-back-to-top]");
    const target = document.getElementById("post-start");
    const actions = document.querySelector(".post-detail-bottom-actions");
    if (!control || !target) return;

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    let animationFrame = 0;
    let returnAnimationFrame = 0;
    let returning = false;

    function setHidden(hidden) {
      control.classList.toggle("is-visible", !hidden);
      control.setAttribute("aria-hidden", String(hidden));
      if (hidden) {
        control.setAttribute("tabindex", "-1");
      } else {
        control.removeAttribute("tabindex");
      }
    }

    function isLightboxOpen() {
      const lightbox = document.querySelector(".lightbox-overlay");
      return Boolean(
        lightbox &&
          (lightbox.classList.contains("active") ||
            lightbox.classList.contains("closing"))
      );
    }

    function overlapsBottomActions() {
      if (!actions) return false;
      return rectsIntersect(
        control.getBoundingClientRect(),
        actions.getBoundingClientRect()
      );
    }

    function updateVisibility() {
      const pastThreshold = window.scrollY >= window.innerHeight;
      const shouldHide =
        !returning && (!pastThreshold || isLightboxOpen() || overlapsBottomActions());
      setHidden(shouldHide);
    }

    function scheduleUpdate() {
      if (animationFrame) return;
      animationFrame = window.requestAnimationFrame(function () {
        animationFrame = 0;
        updateVisibility();
      });
    }

    function completeReturn() {
      if (!returning) return;
      returning = false;
      if (returnAnimationFrame) {
        window.cancelAnimationFrame(returnAnimationFrame);
        returnAnimationFrame = 0;
      }
      target.focus({ preventScroll: true });
      scheduleUpdate();
    }

    function waitForReturn(startScrollY, hasMoved, stableFrames, frames) {
      if (!returning) return;

      const currentScrollY = window.scrollY;
      const moved = hasMoved || Math.abs(currentScrollY - startScrollY) > 1;
      const nextStableFrames = moved && Math.abs(currentScrollY - startScrollY) < 1
        ? stableFrames + 1
        : 0;

      if (reducedMotion.matches || (moved && nextStableFrames >= 3) || frames >= 240) {
        completeReturn();
        return;
      }

      returnAnimationFrame = window.requestAnimationFrame(function () {
        waitForReturn(currentScrollY, moved, nextStableFrames, frames + 1);
      });
    }

    control.classList.add("is-enhanced");
    setHidden(true);
    window.addEventListener("scroll", scheduleUpdate, { passive: true });
    window.addEventListener("resize", scheduleUpdate, { passive: true });

    const lightbox = document.querySelector(".lightbox-overlay");
    if (lightbox) {
      new MutationObserver(scheduleUpdate).observe(lightbox, {
        attributes: true,
        attributeFilter: ["class"],
      });
    }

    control.addEventListener("click", function (event) {
      event.preventDefault();
      returning = true;
      setHidden(false);
      window.history.pushState(null, "", "#post-start");
      target.scrollIntoView({
        behavior: reducedMotion.matches ? "auto" : "smooth",
        block: "start",
      });
      window.addEventListener("scrollend", completeReturn, { once: true });
      waitForReturn(window.scrollY, false, 0, 0);
    });

    scheduleUpdate();
  }

  document.addEventListener("DOMContentLoaded", initBackToTop);
})();
