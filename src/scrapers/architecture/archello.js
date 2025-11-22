// --- JS SCRAPER: ARCHELLO COMPANIES DATA COLLECTION ---
// Скрипт собирает данные архитектурных компаний с Archello

// =================================================================================================
// 1. КОНФИГУРАЦИЯ
// =================================================================================================

const Municipality = 'Vila Franca de Xira'; 
const CURRENT_CITY = 'Vila_Franca_de_Xira';
const CURRENT_PAGE = prompt("Введите номер страницы (например, 1):");

const SELECTORS = {
    // --- СЕЛЕКТОРЫ СТРАНИЦЫ СПИСКА КОМПАНИЙ ---
    COMPANY_CONTAINER: 'div.brand-content__grid-item',       
    LINK_SELECTOR: 'div.short-item__bottom-brand a.text-dark[href^="/brand/"]', 
    DESCRIPTION: 'div.short-item__bottom-description',                    
    
    // --- СЕЛЕКТОРЫ СТРАНИЦЫ КОМПАНИИ ---
    COMPANY_NAME: 'h1.profile-name span.font-weight-bold',                    
    ADDRESS: 'div.company-address',       
    PHONE: 'div.company-phone', 
    WEBSITE: 'a.company-website',        
    SUMMARY: 'div.profile-description',             
    PORTFOLIO: '#brand-projects-grid',                 
    MUNICIPALITY: 'span.company-location',               
};

// =================================================================================================
// 2. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
// =================================================================================================

// Безопасное извлечение текста
const safeText = (selector, parent = document) => {
    const el = parent.querySelector(selector);
    return el ? el.textContent.trim().replace(/\s\s+/g, ' ') : null;
};

// Безопасное извлечение атрибута href
const safeHref = (selector, parent = document) => {
    const el = parent.querySelector(selector);
    return el ? el.getAttribute('href') : null;
};

function hasValidDescription(container) {
    const description = container.querySelector(SELECTORS.DESCRIPTION);
    if (!description) return true; // Если описания нет - все равно собираем
    
    const text = description.textContent.trim().toLowerCase();
    return !text.includes('no description available');
}
// Извлечение проектов портфолио
const extractPortfolio = (parent = document) => {
    // Находим контейнер портфолио
    const portfolioContainer = parent.querySelector(SELECTORS.PORTFOLIO);
    if (!portfolioContainer) return null;
    
    // Находим все карточки проектов
    const projectElements = portfolioContainer.querySelectorAll('.grid-item__card-col');
    if (!projectElements.length) return null;
    
    const projects = Array.from(projectElements).map(project => {
        // Ищем название проекта в <b> внутри grid-item-description
        const description = project.querySelector('.grid-item-description');
        if (!description) return null;
        
        const name = description.querySelector('b')?.textContent?.trim();
        const link = description.querySelector('a')?.getAttribute('href');
        const fullLink = link ? new URL(link, window.location.href).href : null;
        
        return name && fullLink ? `${name}: ${fullLink}` : null;
    }).filter(project => project); // Убираем null
    
    return projects.length > 0 ? projects.join(' | ') : null;
};

// Функция для извлечения адреса
function extractAddress(parent = document) {
    const infoElements = parent.querySelectorAll('.grid-item-info-content');
    
    for (const element of infoElements) {
        const text = element.textContent.trim().toLowerCase();
        
        // Ищем элементы, содержащие географические указатели
        if (text.includes('portugal') || 
            text.includes('lisboa') || 
            text.includes('porto') ||
            text.includes('faro') ||
            text.match(/[a-z]+,\s*[a-z]+/i)) { // Формат "город, страна"
            return element.textContent.trim();
        }
    }
    return null;
}

// Функция для извлечения телефона
function extractPhone(parent = document) {
    const infoElements = parent.querySelectorAll('.grid-item-info-content');
    
    for (const element of infoElements) {
        const text = element.textContent.trim();
        
        // Ищем телефонные форматы
        if (text.match(/^[\+]?[\d\s\-\(\)]{7,}$/) || // Международный формат
            text.match(/^(\+351|00351)?\s*\d{9}$/) || // Португальский формат
            text.match(/\(\+\d+\)/)) { // Формат с кодом страны
            return text;
        }
    }
    return null;
}

