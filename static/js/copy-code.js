/**
 * Copy-button для code blocks
 * 
 * Добавляет кнопку "Копировать" в каждый блок кода.
 * Совместим с HTMX динамической подгрузкой.
 */

(function() {
    'use strict';
    
    /**
     * Создает кнопку копирования для блока кода
     */
    function createCopyButton(codeBlock) {
        const button = document.createElement('button');
        button.className = 'copy-button';
        button.innerHTML = '<i class="bi bi-clipboard"></i>';
        button.setAttribute('aria-label', 'Копировать код');
        button.setAttribute('title', 'Копировать код');
        
        button.addEventListener('click', function() {
            copyCode(codeBlock, button);
        });
        
        return button;
    }
    
    /**
     * Копирует код в буфер обмена
     */
    function copyCode(codeBlock, button) {
        const code = codeBlock.textContent;
        
        if (navigator.clipboard && window.isSecureContext) {
            // Современный API (требует HTTPS или localhost)
            navigator.clipboard.writeText(code).then(function() {
                showSuccess(button);
            }).catch(function(err) {
                console.error('Ошибка копирования:', err);
                fallbackCopy(code, button);
            });
        } else {
            // Fallback для HTTP
            fallbackCopy(code, button);
        }
    }
    
    /**
     * Fallback метод копирования для HTTP
     */
    function fallbackCopy(text, button) {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        textArea.style.top = '-999999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        
        try {
            const successful = document.execCommand('copy');
            if (successful) {
                showSuccess(button);
            } else {
                showError(button);
            }
        } catch (err) {
            console.error('Fallback: Ошибка копирования', err);
            showError(button);
        }
        
        document.body.removeChild(textArea);
    }
    
    /**
     * Показывает успешное копирование
     */
    function showSuccess(button) {
        const originalHTML = button.innerHTML;
        button.innerHTML = '<i class="bi bi-check2"></i>';
        button.classList.add('copied');
        
        setTimeout(function() {
            button.innerHTML = originalHTML;
            button.classList.remove('copied');
        }, 2000);
    }
    
    /**
     * Показывает ошибку копирования
     */
    function showError(button) {
        const originalHTML = button.innerHTML;
        button.innerHTML = '<i class="bi bi-x"></i>';
        button.classList.add('error');
        
        setTimeout(function() {
            button.innerHTML = originalHTML;
            button.classList.remove('error');
        }, 2000);
    }
    
    /**
     * Добавляет кнопки копирования ко всем блокам кода
     */
    function initCopyButtons() {
        // Находим все pre > code блоки (исключая inline код)
        const codeBlocks = document.querySelectorAll('pre code');
        
        codeBlocks.forEach(function(codeBlock) {
            const pre = codeBlock.parentElement;
            
            // Пропускаем если это не обычный pre (например, если это часть .mermaid)
            if (pre.classList.contains('mermaid') || pre.parentElement.classList.contains('mermaid')) {
                return;
            }
            
            // Проверяем, что кнопка еще не добавлена
            if (pre.querySelector('.copy-button')) {
                return;
            }
            
            // Оборачиваем pre в контейнер для позиционирования кнопки
            if (!pre.classList.contains('code-block-wrapper')) {
                const wrapper = document.createElement('div');
                wrapper.className = 'code-block-wrapper';
                pre.parentNode.insertBefore(wrapper, pre);
                wrapper.appendChild(pre);
            }
            
            // Добавляем кнопку
            const button = createCopyButton(codeBlock);
            pre.appendChild(button);
        });
    }
    
    // Инициализация при загрузке страницы
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initCopyButtons);
    } else {
        initCopyButtons();
    }
    
    // Экспортируем функцию для HTMX
    window.initCopyButtons = initCopyButtons;
    
})();
