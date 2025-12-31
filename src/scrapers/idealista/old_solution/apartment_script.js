// --- JS SCRAPER: IDEALISTA MANUAL DATA COLLECTION (FINAL - С АДРЕСОМ) ---
// Скрипт собирает 11 параметров (включая listing_id и location_address) с одной страницы.

// =================================================================================================
// 1. КОНФИГУРАЦИЯ (ОБЯЗАТЕЛЬНО ЗАМЕНИТЕ ПЕРЕД ЗАПУСКОМ)
// =================================================================================================

//const CURRENT_CITY = prompt("Введите название города (например, Lisboa):"); 
const CURRENT_CITY = 'lisbon';
const CURRENT_PAGE = prompt("Введите номер страницы (например, 5):");
  
const SELECTORS = {
    // --- ПАРАМЕТРЫ СТРАНИЦЫ СПИСКА (ВАШИ ОРИГИНАЛЬНЫЕ) ---
    LISTING_CONTAINER: 'div.item-info-container',       
    LINK_SELECTOR: 'a.item-link',                     
    
    // --- СЕЛЕКТОРЫ СТРАНИЦЫ ОБЪЯВЛЕНИЯ (ВАШИ ОРИГИНАЛЬНЫЕ) ---
    PRICE: 'span.info-data-price',                    
    AREA: '.details-property-feature-one .details-property_features:first-of-type ul li:nth-child(1)',
    CONDITION: '.details-property-feature-one .details-property_features:first-of-type ul li:nth-child(4)',
    NUM_BEDROOMS: '.details-property-feature-one .details-property_features:first-of-type ul li:nth-child(2)', // "T1"
    NUM_BATHROOMS: '.details-property-feature-one .details-property_features:first-of-type ul li:nth-child(3)', // "1 bathroom"
    FURNISHED: '.details-property-feature-one .details-property_features:first-of-type ul li:nth-child(5)', // "Furnished..."
    FLOOR_NUMBER: '.details-property-feature-one .details-property_features:nth-of-type(2) ul li:nth-child(1)', // "Ground floor"
    HAS_ELEVATOR: '.details-property-feature-one .details-property_features:nth-of-type(2) ul li:nth-child(2)', // "No lift"
    AGENT_NAME: '.about-advertiser-name, .professional-name span:not(.name), .professional-name .particular',        
    DESCRIPTION: '.adCommentsLanguage p',             
    ENERGY_CERT: 'div.details-property-feature-two div.details-property_features:last-of-type li span', 
    UPDATE_DATE: 'p.date-update-text',                 
    TITLE: 'span.main-info__title-main',               
    
    // *** НОВЫЙ СЕЛЕКТОР ДЛЯ АДРЕСА (ЗАМЕНЯЕТ КООРДИНАТЫ) ***
    LOCATION_ADDRESS: '#headerMap .header-map-list', 
};

// =================================================================================================
// 2. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
// =================================================================================================

// Безопасное извлечение текста
const safeText = (selector, parent = document) => {
    const elements = parent.querySelectorAll(selector);
    if (elements.length > 0) {
        // Для адреса объединяем все элементы
        if (selector === '#headerMap .header-map-list') {
            return Array.from(elements).map(el => el.textContent.trim()).join(', ');
        }
        return elements[0].textContent.trim().replace(/\s\s+/g, ' ');
    }
    return null;
};

