// --- GOOGLE MAPS SCRAPER ---

// =================================================================================================
// 1. КОНФИГУРАЦИЯ
// =================================================================================================

const CURRENT_CITY = prompt("Введите название города для поиска в Google Maps (например, Lisbon):");

const SELECTORS = {
    // --- СТРАНИЦА РЕЗУЛЬТАТОВ ПОИСКА GOOGLE MAPS ---
    LISTING_CONTAINER: 'div.Nv2PK', 
    LINK_SELECTOR: 'a.hfpxzc', 
    
    // --- СТРАНИЦА КОМПАНИИ В GOOGLE MAPS ---  
    COMPANY_NAME: 'h1.DUwDvf',
    ADDRESS: 'button[data-item-id="address"]',
    PHONE: 'div.Io6YTe.fontBodyMedium',
    WEBSITE_LINK: 'a.CsEnBe[href*="http"]',
    WEBSITE_TEXT: 'div.Io6YTe.fontBodyMedium',
    Industry: 'button[jsaction*="category"]'
};

// =================================================================================================
// 2. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
// =================================================================================================

// Безопасное извлечение текста
const safeText = (selector, parent = document) => {
    const el = parent.querySelector(selector);
    return el ? el.textContent.trim().replace(/\s\s+/g, ' ') : null;
};

// Функция для извлечения телефона
function extractPhone(parent = document) {
    try {
        const phoneElements = parent.querySelectorAll(SELECTORS.PHONE);
        for (const el of phoneElements) {
            const text = el.textContent.trim();
            // Проверяем, что это телефон (содержит цифры и соответствует формату)
            if (text.match(/^[\+]?[\d\s\-\(\)]{8,}$/) && 
                !text.includes('@') && 
                text.length < 25) {
                return text;
            }
        }
    } catch (error) {
        console.error('Error extracting phone:', error);
    }
    return null;
}

// Функция для извлечения сайта на основе вашего примера
function extractWebsite(parent = document) {
    try {
        // Способ 1: Извлекаем из ссылки CsEnBe (ваш пример)
        const websiteLink = parent.querySelector(SELECTORS.WEBSITE_LINK);
        if (websiteLink) {
            const href = websiteLink.getAttribute('href');
            if (href && !href.includes('google.com') && !href.includes('g.co')) {
                return href;
            }
        }
        
        // Способ 2: Ищем текст сайта в элементах Io6YTe
        const textElements = parent.querySelectorAll(SELECTORS.WEBSITE_TEXT);
        for (const el of textElements) {
            const text = el.textContent.trim();
            // Проверяем, что это домен (содержит точку и нет пробелов)
            if (text.match(/[a-zA-Z0-9-]+\.[a-zA-Z]{2,}/) && 
                !text.includes(' ') && 
                !text.match(/[\d\s\-\(\)]{8,}/)) { // Исключаем телефоны
                return text.startsWith('http') ? text : `https://${text}`;
            }
        }
        
        // Способ 3: Ищем в data-item-id="authority" (из вашего примера)
        const authorityLink = parent.querySelector('a[data-item-id="authority"]');
        if (authorityLink) {
            const href = authorityLink.getAttribute('href');
            if (href) return href;
        }
        
    } catch (error) {
        console.error('Error extracting website:', error);
    }
    return null;
}

// Улучшенная функция для безопасного извлечения
const safeExtract = (extractFunction, parent = document, maxAttempts = 2) => {
    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
        try {
            const result = extractFunction(parent);
            if (result) return result;
            
            // Ждем перед повторной попыткой (на случай динамической загрузки)
            if (attempt < maxAttempts) {
                return new Promise(resolve => setTimeout(() => {
                    resolve(extractFunction(parent));
                }, 1000));
            }
        } catch (error) {
            console.warn(`Attempt ${attempt} failed:`, error.message);
        }
    }
    return null;
};

