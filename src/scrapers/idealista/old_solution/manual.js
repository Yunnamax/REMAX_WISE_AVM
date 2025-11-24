// --- JS SCRAPER: IDEALISTA MANUAL DATA COLLECTION (FINAL - С АДРЕСОМ) ---
// Скрипт собирает 11 параметров (включая listing_id и location_address) с одной страницы.

// =================================================================================================
// 1. КОНФИГУРАЦИЯ (ОБЯЗАТЕЛЬНО ЗАМЕНИТЕ ПЕРЕД ЗАПУСКОМ)
// =================================================================================================

//const CURRENT_CITY = prompt("Введите название города (например, Lisboa):"); 
const CURRENT_CITY = 'vila_nova_de_gaia';
const CURRENT_PAGE = prompt("Введите номер страницы (например, 5):");

const SELECTORS = {
    // --- ПАРАМЕТРЫ СТРАНИЦЫ СПИСКА (ВАШИ ОРИГИНАЛЬНЫЕ) ---
    LISTING_CONTAINER: 'div.item-info-container',       
    LINK_SELECTOR: 'a.item-link',                     
    
    // --- СЕЛЕКТОРЫ СТРАНИЦЫ ОБЪЯВЛЕНИЯ (ВАШИ ОРИГИНАЛЬНЫЕ) ---
    PRICE: 'span.info-data-price',                    
    AREA: 'div.info-features span:nth-child(1)',       
    LAND_STATUS: 'div.info-features span:nth-child(2)', 
    AGENT_NAME: 'p.about-advertiser-name',        
    DESCRIPTION: 'div.adCommentsLanguage',             
    ENERGY_CERT: 'div.details-property-feature-two div.details-property_features:last-of-type li span', 
    UPDATE_DATE: 'p.date-update-text',                 
    TITLE: 'span.main-info__title-main',               
    
    // *** НОВЫЙ СЕЛЕКТОР ДЛЯ АДРЕСА (ЗАМЕНЯЕТ КООРДИНАТЫ) ***
    LOCATION_ADDRESS: 'span.main-info__title-minor', 
};

// =================================================================================================
// 2. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
// =================================================================================================

// Безопасное извлечение текста
const safeText = (selector, parent = document) => {
    const el = parent.querySelector(selector);
    return el ? el.textContent.trim().replace(/\s\s+/g, ' ') : null;
};

// Извлечение Listing ID из URL
const extractListingId = (url) => {
    // Ищет последовательность цифр (\d+) между /imovel/ и следующим /
    const match = url.match(/\/imovel\/(\d+)\//); 
    // Если формат /imovel/ID/ найден
    return match ? match[1] : null;
};


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
// 3. ОСНОВНАЯ ЛОГИКА СКРАПИНГА СТРАНИЦЫ
// =================================================================================================

async function scrapePageAndDownload() {
    console.log(`--- Начинаю сбор данных для ${CURRENT_CITY}, Страница ${CURRENT_PAGE} ---`);
    const mainListURL = window.location.href; 
    const listingData = [];

    // 3.1. Извлечение ссылок со страницы списка
    const listingContainers = document.querySelectorAll(SELECTORS.LISTING_CONTAINER);
    
    const listingURLs = Array.from(listingContainers).map(container => {
        const link = container.querySelector(SELECTORS.LINK_SELECTOR);
        return link ? new URL(link.getAttribute('href'), mainListURL).href : null;
    }).filter(url => url !== null);

    console.log(`Найдено ${listingURLs.length} ссылок. Начинаю детальный скрапинг...`);
    
    
    // 3.2. Детальный сбор данных с помощью Fetch (AJAX)
    
    for (const url of listingURLs) {
        
        // Задержка между запросами (Этика)
        await new Promise(r => setTimeout(r, Math.random() * 3000 + 1000)); 
        
        try {
            const response = await fetch(url);
            const htmlText = await response.text();
            const doc = new DOMParser().parseFromString(htmlText, 'text/html');
            
            // --- Сбор данных ---
            const data = {
                listing_id: extractListingId(url),
                listing_url: url,
                scraped_city: CURRENT_CITY,
                scraped_page: CURRENT_PAGE,
                
                scraped_title: safeText(SELECTORS.TITLE, doc),
                scraped_price: safeText(SELECTORS.PRICE, doc),
                area_sqm: safeText(SELECTORS.AREA, doc),
                land_status: safeText(SELECTORS.LAND_STATUS, doc),
                agent_name: safeText(SELECTORS.AGENT_NAME, doc),
                description_text: safeText(SELECTORS.DESCRIPTION, doc),
                energy_certificate: safeText(SELECTORS.ENERGY_CERT, doc),
                update_date: safeText(SELECTORS.UPDATE_DATE, doc),
                
                // *** НОВЫЙ ПАРАМЕТР ***
                location_address: safeText(SELECTORS.LOCATION_ADDRESS, doc), 
            };
            
            listingData.push(data);
            console.log(` Succesfully collected ID: ${data.listing_id}`);

        } catch (error) {
            console.error(` Ошибка при сборе деталей с ${url}: ${error.message}`);
            listingData.push({listing_id: extractListingId(url), listing_url: url, error: error.message});
        }
    }
    
    // 3.3. Сохранение
    if (listingData.length > 0) {
        const csv = convertToCSV(listingData);
        const filename = `idealista_land_${CURRENT_CITY}_page${CURRENT_PAGE}.csv`;
        downloadCSV(csv, filename);
    } else {
        console.warn(" На странице не найдено ссылок или не удалось собрать данные.");
    }
}

scrapePageAndDownload();