// Извлечение Listing ID из URL
const extractListingId = (url) => {
    // Ищет последовательность цифр (\d+) между /imovel/ и следующим /
    const match = url.match(/\/imovel\/(\d+)\//); 
    // Если формат /imovel/ID/ найден
    return match ? match[1] : null;
};

function extractFloorFromBuildingSection(doc) {
    // Находим заголовок "Building"
    const buildingHeader = Array.from(doc.querySelectorAll('h2.details-property-h2'))
        .find(header => header.textContent.trim() === 'Building');
    
    if (buildingHeader) {
        // Находим следующий блок с features после заголовка Building
        let nextElement = buildingHeader.nextElementSibling;
        while (nextElement && !nextElement.classList.contains('details-property_features')) {
            nextElement = nextElement.nextElementSibling;
        }
        
        if (nextElement) {
            // Ищем в списке элементы с упоминанием этажа
            const listItems = nextElement.querySelectorAll('li');
            for (const item of listItems) {
                const text = item.textContent.toLowerCase();
                if (text.includes('floor') || text.includes('ground') || text.includes('st') || text.includes('nd') || text.includes('rd') || text.includes('th')) {
                    return item.textContent.trim();
                }
            }
        }
    }
    return null;
}

// Основная функция для использования в data mapping
function extractFloorInfo(doc) {
    // Приоритет 1: Building секция (точная информация)
    const buildingFloor = extractFloorFromExactSection(doc, 'Building');
    if (buildingFloor) return buildingFloor;
    
    // Приоритет 2: Basic features через "floor area" (косвенная информация)
    const basicFeaturesFloor = extractFloorFromBasicFeatures(doc);
    if (basicFeaturesFloor) return basicFeaturesFloor;
    
    return null;
}

// Вспомогательная функция 1 - для Building секции
function extractFloorFromExactSection(doc, sectionName) {
    const header = Array.from(doc.querySelectorAll('h2.details-property-h2'))
        .find(h => h.textContent.trim() === sectionName);
    
    if (header) {
        let nextElement = header.nextElementSibling;
        while (nextElement && !nextElement.classList.contains('details-property_features')) {
            nextElement = nextElement.nextElementSibling;
        }
        
        if (nextElement) {
            const listItems = nextElement.querySelectorAll('li');
            for (const item of listItems) {
                const text = item.textContent.toLowerCase();
                // Строгая проверка на этаж (исключаем лифт и другие поля)
                if ((text.includes('floor') && !text.includes('lift')) ||
                    /ground floor|\d+(st|nd|rd|th) floor/.test(text)) {
                    return item.textContent.trim();
                }
            }
        }
    }
    return null;
}

// Вспомогательная функция 2 - для Basic features
function extractFloorFromBasicFeatures(doc) {
    const header = Array.from(doc.querySelectorAll('h2.details-property-h2'))
        .find(h => h.textContent.trim() === 'Basic features');
    
    if (header) {
        let nextElement = header.nextElementSibling;
        while (nextElement && !nextElement.classList.contains('details-property_features')) {
            nextElement = nextElement.nextElementSibling;
        }
        
        if (nextElement) {
            const listItems = nextElement.querySelectorAll('li');
            for (const item of listItems) {
                const text = item.textContent.toLowerCase();
                if (text.includes('floor area')) {
                    return "Ground floor"; // предположение для floor area
                }
            }
        }
    }
    return null;
}


    // Улучшенная функция для спален
    function extractBedroomsImproved(doc) {
        const descriptionText = safeText(SELECTORS.DESCRIPTION, doc);
        if (!descriptionText) return null;
        
        // 1. Сначала ищем T-обозначения
        const tPattern = /T[0-6]/i;
        const tMatch = descriptionText.match(tPattern);
        if (tMatch) {
            return tMatch[0];
        }
        
        // 2. Ищем явные числовые указания
        const explicitPattern = /(\d+\s*bedroom|\d+\s*bedrooms|\bone\s*bedroom|\btwo\s*bedrooms|\bthree\s*bedrooms|\bfour\s*bedrooms|\bfive\s*bedrooms|\bsix\s*bedrooms)/i;
        const explicitMatch = descriptionText.match(explicitPattern);
        if (explicitMatch) {
            return explicitMatch[0].trim();
        }
        
        // 3. Анализируем контекст - если есть "bedroom" в единственном числе, считаем что 1 спальня
        const text = descriptionText.toLowerCase();
        
        // Если есть "bedroom" (единственное число) и нет множественного
        if (text.includes('bedroom') && !text.includes('bedrooms')) {
            // Проверяем контекст - если упоминается в контексте описания комнат
            const bedroomContext = /(bedroom|bed room|room)/i;
            if (bedroomContext.test(descriptionText)) {
                return "1 bedroom"; // Предполагаем одну спальню
            }
        }
        
        // 4. Ищем другие указания на количество спален
        const bedroomIndicators = [
            'double bedroom', 'single bedroom', 'master bedroom', 
            'bedroom with', 'bedroom and', 'bedroom,'
        ];
        
        for (const indicator of bedroomIndicators) {
            if (text.includes(indicator)) {
                return "bedroom mentioned"; // Упоминание спальни без точного количества
            }
        }
        
        return null;
    }

function extractBedroomsComprehensive(doc) {
    // Места, где может быть информация о спальнях (в порядке приоритета)
    const searchLocations = [
        {
            selector: '.details-property-feature-one .details-property_features:first-of-type ul li:nth-child(2)',
            description: 'Basic features (позиция T-обозначения)'
        },
        {
            selector: 'span.main-info__title-main',
            description: 'Заголовок объявления'
        },
        {
            selector: '.adCommentsLanguage p',
            description: 'Описание'
        },
        {
            selector: '.details-property-feature-one .details-property_features ul li',
            description: 'Все Basic features'
        }
    ];

    // Ключевые слова для поиска спален
    const bedroomKeywords = [
        'T0', 'T1', 'T2', 'T3', 'T4', 'T5', 'T6',
        'bedroom', 'bedrooms', 'bed', 'beds',
        'one bedroom', 'two bedrooms', 'three bedrooms', 'four bedrooms',
        'double bedroom', 'single bedroom', 'master bedroom'
    ];

    // 1. Поиск по селекторам (структурированные данные)
    for (const location of searchLocations) {
        const elements = doc.querySelectorAll(location.selector);
        for (const element of elements) {
            const text = element.textContent.trim();
            const lowerText = text.toLowerCase();
            
            // Ищем T-обозначения
            const tMatch = text.match(/T[0-6]/i);
            if (tMatch) {
                console.log(`Найдены спальни в ${location.description}: ${tMatch[0]}`);
                return tMatch[0];
            }
            
            // Ищем ключевые слова
            for (const keyword of bedroomKeywords) {
                if (lowerText.includes(keyword.toLowerCase())) {
                    console.log(`Найдены спальни в ${location.description}: ${text}`);
                    
                    // Если нашли число + bedrooms, возвращаем как есть
                    const numberMatch = text.match(/(\d+\s*bedroom|\d+\s*bedrooms)/i);
                    if (numberMatch) {
                        return numberMatch[0].trim();
                    }
                    
                    // Если нашли текстовое упоминание
                    const textMatch = text.match(/(one|two|three|four)\s*bedrooms?/i);
                    if (textMatch) {
                        return textMatch[0].trim();
                    }
                    
                    // Если просто нашли ключевое слово
                    return text;
                }
            }
        }
    }

    // 2. Расширенный поиск по контексту в описании
    const descriptionText = safeText(SELECTORS.DESCRIPTION, doc);
    if (descriptionText) {
        const lowerDesc = descriptionText.toLowerCase();
        
        // Анализ контекста - если есть "bedroom" в единственном числе
        if (lowerDesc.includes('bedroom') && !lowerDesc.includes('bedrooms')) {
            // Проверяем, что это именно описание спальни, а не общее слово
            const bedroomContext = /(bedroom|bed room|room)(?:\s+with|\s+and|\s+has|\s+featuring)/i;
            if (bedroomContext.test(descriptionText)) {
                console.log('Найдена спальня по контексту в описании');
                return "1 bedroom (context)";
            }
        }
        
        // Поиск косвенных указаний
        const indirectIndicators = [
            'double bedroom', 'master bedroom', 'bedroom with', 'bedroom and'
        ];
        for (const indicator of indirectIndicators) {
            if (lowerDesc.includes(indicator)) {
                console.log(`Найдены спальни по индикатору: ${indicator}`);
                return "bedroom mentioned";
            }
        }
    }

    console.log('Спальни не найдены');
    return null;
}

// Функция для поиска конкретного значения в блоках
function extractSpecificValue(doc, keywords) {
    // Ищем во всех блоках с деталями
    const sections = doc.querySelectorAll('.details-property .details-property_features');
    
    for (const section of sections) {
        const listItems = section.querySelectorAll('li');
        for (const item of listItems) {
            const text = item.textContent.toLowerCase();
            for (const keyword of keywords) {
                if (text.includes(keyword.toLowerCase())) {
                    return item.textContent.trim();
                }
            }
        }
    }
    return null;
}

// Функция для этажа (ТОЛЬКО из структурированных блоков)
function extractFloorNumber(doc) {
    return extractSpecificValue(doc, ['ground floor', 'first', 'second', 'third', 'floor']);
}

// Функция для лифта (ТОЛЬКО из структурированных блоков)
function extractElevator(doc) {
    return extractSpecificValue(doc, ['lift', 'elevator', 'with lift', 'no lift']);
}

// Функция для ванных (ТОЛЬКО из структурированных блоков)
function extractBathrooms(doc) {
    return extractSpecificValue(doc, ['bathroom', 'bathrooms']);
}

// Функция для furnished (ищем в нескольких местах)
function extractFurnished(doc) {
    // Сначала ищем в структурированных блоках
    const fromStructured = extractSpecificValue(doc, ['furnished', 'unfurnished', 'partially furnished']);
    if (fromStructured) return fromStructured;
    
    // Если не нашли, ищем в описании
    const descriptionText = safeText(SELECTORS.DESCRIPTION, doc);
    if (descriptionText) {
        const text = descriptionText.toLowerCase();
        if (text.includes('furnished')) return 'furnished';
        if (text.includes('unfurnished')) return 'unfurnished';
    }
    
    return null;
}

function debugEnergyCertificate(doc) {
    console.log('=== Energy Certificate Debug ===');
    
    // Выводим все элементы с title
    const elementsWithTitle = doc.querySelectorAll('[title]');
    elementsWithTitle.forEach((el, index) => {
        console.log(`Element ${index}:`, {
            tag: el.tagName,
            class: el.className,
            title: el.getAttribute('title')
        });
    });
    
    return extractEnergyCertificate(doc);
}

// Функция для энергетического сертификата (через классы)
function extractEnergyCertificate(doc) {
    try {
        // 1. Ищем все span с атрибутом title
        const spansWithTitle = doc.querySelectorAll('span[title]');
        
        for (const span of spansWithTitle) {
            const title = span.getAttribute('title');
            
            // 2. Ищем энергетический рейтинг в title (A+, A, B, C, D, E, F)
            if (title && /^[a-f]\+?$/i.test(title.trim())) {
                return title.trim().toUpperCase(); // "a+" → "A+", "c" → "C"
            }
        }
        
        // 3. Проверяем "In process"
        if (doc.body.textContent.includes('In process')) {
            return 'In process';
        }
        
        return null;
        
    } catch (error) {
        console.error('Error extracting energy certificate:', error);
        return null;
    }
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
                // Основные идентификаторы
                listing_id: extractListingId(url),
                listing_url: url,
                
                // Основная информация
                title: safeText(SELECTORS.TITLE, doc),
                description: safeText(SELECTORS.DESCRIPTION, doc),
                agent_name: safeText(SELECTORS.AGENT_NAME, doc),
                location_address: safeText(SELECTORS.LOCATION_ADDRESS, doc),
                municipality: CURRENT_CITY,
                
                // Характеристики недвижимости (ТОЧНЫЕ значения)
                condition: extractSpecificValue(doc, ['new', 'good', 'renovated', 'second hand', 'condition']) || "not indicated",
                furnished: extractFurnished(doc) || "not indicated", 
                num_bedrooms: extractBedroomsComprehensive(doc) || "not indicated",
                num_bathrooms: extractBathrooms(doc) || "not indicated", // ТОЛЬКО из структурированных блоков
                floor_number: extractFloorInfo(doc) || "unknown", // ТОЛЬКО из структурированных блоков
                has_elevator: extractElevator(doc) || "not indicated", // ТОЛЬКО из структурированных блоков
                
                // Финансовые параметры
                scraped_price: safeText(SELECTORS.PRICE, doc),
                area_sqm: safeText(SELECTORS.AREA, doc) || "not indicated",
                energy_certificate: extractEnergyCertificate(doc) || "not indicated",
                
                // Временные метки
                scraped_at: new Date().toISOString(),
                update_date: safeText(SELECTORS.UPDATE_DATE, doc)
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
        const filename = `idealista_apartments_${CURRENT_CITY}_page${CURRENT_PAGE}.csv`;
        downloadCSV(csv, filename);
    } else {
        console.warn(" На странице не найдено ссылок или не удалось собрать данные.");
    }
}

scrapePageAndDownload();