// Функция для ожидания появления элемента
const waitForElement = (selector, timeout = 5000) => {
    return new Promise((resolve, reject) => {
        const startTime = Date.now();
        const checkElement = () => {
            const element = document.querySelector(selector);
            if (element) {
                resolve(element);
            } else if (Date.now() - startTime > timeout) {
                reject(new Error(`Element ${selector} not found within ${timeout}ms`));
            } else {
                setTimeout(checkElement, 100);
            }
        };
        checkElement();
    });
};

// ФУНКЦИЯ ДЛЯ ОПРЕДЕЛЕНИЯ КОНЦА СПИСКА
function hasReachedEndOfList() {
    // Ищем различные варианты сообщения о конце списка
    const endOfListIndicators = [
        // Английские сообщения
        'You\'ve reached the end of the list',
        'End of list',
        'No more results',
        'Showing top results',
        
        // Португальские сообщения (если сайт на португальском)
        'Você chegou ao final da lista',
        'Fim da lista',
        'Sem mais resultados',
        
        // Классы и атрибуты, которые могут указывать на конец списка
        '[class*="end-of-list"]',
        '[class*="no-more-results"]',
        '[class*="section-limit-title"]',
        '[class*="results-limit"]',
        '[aria-label*="end of list"]',
        '[aria-label*="no more results"]'
    ];
    
    // Проверяем по тексту
    for (const text of endOfListIndicators) {
        if (text.includes('class') || text.includes('aria-label')) {
            // Это селектор
            const element = document.querySelector(text);
            if (element) {
                console.log('Found end of list element:', element.textContent);
                return true;
            }
        } else {
            // Это текст для поиска
            const elements = document.querySelectorAll('*');
            for (const el of elements) {
                if (el.textContent && el.textContent.includes(text)) {
                    console.log('Found end of list text:', el.textContent);
                    return true;
                }
            }
        }
    }
    
    // Дополнительная проверка: если видим много компаний, но новые не грузятся
    const companyCount = document.querySelectorAll(SELECTORS.LISTING_CONTAINER).length;
    if (companyCount > 0) {
        // Проверяем, есть ли элемент, который выглядит как индикатор конца
        const possibleEndElements = document.querySelectorAll('div, span, p');
        for (const el of possibleEndElements) {
            const text = el.textContent || '';
            if (text && (
                text.includes('end') && text.includes('list') ||
                text.includes('fim') && text.includes('lista') ||
                text.includes('no more') ||
                text.includes('sem mais')
            )) {
                console.log('Found potential end indicator:', text);
                return true;
            }
        }
    }
    
    return false;
}

