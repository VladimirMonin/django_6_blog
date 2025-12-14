// static/js/media-players.js
/**
 * Инициализация Plyr.io для видео и аудио
 */

function initMediaPlayers() {
  // Проверяем наличие Plyr
  if (typeof Plyr === "undefined") {
    console.warn("Plyr не загружен");
    return;
  }

  // Инициализация для видео
  const videoElements = document.querySelectorAll(".markdown-content video");
  videoElements.forEach((video) => {
    new Plyr(video, {
      controls: [
        "play-large",
        "play",
        "progress",
        "current-time",
        "duration",
        "mute",
        "volume",
        "settings",
        "fullscreen",
      ],
      settings: ["quality", "speed"],
      speed: { selected: 1, options: [0.5, 0.75, 1, 1.25, 1.5, 2] },
    });
  });

  // Инициализация для аудио
  const audioElements = document.querySelectorAll(".markdown-content audio");
  audioElements.forEach((audio) => {
    new Plyr(audio, {
      controls: [
        "play",
        "progress",
        "current-time",
        "duration",
        "mute",
        "volume",
        "settings",
      ],
      settings: ["speed"],
      speed: { selected: 1, options: [0.5, 0.75, 1, 1.25, 1.5, 2] },
    });
  });

  if (videoElements.length > 0 || audioElements.length > 0) {
    console.log(
      `✓ Plyr инициализирован (${videoElements.length} видео, ${audioElements.length} аудио)`
    );
  }
}

window.initMediaPlayers = initMediaPlayers;
