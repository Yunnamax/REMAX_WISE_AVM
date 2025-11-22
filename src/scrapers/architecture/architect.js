// --- JS SCRAPER: IDEALISTA MANUAL DATA COLLECTION (FINAL - С АДРЕСОМ) ---

// =================================================================================================
// 1. КОНФИГУРАЦИЯ (ОБЯЗАТЕЛЬНО ЗАМЕНИТЕ ПЕРЕД ЗАПУСКОМ)
// =================================================================================================

//const CURRENT_CITY = prompt("Введите название города (например, Lisboa):"); 
const CURRENT_CITY = 'porto';
const CURRENT_PAGE = prompt("Введите номер страницы (например, 5):");

const SELECTORS = {
    // --- ПАРАМЕТРЫ СТРАНИЦЫ СПИСКА (ВАШИ ОРИГИНАЛЬНЫЕ) ---
    LISTING_CONTAINER: 'div.article03-content',       
    LINK_SELECTOR: 'div.title03 a',                     
    
    // --- СЕЛЕКТОРЫ СТРАНИЦЫ ОБЪЯВЛЕНИЯ (ВАШИ ОРИГИНАЛЬНЫЕ) ---
    COMPANY_NAME: 'h1.title01.fn.localbusiness', // ⚠️ УТОЧНИТЬ!
    ADDRESS: '#situation', // ⚠️ УТОЧНИТЬ!
    SPECIALIZATION: 'table.table-datos-externos tr:nth-child(4) td.td-datos-externos span.category', // ⚠️ УТОЧНИТЬ!
    LEGAL_NAME: 'table.table-datos-externos:nth-of-type(2) tr:nth-child(1) td.td-datos-externos', // ⚠️ дублируем company_name
    GENERAL_SUMMARY: 'ul.list05b.collapsible-content > p:first-child'
};

const TARGET_MUNICIPALITIES = [
    'VILA FRANCA DE XIRA', 'ODIVELAS', 'SINTRA', 'SOBRAL DE MONTE AGRAÇO',
    'ALENQUER', 'ARRUDA DOS VINHOS', 'AZAMBUJA', 'MAFRA', 'CADAVAL',
    'MONTIJO', 'BARREIRO', 'TORRES VEDRAS', 'AMADORA', 'CASCAIS',
    'OEIRAS', 'LISBON', 'LOURINHÃ', 'LOURES', 'ALMADA', 'SEIXAL',
    'PALMELA', 'MOITA', 'SESIMBRA', 'ALCOCHETE', 'SETÚBAL'
].map(m => m.toUpperCase());

const ARCHITECTURAL_KEYWORDS = [
    'Architectural Activities', 
    'Arquitectura',
    'Arquitectos',
    'Architecture',
    'Architects',
    'Architectural',
    'Projectos de Arquitectura',
    'Planeamento e Arquitectura',
    'Promoção imobiliária',
    'desenvolvimento de projetos de edifícios',
    'Construção de edifícios'
].map(k => k.toLowerCase());

// =================================================================================================
// 2. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
// =================================================================================================

// Безопасное извлечение текста
const safeText = (selector, parent = document) => {
    const el = parent.querySelector(selector);
    return el ? el.textContent.trim().replace(/\s\s+/g, ' ') : null;
};

//НУЖНО ДОБАВИТЬ:
function extractMunicipality(address) {
    if (!address) return null;
    
    // Преобразование всех адресов в верхний регистр для сравнения
    const upperAddress = address.toUpperCase();
    
    // 1. Поиск прямого совпадения в адресе (используем наш целевой список)
    for (const targetCity of TARGET_MUNICIPALITIES) {
        // Проверяем, содержит ли сырой адрес название нашего целевого муниципалитета
        // Например, ищем "SINTRA" в адресе
        if (upperAddress.includes(targetCity.toUpperCase())) {
            
            // Если компания находится в LISBOA, но ее адрес также содержит CAMPOLIDE LISBOA,
            // мы должны вернуть именно LISBOA, поскольку это муниципалитет.
            
            // ВАЖНОЕ ИСПРАВЛЕНИЕ: Если нашли совпадение, возвращаем его.
            // (Возвращаем оригинальное название с корректным регистром для вывода в CSV)
            return targetCity.charAt(0) + targetCity.slice(1).toLowerCase(); // Например, "Lisbon"
        }
    }
    
    // 2. Если не найдено прямого совпадения, используем старую логику (по частям адреса)
    const parts = address.split(',').map(part => part.trim().toUpperCase());
    
    // Проверка последнего или предпоследнего элемента
    for (let i = 1; i <= 2 && parts.length >= i; i++) {
        const checkPart = parts[parts.length - i].replace(/\s/g, ''); // Удаляем пробелы
        
        for (const targetCity of TARGET_MUNICIPALITIES) {
            // Сравнение: Например, 'LISBOA' == 'LISBOA'
            if (checkPart.includes(targetCity.toUpperCase().replace(/\s/g, ''))) {
                 // Если найдено, возвращаем чистое название муниципалитета
                 return targetCity.charAt(0) + targetCity.slice(1).toLowerCase();
            }
        }
    }
    
    // Если ничего не совпало, компания пропускается
    return null;
}