// Функция для автоматического скролла и загрузки всех результатов
const autoScroll = async () => {
    console.log('Starting optimized auto-scroll for Google Maps...');
    
    let previousCompanyCount = 0;
    let scrollAttempts = 0;
    const maxAttempts = 150;
    let consecutiveNoNewResults = 0;
    const maxConsecutiveNoNewResults = 5;

    while (scrollAttempts < maxAttempts && consecutiveNoNewResults < maxConsecutiveNoNewResults) {
        // Проверяем наличие сообщения о конце списка ДО прокрутки
        if (hasReachedEndOfList()) {
            console.log('✅ Reached the end of the list!');
            break;
        }
        
        const companyCountBefore = document.querySelectorAll(SELECTORS.LISTING_CONTAINER).length;
        
        // Прокручиваем более агрессивно
        const scrollHeight = document.documentElement.scrollHeight;
        const currentScroll = window.pageYOffset || document.documentElement.scrollTop;
        const scrollStep = 800;
        
        // Прокручиваем несколькими шагами
        for (let scrollPos = currentScroll; scrollPos < scrollHeight; scrollPos += scrollStep) {
            window.scrollTo(0, scrollPos);
            await new Promise(resolve => setTimeout(resolve, 500));
            
            // Проверяем конец списка после каждого шага
            if (hasReachedEndOfList()) {
                console.log('✅ Reached the end of the list during step scroll!');
                break;
            }
        }
        
        // Финальная прокрутка до самого конца
        window.scrollTo(0, document.documentElement.scrollHeight);
        
        // Увеличиваем время ожидания для медленных соединений
        await new Promise(resolve => setTimeout(resolve, 4000));
        
        // Проверяем количество компаний ПОСЛЕ прокрутки
        const currentCompanyCount = document.querySelectorAll(SELECTORS.LISTING_CONTAINER).length;
        
        console.log(`Scroll attempt ${scrollAttempts + 1}: ${currentCompanyCount} companies (was ${companyCountBefore})`);
        
        // Проверяем конец списка снова
        if (hasReachedEndOfList()) {
            console.log('✅ Reached the end of the list after scroll!');
            break;
        }
        
        // Если количество компаний не изменилось
        if (currentCompanyCount === companyCountBefore) {
            consecutiveNoNewResults++;
            console.log(`No new companies loaded (${consecutiveNoNewResults}/${maxConsecutiveNoNewResults})`);
            
            // Попробуем альтернативный метод скролла
            if (consecutiveNoNewResults >= 2) {
                await alternativeScrollMethod();
            }
        } else {
            consecutiveNoNewResults = 0;
        }
        
        scrollAttempts++;
        previousCompanyCount = currentCompanyCount;
    }
    
    const finalCompanyCount = document.querySelectorAll(SELECTORS.LISTING_CONTAINER).length;
    console.log(`Auto-scroll completed. Total companies loaded: ${finalCompanyCount}`);
};

// АЛЬТЕРНАТИВНЫЙ МЕТОД СКРОЛЛА ДЛЯ СЛОЖНЫХ СЛУЧАЕВ
async function alternativeScrollMethod() {
    console.log('Trying alternative scroll method...');
    
    // Метод 1: Прокрутка с помощью клавиш Page Down
    document.body.focus();
    for (let i = 0; i < 5; i++) {
        document.dispatchEvent(new KeyboardEvent('keydown', {
            key: 'PageDown',
            keyCode: 34,
            which: 34
        }));
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        if (hasReachedEndOfList()) break;
    }
    
    // Метод 2: Прокрутка к определенным элементам
    const containers = document.querySelectorAll(SELECTORS.LISTING_CONTAINER);
    if (containers.length > 0) {
        // Прокручиваем к последним элементам
        const lastElements = Array.from(containers).slice(-10);
        for (const el of lastElements) {
            el.scrollIntoView({ behavior: 'smooth', block: 'center' });
            await new Promise(resolve => setTimeout(resolve, 500));
            
            if (hasReachedEndOfList()) break;
        }
    }
}

