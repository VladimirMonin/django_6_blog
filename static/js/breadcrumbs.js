// static/js/breadcrumbs.js
/**
 * Sticky breadcrumbs: neutral site path + compact in-article section trail.
 */

function initDynamicBreadcrumbs() {
  const breadcrumbsContainer = document.querySelector(".breadcrumbs-dynamic");
  if (!breadcrumbsContainer) return;

  const sectionSlot = breadcrumbsContainer.querySelector(".breadcrumbs-section");
  const headings = Array.from(
    document.querySelectorAll(".markdown-content h2, .markdown-content h3")
  );

  headings.forEach((heading, index) => {
    if (!heading.id) {
      heading.id = `post-section-${index + 1}`;
    }
  });

  function scrollToHeading(id) {
    const target = document.getElementById(id);
    if (!target) return;
    target.scrollIntoView({ behavior: "smooth", block: "start" });
    history.replaceState(null, "", `#${id}`);
  }

  function createSectionLink(heading, levelClass) {
    const link = document.createElement("a");
    link.href = `#${heading.id}`;
    link.textContent = heading.textContent;
    link.className = `article-section-link ${levelClass}`;
    link.addEventListener("click", (event) => {
      event.preventDefault();
      scrollToHeading(heading.id);
    });
    return link;
  }

  function createSectionSeparator() {
    const separator = document.createElement("span");
    separator.className = "article-section-separator";
    separator.textContent = "/";
    return separator;
  }

  function renderSection(currentH2, currentH3) {
    if (!sectionSlot) return;
    sectionSlot.innerHTML = "";
    sectionSlot.classList.toggle("is-empty", !currentH2 && !currentH3);

    if (!currentH2 && !currentH3) return;

    const label = document.createElement("span");
    label.className = "article-section-label";
    label.textContent = "В статье:";
    sectionSlot.appendChild(label);

    if (currentH2) {
      sectionSlot.appendChild(createSectionLink(currentH2, "article-section-link-h2"));
    }

    if (currentH2 && currentH3) {
      sectionSlot.appendChild(createSectionSeparator());
    }

    if (currentH3) {
      sectionSlot.appendChild(createSectionLink(currentH3, "article-section-link-h3"));
    }
  }

  function updateBreadcrumbs() {
    const scrollPosition = window.scrollY + 280;
    let currentH2 = null;
    let currentH3 = null;

    for (const heading of headings) {
      if (heading.offsetTop <= scrollPosition) {
        if (heading.tagName === "H2") {
          currentH2 = heading;
          currentH3 = null;
        } else if (heading.tagName === "H3") {
          currentH3 = heading;
        }
      }
    }

    renderSection(currentH2, currentH3);
  }

  let ticking = false;
  window.addEventListener("scroll", () => {
    if (!ticking) {
      window.requestAnimationFrame(() => {
        updateBreadcrumbs();
        ticking = false;
      });
      ticking = true;
    }
  });

  updateBreadcrumbs();
  console.log(`✓ Sticky breadcrumbs инициализированы (${headings.length} заголовков)`);
}

window.initDynamicBreadcrumbs = initDynamicBreadcrumbs;
