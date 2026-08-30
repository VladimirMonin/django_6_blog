// Track successful HTMX history navigations as Yandex.Metrika virtual pageviews.
(function (window, document) {
  "use strict";

  const COUNTER_ID = 111929557;
  const historyEvents = [
    "htmx:pushedIntoHistory",
    "htmx:replacedInHistory",
    "htmx:historyRestore",
  ];
  let lastEffectiveUrl = removeHash(window.location.href);
  let lastUrl = window.location.href;

  function trackGoal(goalName, params) {
    if (typeof window.ym !== "function") return;
    try {
      window.ym(COUNTER_ID, "reachGoal", goalName, params || {});
    } catch (_error) {
      // Analytics must never interrupt user interactions.
    }
  }

  window.trackMetrikaGoal = trackGoal;

  document.addEventListener("htmx:afterSwap", function (event) {
    const root = event.target;
    const button = root && root.querySelector
      ? root.querySelector(".post-like-button[aria-pressed]")
      : null;
    if (!button) return;
    const goalName = button.getAttribute("aria-pressed") === "true"
      ? "post_like"
      : "post_unlike";
    trackGoal(goalName, {
      page_path: window.location.pathname,
      content_kind: "post",
    });
  });

  document.addEventListener("play", function (event) {
    const media = event.target;
    if (!media || (media.tagName !== "AUDIO" && media.tagName !== "VIDEO")) return;
    if (media.dataset.metrikaStartTracked === "true") return;
    media.dataset.metrikaStartTracked = "true";
    trackGoal("media_start", {
      page_path: window.location.pathname,
      content_kind: media.tagName.toLowerCase(),
    });
  }, true);

  function removeHash(url) {
    const parsed = new URL(url, window.location.href);
    parsed.hash = "";
    return parsed.href;
  }

  function trackHistoryNavigation() {
    const currentUrl = window.location.href;
    const currentEffectiveUrl = removeHash(currentUrl);
    if (currentEffectiveUrl === lastEffectiveUrl) return;

    const previousUrl = lastUrl;
    lastEffectiveUrl = currentEffectiveUrl;
    lastUrl = currentUrl;
    if (typeof window.ym !== "function") return;

    try {
      window.ym(COUNTER_ID, "hit", currentUrl, { referer: previousUrl });
    } catch (_error) {
      // Analytics must never interrupt HTMX navigation.
    }
  }

  historyEvents.forEach(function (eventName) {
    document.addEventListener(eventName, trackHistoryNavigation);
  });
})(window, document);