// ФУНКЦИЯ ДЛЯ РУЧНОГО ОПРЕДЕЛЕНИЯ СЕЛЕКТОРА КОНЦА СПИСКА
function findEndOfListSelector() {
    console.log('=== Searching for end of list indicator ===');
    
    // Ищем все элементы с текстом о конце списка
    const allElements = document.querySelectorAll('*');
    const candidates = [];
    
    for (const el of allElements) {
        const text = el.textContent;
        if (text && (
            text.includes('end of list') ||
            text.includes('You\'ve reached') ||
            text.includes('No more') ||
            text.includes('Fim da lista') ||
            text.includes('Você chegou')
        )) {
            candidates.push({
                element: el,
                text: text,
                html: el.outerHTML,
                classes: el.className,
                tag: el.tagName
            });
        }
    }
    
    if (candidates.length > 0) {
        console.log('Found potential end of list indicators:', candidates);
        return candidates[0];
    }
    
    console.log('No end of list indicators found');
    return null;
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
// 3. ОСНОВНАЯ ЛОГИКА СКРАПИНГА GOOGLE MAPS
// =================================================================================================

async function scrapeGoogleMaps() {
    console.log(`--- Starting Google Maps data collection for ${CURRENT_CITY} ---`);
    
    // Сначала найдем селектор конца списка для отладки
    const endIndicator = findEndOfListSelector();
    if (endIndicator) {
        console.log('End of list indicator found:', endIndicator);
    }
    
    const listingData = [];

    // Шаг 1: Автоскролл для загрузки всех результатов
    await autoScroll();

    // Шаг 2: Сбор всех карточек компаний
    const listingContainers = document.querySelectorAll(SELECTORS.LISTING_CONTAINER);
    console.log(`Found ${listingContainers.length} companies after scrolling`);

    let collectedCount = 0;
    let failedCount = 0;

    // Шаг 3: Обработка каждой компании
    for (let i = 0; i < listingContainers.length; i++) {
        const container = listingContainers[i];
        
        try {
            // Прокручиваем к элементу для гарантии видимости
            container.scrollIntoView({ behavior: 'smooth', block: 'center' });
            
            // Ждем немного перед кликом
            await new Promise(r => setTimeout(r, 1000));
            
            // Кликаем на карточку компании
            const link = container.querySelector(SELECTORS.LINK_SELECTOR);
            if (!link) {
                console.log(`No link found for company ${i}`);
                failedCount++;
                continue;
            }
            
            link.click();
            
            // Ждем загрузки боковой панели с информацией о компании
            await new Promise(r => setTimeout(r, 2000));
            
            // Собираем данные из боковой панели
            const companyName = safeText(SELECTORS.COMPANY_NAME);
            const address = safeText(SELECTORS.ADDRESS);
            const industry = safeText(SELECTORS.Industry);
            
            // ИСПОЛЬЗУЕМ УЛУЧШЕННЫЕ ФУНКЦИИ ДЛЯ ТЕЛЕФОНА И САЙТА
            const phone = await safeExtract(extractPhone);
            const website = await safeExtract(extractWebsite);

            // Детальное логирование для отладки
            console.log('=== EXTRACTION RESULTS ===');
            console.log('Company:', companyName);
            console.log('Phone:', phone || 'NOT FOUND');
            console.log('Website:', website || 'NOT FOUND');

            const data = {
                company_name: companyName,
                industry: industry,
                address: address,
                phone: phone, // Будет null если не найден
                website: website, // Будет null если не найден
                municipality: CURRENT_CITY,
                data_source: 'Google Maps'
            };
            
            listingData.push(data);
            collectedCount++;
            console.log(`✓ Collected ${collectedCount}/${listingContainers.length}: ${companyName}`);

            // Задержка между обработкой компаний
            await new Promise(r => setTimeout(r, Math.random() * 2000 + 1000));
            
        } catch (error) {
            console.error(`Error processing company ${i}:`, error);
            failedCount++;
        }
    }
    
    // Финальный отчет
    console.log(`=== COLLECTION REPORT ===`);
    console.log(`✅ Successfully collected: ${collectedCount} companies`);
    console.log(`❌ Failed to collect: ${failedCount} companies`);
    console.log(`📊 Total processed: ${listingContainers.length} companies`);
    
    // Статистика по контактам
    const companiesWithPhone = listingData.filter(item => item.has_phone).length;
    const companiesWithWebsite = listingData.filter(item => item.has_website).length;
    console.log(`📞 Companies with phone: ${companiesWithPhone}/${collectedCount}`);
    console.log(`🌐 Companies with website: ${companiesWithWebsite}/${collectedCount}`);
    
    if (listingData.length > 0) {
        const csv = convertToCSV(listingData);
        const filename = `google_maps_${CURRENT_CITY.replace(/\s+/g, '_')}.csv`;
        downloadCSV(csv, filename);
    } else {
        console.warn("No companies were collected.");
    }
}

// Запуск скрапера
scrapeGoogleMaps();