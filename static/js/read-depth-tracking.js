/**
 * Read-depth tracking: sends scroll progress to a public API endpoint.
 * Only activates on post detail pages (.post-content).
 */
function initReadDepthTracking() {
  var content = document.querySelector('.post-content');
  if (!content) return;

  var slug = document.querySelector('article[data-post-slug]');
  if (!slug) return;
  var postSlug = slug.getAttribute('data-post-slug');

  var maxDepth = 0;
  var sentDepth = 0;
  var ticking = false;
  var trackedThresholds = { read_50: false, read_90: false };

  function trackThresholds(depth) {
    var trackGoal = window.trackMetrikaGoal;
    if (typeof trackGoal !== 'function') return;
    [['read_50', 0.5], ['read_90', 0.9]].forEach(function (threshold) {
      if (!trackedThresholds[threshold[0]] && depth >= threshold[1]) {
        trackedThresholds[threshold[0]] = true;
        trackGoal(threshold[0], {
          page_path: window.location.pathname,
          content_kind: 'post',
        });
      }
    });
  }

  function calculateDepth() {
    var rect = content.getBoundingClientRect();
    var contentHeight = content.offsetHeight;
    var viewportHeight = window.innerHeight;

    // How far we've scrolled into the content
    var scrolledInto = Math.max(0, -rect.top);
    // Maximum scrollable within content
    var scrollable = Math.max(1, contentHeight - viewportHeight);
    var depth = Math.min(1, scrolledInto / scrollable);
    return depth;
  }

  function onScroll() {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(function() {
      var depth = calculateDepth();
      if (depth > maxDepth) maxDepth = depth;
      trackThresholds(maxDepth);
      ticking = false;
    });
  }

  // Send read depth on page unload or visibility change
  function sendDepth() {
    if (maxDepth <= sentDepth + 0.1) return; // only send if meaningfully increased
    var depthToSend = Math.round(maxDepth * 100) / 100;

    var data = JSON.stringify({ read_depth: depthToSend });
    var url = '/api/v1/posts/' + postSlug + '/read-depth/';

    // Use sendBeacon if available (works on unload)
    if (navigator.sendBeacon) {
      var blob = new Blob([data], { type: 'application/json' });
      navigator.sendBeacon(url, blob);
    } else {
      // Fallback to fetch
      fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: data,
        keepalive: true,
      }).catch(function() {});
    }
    sentDepth = depthToSend;
  }

  window.addEventListener('scroll', onScroll, { passive: true });
  document.addEventListener('visibilitychange', function() {
    if (document.visibilityState === 'hidden') sendDepth();
  });
  window.addEventListener('beforeunload', sendDepth);

  // Also send periodically (every 15 seconds)
  setInterval(sendDepth, 15000);
}

window.initReadDepthTracking = initReadDepthTracking;