function isArchitecturalCompany(specialization) {
    if (!specialization) return false;
    
    const specLower = specialization.toLowerCase();
    return ARCHITECTURAL_KEYWORDS.some(keyword => 
        specLower.includes(keyword)
    );
}

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
    console.log(`--- Starting data collection for ${CURRENT_CITY}, Page ${CURRENT_PAGE} ---`);
    const mainListURL = window.location.href; 
    const listingData = [];

    const listingContainers = document.querySelectorAll(SELECTORS.LISTING_CONTAINER);
    const listingURLs = Array.from(listingContainers).map(container => {
        const link = container.querySelector(SELECTORS.LINK_SELECTOR);
        return link ? new URL(link.getAttribute('href'), mainListURL).href : null;
    }).filter(url => url !== null);

    console.log(`Found ${listingURLs.length} links. Starting municipality filtering...`);
    
    let collectedCount = 0;
    let skippedCount = 0;
    let nonArchitecturalCount = 0;
    
    for (const url of listingURLs) {
        // Delay between requests
        await new Promise(r => setTimeout(r, Math.random() * 3000 + 1000));
        
        try {
            const response = await fetch(url, {
                headers: {
                    // предпочтительный язык - английский (en), с fallback на португальский (pt)
                    'Accept-Language': 'en-US,en;q=0.9,pt;q=0.8' 
                }
            });
            const htmlText = await response.text();
            const doc = new DOMParser().parseFromString(htmlText, 'text/html');
            
            // Get address and check municipality
            const address = safeText(SELECTORS.ADDRESS, doc);
            const municipality = 'Lisbon';
            const specialization = safeText(SELECTORS.SPECIALIZATION, doc);
            //const municipality = extractMunicipality(address);
            
            // FILTERING: check if municipality is in target list
            if (!municipality || !TARGET_MUNICIPALITIES.includes(municipality.toUpperCase())) {
                console.log(`Skipping company: municipality "${municipality}" not in target list`);
                skippedCount++;
                continue;
            }

            // If municipality matches - collect data
            if (!isArchitecturalCompany(specialization)) {
                console.log(`Skipping non-architectural company: "${specialization}"`);
                nonArchitecturalCount++;
                continue;
            }
            const companyName = safeText(SELECTORS.COMPANY_NAME, doc);
            const general_summary = safeText(SELECTORS.GENERAL_SUMMARY, doc);
            
            const data = {
                company_name: companyName,
                municipality: municipality,
                address: address,
                specialization: specialization,
                legal_name: companyName,
                general_summary: general_summary,
                data_source: 'Empresite',
                phone: null,
                contact_email: null,
                website: null,
                portfolio_url: null,
                year_founded: null,
                tax_id: null
            };
            
            listingData.push(data);
            collectedCount++;
            console.log(`Collected company: ${companyName} (${municipality})`);

        } catch (error) {
            console.error(`Error during collection: ${error.message}`);
        }
    }
    
    // Collection report
    console.log(`RESULT: Collected ${collectedCount} companies, skipped ${skippedCount}`);
    
    if (listingData.length > 0) {
        const csv = convertToCSV(listingData);
        const filename = `${CURRENT_CITY}_${CURRENT_PAGE}.csv`;
        downloadCSV(csv, filename);
    } else {
        console.warn("No companies found in target municipalities.");
    }
}

scrapePageAndDownload();