function extractWebsite(parent = document) {
    const link = parent.querySelector('.grid-item-info-content a[href^="http"]');
    return link ? link.getAttribute('href') : null;
}

const convertToCSV = (data) => {
    if (data.length === 0) return '';
    
    const headers = Object.keys(data[0]);
    const csvRows = [];
    csvRows.push(headers.join(';'));
    
    for (const row of data) {
        const values = headers.map(header => {
            const val = row[header] || '';
            return `"${String(val).replace(/"/g, '""').replace(/\n/g, ' ')}"`;
        });
        csvRows.push(values.join(';'));
    }
    return csvRows.join('\n');
};

const downloadCSV = (csv, filename) => {
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement("a");
    
    if (link.download !== undefined) {
        const url = URL.createObjectURL(blob);
        link.setAttribute("href", url);
        link.setAttribute("download", filename);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        console.log(`✅ Файл ${filename} успешно скачан.`);
    }
};

// =================================================================================================
// 3. ОСНОВНАЯ ЛОГИКА СКРАПИНГА
// =================================================================================================

async function scrapeArchelloCompanies() {
    console.log(`--- Начинаю сбор данных компаний для ${CURRENT_CITY}, Страница ${CURRENT_PAGE} ---`);
    const mainListURL = window.location.href; 
    const companyData = [];

    // 3.1. Извлечение ссылок на компании со страницы списка
        const companyContainers = document.querySelectorAll(SELECTORS.COMPANY_CONTAINER);

        const companyURLs = Array.from(companyContainers)
            .filter(container => hasValidDescription(container))
            .map(container => {
                const link = container.querySelector(SELECTORS.LINK_SELECTOR);
                if (link) {
                    const relativeUrl = link.getAttribute('href');
                    return new URL(relativeUrl, window.location.href).href;
                }
                return null;
            })
            .filter(url => url !== null);

        console.log(`Найдено компаний: ${companyContainers.length}`);
        console.log(`После фильтрации: ${companyURLs.length}`);
        console.log(`Отфильтровано: ${companyContainers.length - companyURLs.length} компаний без описания`);
    
    // 3.2. Детальный сбор данных с каждой страницы компании
    for (const url of companyURLs) {
        
        // Задержка между запросами
        await new Promise(r => setTimeout(r, Math.random() * 2000 + 1000)); 
        
        try {
            const response = await fetch(url);
            const htmlText = await response.text();
            const doc = new DOMParser().parseFromString(htmlText, 'text/html');
            
            // --- Сбор данных компании ---
            const data = {
                company_name: safeText(SELECTORS.COMPANY_NAME, doc),
                address: extractAddress(doc),
                phone: extractPhone(doc),
                website: extractWebsite(doc),
                municipality: Municipality,
                general_summary: safeText(SELECTORS.SUMMARY, doc),
                portfolio: extractPortfolio(doc),
                data_source: 'Archello',
                company_url: url,
                scraped_city: CURRENT_CITY,
                scraped_page: CURRENT_PAGE,
                scraped_at: new Date().toISOString()
            };
            
            companyData.push(data);
            console.log(`✅ Собрана компания: ${data.company_name || 'без названия'}`);

        } catch (error) {
            console.error(`❌ Ошибка при сборе данных компании с ${url}: ${error.message}`);
            companyData.push({
                company_url: url, 
                error: error.message,
                data_source: 'Archello',
                scraped_city: CURRENT_CITY
            });
        }
    }
    
    // 3.3. Сохранение в CSV
    if (companyData.length > 0) {
        const csv = convertToCSV(companyData);
        const filename = `archello_companies_${CURRENT_CITY}_page${CURRENT_PAGE}.csv`;
        downloadCSV(csv, filename);
        
        // Финальный отчет
        console.log(`=== ОТЧЕТ ===`);
        console.log(`✅ Успешно собрано: ${companyData.filter(item => !item.error).length} компаний`);
        console.log(`❌ Ошибок: ${companyData.filter(item => item.error).length}`);
        console.log(`💾 Файл: ${filename}`);
    } else {
        console.warn("⚠️ Не удалось собрать данные компаний.");
    }
}

// Запуск скрапера
scrapeArchelloCompanies();