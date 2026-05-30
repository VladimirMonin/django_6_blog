// static/js/breadcrumbs.js
/**
 * Sticky-навигация по статье.
 * Всегда показывает Главная / статья, а при прокрутке добавляет текущий H2/H3.
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
      const slug = heading.textContent
        .toLowerCase()
        .replace(/[^\w\s-]/g, "")
        .replace(/\s+/g, "-")
        .substring(0, 50);
      heading.id = `heading-${slug || "section"}-${index}`;
    }
  });

  const allH2 = headings.filter((h) => h.tagName === "H2");

  function renderSection(currentH2, currentH3) {
    if (!sectionSlot) return;
    sectionSlot.innerHTML = "";

    const current = currentH3 || currentH2;
    if (!current) return;

    if (currentH2 && allH2.length > 1) {
      sectionSlot.appendChild(createH2Dropdown(currentH2));
      if (currentH3) {
        sectionSlot.appendChild(createSeparator());
        sectionSlot.appendChild(createPlainItem(currentH3.textContent, currentH3.id, true));
      }
      return;
    }

    sectionSlot.appendChild(createPlainItem(current.textContent, current.id, true));
  }

  function createH2Dropdown(currentH2) {
    const wrapper = document.createElement("span");
    wrapper.className = "breadcrumb-item breadcrumb-dropdown";

    const link = document.createElement("a");
    link.href = `#${currentH2.id}`;
    link.textContent = currentH2.textContent;
    link.className = "text-decoration-none breadcrumb-h2-link";
    link.addEventListener("click", (event) => {
      event.preventDefault();
      currentH2.scrollIntoView({ behavior: "smooth", block: "start" });
    });

    const dropdown = document.createElement("div");
    dropdown.className = "breadcrumb-dropdown-menu";

    allH2.forEach((h2) => {
      const item = document.createElement("a");
      item.href = `#${h2.id}`;
      item.textContent = h2.textContent;
      item.className = "breadcrumb-dropdown-item";
      if (h2.id === currentH2.id) item.classList.add("active");
      item.addEventListener("click", (event) => {
        event.preventDefault();
        h2.scrollIntoView({ behavior: "smooth", block: "start" });
        dropdown.classList.remove("show");
      });
      dropdown.appendChild(item);
    });

    wrapper.addEventListener("mouseenter", () => dropdown.classList.add("show"));
    wrapper.addEventListener("mouseleave", () => dropdown.classList.remove("show"));
    wrapper.appendChild(link);
    wrapper.appendChild(dropdown);
    return wrapper;
  }

  function createPlainItem(text, id, isLast = false) {
    const item = document.createElement("span");
    item.className = "breadcrumb-item";
    if (isLast) item.classList.add("active");

    const link = document.createElement("a");
    link.href = `#${id}`;
    link.textContent = text;
    link.className = "text-decoration-none";
    link.addEventListener("click", (event) => {
      event.preventDefault();
      document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
    });

    if (isLast) {
      item.textContent = text;
    } else {
      item.appendChild(link);
    }
    return item;
  }

  function createSeparator() {
    const separator = document.createElement("span");
    separator.className = "breadcrumb-separator";
    separator.textContent = "/";
    return separator;
  }

  function updateBreadcrumbs() {
    const scrollPosition = window.scrollY + 170;
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
