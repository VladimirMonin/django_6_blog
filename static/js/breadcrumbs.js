// static/js/breadcrumbs.js
/**
 * Динамические хлебные крошки
 * Отслеживают текущий H2/H3 при прокрутке
 * Dropdown меню для навигации по всем H2
 */

function initDynamicBreadcrumbs() {
    const breadcrumbsContainer = document.querySelector('.breadcrumbs-dynamic');
    if (!breadcrumbsContainer) return;
    
    const headings = Array.from(document.querySelectorAll('.markdown-content h2, .markdown-content h3'));
    if (headings.length === 0) return;
    
    // ВАЖНО: Добавляем ID к заголовкам (если нет)
    headings.forEach((heading, index) => {
        if (!heading.id) {
            const slug = heading.textContent
                .toLowerCase()
                .replace(/[^\w\s-]/g, '')
                .replace(/\s+/g, '-')
                .substring(0, 50);
            heading.id = `heading-${slug}-${index}`;
        }
    });
    
    // Собираем все H2 для dropdown
    const allH2 = headings.filter(h => h.tagName === 'H2');
    
    function updateBreadcrumbs() {
        // Находим текущий заголовок (который виден на экране)
        const scrollPosition = window.scrollY + 150; // Offset для точности
        
        let currentH2 = null;
        let currentH3 = null;
        
        for (const heading of headings) {
            const headingTop = heading.offsetTop;
            
            if (headingTop <= scrollPosition) {
                if (heading.tagName === 'H2') {
                    currentH2 = heading;
                    currentH3 = null; // Сбрасываем H3 при новом H2
                } else if (heading.tagName === 'H3' && currentH2) {
                    currentH3 = heading;
                }
            }
        }
        
        // Обновляем breadcrumbs
        breadcrumbsContainer.innerHTML = '';
        
        if (currentH2) {
            addBreadcrumbWithDropdown(breadcrumbsContainer, currentH2, allH2);
        }
        
        if (currentH3) {
            addBreadcrumb(breadcrumbsContainer, currentH3.textContent, currentH3.id, true);
        }
    }
    
    function addBreadcrumbWithDropdown(container, currentH2, allH2) {
        const wrapper = document.createElement('span');
        wrapper.className = 'breadcrumb-item breadcrumb-dropdown';
        
        const link = document.createElement('a');
        link.href = `#${currentH2.id}`;
        link.textContent = currentH2.textContent;
        link.className = 'text-decoration-none breadcrumb-h2-link';
        
        // Создаем dropdown меню
        const dropdown = document.createElement('div');
        dropdown.className = 'breadcrumb-dropdown-menu';
        
        // Добавляем небольшой padding для перекрытия gap
        dropdown.style.marginTop = '-2px';
        dropdown.style.paddingTop = '8px';
        
        allH2.forEach(h2 => {
            const dropdownItem = document.createElement('a');
            dropdownItem.href = `#${h2.id}`;
            dropdownItem.textContent = h2.textContent;
            dropdownItem.className = 'breadcrumb-dropdown-item';
            
            // Подсветка текущего пункта
            if (h2.id === currentH2.id) {
                dropdownItem.classList.add('active');
            }
            
            // Плавная прокрутка при клике
            dropdownItem.addEventListener('click', (e) => {
                e.preventDefault();
                h2.scrollIntoView({ behavior: 'smooth', block: 'start' });
                dropdown.classList.remove('show');
            });
            
            dropdown.appendChild(dropdownItem);
        });
        
        wrapper.appendChild(link);
        wrapper.appendChild(dropdown);
        
        // Показываем dropdown при наведении
        wrapper.addEventListener('mouseenter', () => {
            dropdown.classList.add('show');
        });
        
        wrapper.addEventListener('mouseleave', () => {
            dropdown.classList.remove('show');
        });
        
        // Плавная прокрутка для основной ссылки
        link.addEventListener('click', (e) => {
            e.preventDefault();
            currentH2.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
        
        container.appendChild(wrapper);
        
        // Добавляем separator
        const separator = document.createElement('span');
        separator.className = 'breadcrumb-separator';
        separator.textContent = ' / ';
        container.appendChild(separator);
    }
    
    function addBreadcrumb(container, text, id, isLast = false) {
        const item = document.createElement('span');
        item.className = 'breadcrumb-item';
        
        if (isLast) {
            item.textContent = text;
            item.classList.add('active');
        } else {
            const link = document.createElement('a');
            link.href = `#${id}`;
            link.textContent = text;
            link.className = 'text-decoration-none';
            
            // Плавная прокрутка
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const target = document.getElementById(id);
                if (target) {
                    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            });
            
            item.appendChild(link);
        }
        
        container.appendChild(item);
    }
    
    // Обновляем при прокрутке (с throttle)
    let ticking = false;
    window.addEventListener('scroll', () => {
        if (!ticking) {
            window.requestAnimationFrame(() => {
                updateBreadcrumbs();
                ticking = false;
            });
            ticking = true;
        }
    });
    
    // Начальное обновление
    updateBreadcrumbs();
    console.log(`✓ Dynamic breadcrumbs инициализированы (${allH2.length} H2 заголовков)`);
}

window.initDynamicBreadcrumbs = initDynamicBreadcrumbs;
