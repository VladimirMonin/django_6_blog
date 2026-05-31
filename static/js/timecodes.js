// static/js/timecodes.js
/**
 * Clickable media timecodes for audio/video posts.
 * Buttons use data-seek-seconds and data-timecode-target to seek the matching player.
 */

function initTimecodeButtons(root = document) {
  root.querySelectorAll(".timecode-button[data-seek-seconds]").forEach((button) => {
    if (button.dataset.timecodeBound === "true") return;
    button.dataset.timecodeBound = "true";

    button.addEventListener("click", () => {
      const seconds = Number(button.dataset.seekSeconds || 0);
      const targetName = button.dataset.timecodeTarget || "post-media-player";
      const player = root.querySelector(`[data-timecode-player="${targetName}"]`) || document.querySelector(`[data-timecode-player="${targetName}"]`);
      if (!player || Number.isNaN(seconds)) return;

      player.currentTime = seconds;
      player.focus({ preventScroll: true });
      const playResult = player.play?.();
      if (playResult && typeof playResult.catch === "function") {
        playResult.catch(() => {
          // Browsers may block autoplay before explicit media interaction. Seeking still works.
        });
      }

      root.querySelectorAll(".timecode-button.is-active").forEach((activeButton) => {
        activeButton.classList.remove("is-active");
      });
      button.classList.add("is-active");
    });
  });
}

window.initTimecodeButtons = initTimecodeButtons;

document.addEventListener("DOMContentLoaded", () => initTimecodeButtons());
document.body?.addEventListener("htmx:afterSwap", (event) => initTimecodeButtons(event.detail.elt));
