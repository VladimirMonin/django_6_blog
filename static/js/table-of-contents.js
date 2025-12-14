// static/js/table-of-contents.js
/**
 * Генерация оглавления из H2 и H3 заголовков
 */

function generateTableOfContents() {
  const tocContainer = document.getElementById("table-of-contents");
  if (!tocContainer) return;

  const headings = document.querySelectorAll(
    ".markdown-content h2, .markdown-content h3"
  );
  if (headings.length === 0) return;

  const tocList = document.createElement("ul");
  tocList.className = "list-unstyled";

  headings.forEach((heading, index) => {
    // Добавляем ID к заголовку (если нет)
    if (!heading.id) {
      heading.id = `heading-${index}`;
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
  console.log(`✓ TOC создано (${headings.length} заголовков)`);
}

window.generateTableOfContents = generateTableOfContents;
