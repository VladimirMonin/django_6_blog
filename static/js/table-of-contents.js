// static/js/table-of-contents.js
/**
 * Сервер рендерит TOC, этот модуль только делает якорную прокрутку надежной.
 */

function initPostTocAnchors() {
  const toc = document.querySelector(".post-toc");
  if (!toc) return;

  toc.querySelectorAll('a[href^="#"]').forEach((link) => {
    link.addEventListener("click", (event) => {
      const rawId = link.getAttribute("href").slice(1);
      if (!rawId) return;

      const target = document.getElementById(rawId);
      if (!target) return;

      event.preventDefault();
      target.scrollIntoView({ behavior: "smooth", block: "start" });
      history.pushState(null, "", `#${rawId}`);
      target.setAttribute("tabindex", "-1");
      target.focus({ preventScroll: true });
    });
  });
}

function generateTableOfContents() {
  const tocContainer = document.getElementById("table-of-contents");
  if (!tocContainer) {
    initPostTocAnchors();
    return;
  }

  const headings = document.querySelectorAll(
    ".markdown-content h2, .markdown-content h3"
  );
  if (headings.length === 0) return;

  const tocList = document.createElement("ul");
  tocList.className = "list-unstyled";

  headings.forEach((heading, index) => {
    if (!heading.id) {
      heading.id = `post-section-${index + 1}`;
    }

    const tocItem = document.createElement("li");
    tocItem.className = heading.tagName === "H2" ? "mb-2" : "ms-3 mb-1";

    const tocLink = document.createElement("a");
    tocLink.href = `#${heading.id}`;
    tocLink.textContent = heading.textContent;
    tocLink.className = "text-decoration-none";

    tocItem.appendChild(tocLink);
    tocList.appendChild(tocItem);
  });

  tocContainer.appendChild(tocList);
  initPostTocAnchors();
  console.log(`✓ TOC создано (${headings.length} заголовков)`);
}

window.generateTableOfContents = generateTableOfContents;
window.initPostTocAnchors = initPostTocAnchors;
