# imovirtual_scraper_fixed.py
import asyncio
import json
import random
import time
from datetime import datetime
import csv
from playwright.async_api import async_playwright

class ImovirtualScraperSimple:
    """Упрощенный работающий скрапер"""
    
    def __init__(self, max_pages=5, headless=False):
        self.max_pages = max_pages
        self.headless = headless
        self.base_url = "https://www.imovirtual.com"
        self.scraped_data = []
    
    async def run(self):
        print(f"🚀 Запуск упрощенного скрапера (max {self.max_pages} страниц)")
        
        async with async_playwright() as p:
            # Запускаем браузер
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            
            page = await context.new_page()
            
            try:
                # 1. Открываем первую страницу
                url = "https://www.imovirtual.com/pt/resultados/comprar/apartamento/todo-o-pais"
                print(f"📄 Открываю: {url}")
                await page.goto(url, timeout=60000)
                
                # 2. Принимаем куки если есть
                await self.accept_cookies(page)
                
                # 3. Проходим по страницам
                for page_num in range(1, self.max_pages + 1):
                    print(f"\n{'='*60}")
                    print(f"🔍 Страница {page_num}/{self.max_pages}")
                    print(f"{'='*60}")
                    
                    # Ждем загрузки
                    await page.wait_for_load_state('networkidle')
                    
                    # 4. Находим ссылки на объявления - КЛЮЧЕВОЕ ИЗМЕНЕНИЕ!
                    # Способ 1: Ищем по data-cy атрибуту (как в твоих тестах)
                    links = await self.find_listing_links(page)
                    
                    if not links:
                        print("⚠️ Не нашел ссылки, пробую альтернативный метод...")
                        # Способ 2: Ищем по тексту в href
                        links = await page.eval_on_selector_all(
                            "a",
                            '''elements => elements
                                .filter(el => el.href && el.href.includes('/anuncio/'))
                                .map(el => el.href)
                            '''
                        )
                    
                    print(f"Найдено ссылок: {len(links)}")
                    
                    # 5. Обрабатываем первые 3 ссылки для теста
                    for i, link in enumerate(links[:3]):
                        print(f"[{i+1}/{min(3, len(links))}] Обрабатываю: {link[:80]}...")
                        
                        # Открываем объявление в новой вкладке
                        page2 = await context.new_page()
                        try:
                            await page2.goto(link, timeout=30000)
                            await asyncio.sleep(2)  # Ждем загрузки
                            
                            # Извлекаем базовые данные
                            data = await self.extract_basic_data(page2)
                            if data:
                                data['url'] = link
                                data['scraped_at'] = datetime.now().isoformat()
                                self.scraped_data.append(data)
                                print(f"✅ Собрано: {data.get('price', 'N/A')}€ - {data.get('address', 'N/A')}")
                            
                            await page2.close()
                            await asyncio.sleep(random.uniform(1, 2))  # Пауза
                            
                        except Exception as e:
                            print(f"❌ Ошибка: {e}")
                            if 'page2' in locals():
                                await page2.close()
                    
                    # 6. Переход на следующую страницу
                    if page_num < self.max_pages:
                        next_url = await self.get_next_page_url(page)
                        if next_url:
                            await page.goto(next_url, timeout=30000)
                            await asyncio.sleep(2)
                        else:
                            print("⏹️ Нет следующей страницы")
                            break
                    
                # 7. Сохраняем результаты
                await self.save_results()
                
            except Exception as e:
                print(f"💥 Критическая ошибка: {e}")
            finally:
                await browser.close()
    
    async def accept_cookies(self, page):
        """Принимаем куки"""
        try:
            # Попробуем разные кнопки
            cookie_selectors = [
                "button:has-text('Aceitar')",
                "button:has-text('Aceitar todos')",
                "button:has-text('Accept')",
                "button:has-text('Aceitar cookies')",
            ]
            
            for selector in cookie_selectors:
                try:
                    button = await page.query_selector(selector)
                    if button:
                        await button.click()
                        await asyncio.sleep(1)
                        print("🍪 Куки приняты")
                        break
                except:
                    continue
        except:
            pass
    
    async def find_listing_links(self, page):
        """Находим ссылки на объявления - основной метод"""
        try:
            # Метод 1: По data-cy атрибуту (самый надежный)
            links = await page.eval_on_selector_all(
                '[data-cy="listing-item-link"]',
                'elements => elements.map(el => el.href)'
            )
            
            if links:
                return list(set(links))  # Удаляем дубликаты
            
            # Метод 2: По классу (из HTML который ты показывала)
            links = await page.eval_on_selector_all(
                'a.css-16vl3c1',
                'elements => elements.map(el => el.href)'
            )
            
            if links:
                return list(set(links))
            
            # Метод 3: Все ссылки содержащие "/anuncio/"
            all_links = await page.eval_on_selector_all(
                'a',
                '''elements => elements
                    .filter(el => el.href && el.href.includes('/anuncio/'))
                    .map(el => el.href)
                '''
            )
            
            return list(set(all_links))
            
        except Exception as e:
            print(f"Ошибка поиска ссылок: {e}")
            return []
    
    async def extract_basic_data(self, page):
        """Извлекаем полные данные об объявлении с исправленными селекторами"""
        data = {}
        
        try:
            # 0. Ждем загрузки ключевых элементов
            await page.wait_for_selector('body', timeout=30000)
            
            # 1. ЦЕНА (это работает, оставляем)
            price_elem = await page.query_selector('strong[data-cy="adPageHeaderPrice"]')
            if price_elem:
                price_text = await price_elem.text_content()
                if price_text:
                    import re
                    digits = re.sub(r'[^\d,]', '', price_text)
                    digits = digits.replace(',', '.')
                    try:
                        data['price'] = float(digits)
                        data['price_currency'] = '€'
                    except:
                        data['price_raw'] = price_text.strip()
            
            # 2. АДРЕС (это работает, оставляем)
            address_elem = await page.query_selector('a[href="#map"]')
            if not address_elem:
                address_elem = await page.query_selector('[data-testid="ad-location"]')
            
            if address_elem:
                address = await address_elem.text_content()
                if address:
                    data['address'] = address.strip()
                    # Парсим адрес на компоненты
                    await self.parse_address_components(data, address)
            
            # 3. ЗАГОЛОВОК
            title_elem = await page.query_selector('[data-cy="listing-item-title"]')
            if not title_elem:
                title_elem = await page.query_selector('h1')
            
            if title_elem:
                title = await title_elem.text_content()
                if title:
                    data['title'] = title.strip()
            
            # 4. ИСПОЛЬЗУЕМ ПОДХОД STABLE_SPIDER ДЛЯ ХАРАКТЕРИСТИК
            characteristics = await self.extract_characteristics_stable_spider(page)
            data.update(characteristics)
            
            # 5. ОПИСАНИЕ (используем подход stable_spider)
            description = await self.extract_description_stable_spider(page)
            if description:
                data['description'] = description
            
            # 6. ОСОБЕННОСТИ (features)
            features = await self.extract_features_stable_spider(page)
            if features:
                data['features'] = features
                # Извлекаем булевые особенности из features
                data.update(self.extract_booleans_from_features(features))
            
            # 7. ДАТА ПУБЛИКАЦИИ
            publish_date = await self.extract_publish_date_stable_spider(page)
            if publish_date:
                data['publish_date'] = publish_date
            
            # 8. ФОТО (количество)
            photo_count = await self.count_photos_stable_spider(page)
            if photo_count:
                data['photo_count'] = photo_count
            
            # 9. URL и ID
            data['url'] = page.url
            data['listing_id'] = self.extract_listing_id(page.url)
            
            # 10. ВРЕМЯ СКРАПИНГА
            data['scraped_at'] = datetime.now().isoformat()
            
            # 11. ДОПОЛНИТЕЛЬНЫЕ ПОЛЯ ИЗ STABLE_SPIDER
            additional_data = await self.extract_additional_fields_stable_spider(page)
            data.update(additional_data)
            
        except Exception as e:
            print(f"⚠️  Ошибка при извлечении данных: {e}")
            import traceback
            print(traceback.format_exc())
        
        return data


    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ

    async def parse_address_components(self, data, address):
        """Парсинг адреса на компоненты (district, city, neighborhood)"""
        try:
            parts = [p.strip() for p in address.split(',') if p.strip()]
            
            if len(parts) >= 3:
                data['district'] = parts[-1]
                data['city'] = parts[-2]
                data['neighborhood'] = parts[-3]
            elif len(parts) == 2:
                data['district'] = parts[-1]
                data['city'] = parts[-2]
            elif len(parts) == 1:
                data['city'] = parts[0]
        except Exception as e:
            print(f"Ошибка парсинга адреса: {e}")


    async def extract_characteristics_stable_spider(self, page):
        """Извлечение характеристик методом stable_spider"""
        characteristics = {}
        
        try:
            # JavaScript код из stable_spider для извлечения пар ключ-значение
            kv_pairs = await page.evaluate("""() => {
                const norm = s => (s || '').replace(/\\u00A0/g, ' ').replace(/\\s+/g, ' ').trim();
                const out = [];
                
                // Ищем все контейнеры с характеристиками
                document.querySelectorAll("div[data-sentry-element='ItemGridContainer']").forEach(g => {
                    const kids = [...g.children];
                    for (let i = 0; i < kids.length; i++) {
                        const el = kids[i];
                        if ((el.getAttribute && el.getAttribute("data-sentry-element")) !== "Item") continue;
                        const label = norm(el.textContent);
                        if (!label) continue;
                        let j = i + 1, val = "";
                        while (j < kids.length && !val) {
                            const t = norm(kids[j].textContent);
                            if (t && t !== ":" && t !== "…") val = t;
                            j++;
                        }
                        if (label && val) out.push([label.toLowerCase(), val]);
                    }
                });
                return out;
            }""")
            
            # Обрабатываем найденные пары
            import re
            
            for key, value in kv_pairs:
                key_norm = key.lower()
                
                # ПЛОЩАДЬ
                if 'área' in key_norm or 'area' in key_norm:
                    match = re.search(r'(\d+)', value)
                    if match:
                        characteristics['area_sqm'] = int(match.group(1))
                        characteristics['area_raw'] = value.strip()
                
                # СПАЛЬНИ
                elif 'tipologia' in key_norm or 'quartos' in key_norm or 'quarto' in key_norm:
                    # Ищем T1, T2, T3 или просто цифру
                    match = re.search(r'T(\d)|(\d+)', value.upper())
                    if match:
                        characteristics['bedrooms'] = int(match.group(1) or match.group(2))
                    characteristics['bedrooms_raw'] = value.strip()
                
                # САНУЗЕЛЫ
                elif 'casas de banho' in key_norm or 'wc' in key_norm or 'banho' in key_norm:
                    match = re.search(r'(\d+)', value)
                    if match:
                        characteristics['bathrooms'] = int(match.group(1))
                    characteristics['bathrooms_raw'] = value.strip()
                
                # ЭТАЖ
                elif 'andar' in key_norm or 'piso' in key_norm or 'floor' in key_norm:
                    if 'r/c' in value.lower() or 'rés do chão' in value.lower():
                        characteristics['floor'] = '0'
                    else:
                        match = re.search(r'(\d+)', value)
                        if match:
                            characteristics['floor'] = match.group(1)
                    characteristics['floor_raw'] = value.strip()
                
                # ГОД ПОСТРОЙКИ
                elif 'ano' in key_norm and 'construção' in key_norm:
                    match = re.search(r'(\d{4})', value)
                    if match:
                        characteristics['construction_year'] = int(match.group(1))
                
                # ЭНЕРГОСЕРТИФИКАТ
                elif 'certificado' in key_norm and 'energético' in key_norm:
                    # Ищем класс энергии: A, B, C, etc
                    match = re.search(r'([A-G][+]?)', value.upper())
                    if match:
                        characteristics['energy_certificate'] = match.group(1)
                    characteristics['energy_certificate_raw'] = value.strip()
                
                # СОСТОЯНИЕ (conservation)
                elif 'estado' in key_norm and 'conservação' in key_norm:
                    characteristics['conservation_status'] = value.strip()
                
                # ПАРКОВКА
                elif 'estacionamento' in key_norm or 'parqueamento' in key_norm:
                    match = re.search(r'(\d+)', value)
                    if match:
                        characteristics['parking_spaces'] = int(match.group(1))
                    characteristics['parking_raw'] = value.strip()
                
                # ГАРАЖ
                elif 'garagem' in key_norm or 'box' in key_norm:
                    characteristics['has_garage'] = self.parse_boolean(value)
                
                # ЛИФТ
                elif 'elevador' in key_norm or 'elevator' in key_norm:
                    characteristics['has_elevator'] = self.parse_boolean(value)
                
                # ХРАНИМ все остальные поля в details
                else:
                    if 'details' not in characteristics:
                        characteristics['details'] = {}
                    characteristics['details'][key] = value
            
            # Если не нашли площадь через характеристики, ищем другим способом
            if 'area_sqm' not in characteristics:
                area_text = await page.evaluate("""() => {
                    // Ищем площадь в любом месте
                    const allElements = document.querySelectorAll('div, span, p, li, td');
                    for (let el of allElements) {
                        const text = el.textContent || '';
                        if (text.includes('m²') || text.includes('m2') || text.includes('metro')) {
                            // Ищем цифры перед m²
                            const match = text.match(/(\\d+)\\s*m²/);
                            if (match) return match[1];
                            // Ищем просто цифры в контексте площади
                            const words = text.toLowerCase().split(' ');
                            if (words.includes('área') || words.includes('area')) {
                                const numMatch = text.match(/(\\d+)/);
                                if (numMatch) return numMatch[1];
                            }
                        }
                    }
                    return null;
                }""")
                
                if area_text:
                    match = re.search(r'(\d+)', area_text)
                    if match:
                        characteristics['area_sqm'] = int(match.group(1))
            
        except Exception as e:
            print(f"Ошибка при извлечении характеристик: {e}")
        
        return characteristics


    async def extract_description_stable_spider(self, page):
        """Извлечение описания методом stable_spider"""
        try:
            description = await page.evaluate("""() => {
                const norm = s => (s || '').replace(/\\u00A0/g, ' ').replace(/\\s+/g, ' ').trim();
                
                // Пробуем разные селекторы
                const selectors = [
                    "[data-testid='ad-description']",
                    "[data-testid='adDescription']",
                    "#ad-description",
                    ".description",
                    "[data-cy='adDescription']",
                    "div:has(> h2:contains('Descrição')) + div",
                    "div:has(> h3:contains('Descrição')) + div",
                ];
                
                for (const selector of selectors) {
                    const el = document.querySelector(selector);
                    if (el && el.textContent && el.textContent.trim().length > 50) {
                        return norm(el.textContent).substring(0, 2000); // Ограничиваем длину
                    }
                }
                
                // Если не нашли, ищем любой большой текст
                const allDivs = document.querySelectorAll('div');
                for (let div of allDivs) {
                    const text = div.textContent || '';
                    if (text.length > 300 && text.length < 5000) {
                        const lines = text.split('\\n').filter(line => line.trim().length > 50);
                        if (lines.length > 0) {
                            return norm(lines[0]).substring(0, 2000);
                        }
                    }
                }
                
                return null;
            }""")
            
            return description
            
        except Exception as e:
            print(f"Ошибка при извлечении описания: {e}")
            return None


    async def extract_features_stable_spider(self, page):
        """Извлечение списка особенностей (features)"""
        try:
            features = await page.evaluate("""() => {
                const features = new Set();
                
                // Ищем в блоке особенностей
                const featureElements = document.querySelectorAll(
                    "[data-testid='ad-features'] li, " +
                    "ul[class*='features'] li, " +
                    "div[data-sentry-element='ItemGridContainer'] p span"
                );
                
                featureElements.forEach(el => {
                    const text = (el.textContent || '').trim().toLowerCase();
                    if (text && text.length > 2 && text.length < 100) {
                        features.add(text);
                    }
                });
                
                // Ищем в произвольных местах (как в stable_spider)
                document.querySelectorAll("div[data-sentry-element='ItemGridContainer']").forEach(g => {
                    g.querySelectorAll("li, span, p").forEach(el => {
                        const text = (el.textContent || '').trim().toLowerCase();
                        if (text && text.length <= 60 && text !== ":" && text !== "…") {
                            features.add(text);
                        }
                    });
                });
                
                return Array.from(features);
            }""")
            
            return features
            
        except Exception as e:
            print(f"Ошибка при извлечении features: {e}")
            return []


    async def extract_publish_date_stable_spider(self, page):
        """Извлечение даты публикации"""
        try:
            publish_date = await page.evaluate("""() => {
                // Ищем блок с историей объявления
                const historyBlocks = document.querySelectorAll("div[data-sentry-component='AdHistoryBase']");
                for (let block of historyBlocks) {
                    const text = block.textContent || '';
                    // Ищем дату в формате DD.MM.YYYY
                    const match = text.match(/(\\d{1,2})\\.(\\d{1,2})\\.(\\d{4})/);
                    if (match) {
                        return match[0];
                    }
                }
                return null;
            }""")
            
            if publish_date:
                # Конвертируем в ISO формат
                import re
                match = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', publish_date)
                if match:
                    day, month, year = match.groups()
                    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            
            return None
            
        except Exception as e:
            print(f"Ошибка при извлечении даты: {e}")
            return None


    async def count_photos_stable_spider(self, page):
        """Подсчет количества фотографий"""
        try:
            count = await page.evaluate("""() => {
                // Ищем все изображения объявления
                const images = document.querySelectorAll(
                    "[data-testid='image-attachment'] img, " +
                    ".gallery img, " +
                    "img[alt*='imovel'], " +
                    "img[alt*='property']"
                );
                return images.length;
            }""")
            
            return count if count > 0 else None
            
        except Exception as e:
            print(f"Ошибка при подсчете фото: {e}")
            return None


    async def extract_additional_fields_stable_spider(self, page):
        """Извлечение дополнительных полей"""
        additional = {}
        
        try:
            # Проверяем наличие лифта, гаража, парковки через features
            features = await self.extract_features_stable_spider(page)
            if features:
                features_lower = [f.lower() for f in features]
                
                # ЛИФТ
                if any(word in ' '.join(features_lower) for word in ['elevador', 'elevator']):
                    additional['has_elevator'] = True
                elif any(word in ' '.join(features_lower) for word in ['sem elevador', 'no elevator']):
                    additional['has_elevator'] = False
                
                # ГАРАЖ
                if any(word in ' '.join(features_lower) for word in ['garagem', 'garage', 'box']):
                    additional['has_garage'] = True
                elif any(word in ' '.join(features_lower) for word in ['sem garagem', 'no garage']):
                    additional['has_garage'] = False
                
                # ПАРКОВКА
                if any(word in ' '.join(features_lower) for word in ['estacionamento', 'parking', 'parqueamento']):
                    additional['has_parking'] = True
                elif any(word in ' '.join(features_lower) for word in ['sem estacionamento', 'no parking']):
                    additional['has_parking'] = False
                
                # МЕБЕЛЬ
                if any(word in ' '.join(features_lower) for word in ['mobilado', 'mobilada', 'furnished']):
                    additional['furnished'] = True
                elif any(word in ' '.join(features_lower) for word in ['não mobilado', 'unfurnished']):
                    additional['furnished'] = False
            
        except Exception as e:
            print(f"Ошибка при извлечении дополнительных полей: {e}")
        
        return additional


    def extract_booleans_from_features(self, features):
        """Извлечение булевых значений из списка features"""
        booleans = {}
        
        if not features:
            return booleans
        
        features_lower = [f.lower() for f in features]
        all_features_text = ' '.join(features_lower)
        
        # ЛИФТ
        if any(word in all_features_text for word in ['elevador', 'elevator']):
            booleans['has_elevator'] = True
        elif any(word in all_features_text for word in ['sem elevador', 'no elevator']):
            booleans['has_elevator'] = False
        
        # ГАРАЖ
        if any(word in all_features_text for word in ['garagem', 'garage', 'box']):
            booleans['has_garage'] = True
        elif any(word in all_features_text for word in ['sem garagem', 'no garage']):
            booleans['has_garage'] = False
        
        # ПАРКОВКА
        if any(word in all_features_text for word in ['estacionamento', 'parking', 'parqueamento']):
            booleans['has_parking'] = True
        elif any(word in all_features_text for word in ['sem estacionamento', 'no parking']):
            booleans['has_parking'] = False
        
        # МЕБЕЛЬ
        if any(word in all_features_text for word in ['mobilado', 'mobilada', 'furnished']):
            booleans['furnished'] = True
        elif any(word in all_features_text for word in ['não mobilado', 'unfurnished']):
            booleans['furnished'] = False
        
        return booleans


    def parse_boolean(self, text):
        """Парсинг булевых значений из текста"""
        if not text:
            return None
        
        text_lower = text.lower().strip()
        
        true_values = ['sim', 'yes', 'true', '1', 'com', 'possui', 'tem', 'inclui', 'disponível']
        false_values = ['não', 'nao', 'no', 'false', '0', 'sem']
        
        for val in true_values:
            if val in text_lower:
                return True
        
        for val in false_values:
            if val in text_lower:
                return False
        
        return None


    def extract_listing_id(self, url):
        """Извлечение ID объявления из URL"""
        import re
        # Ищем ID в формате ID1hJes, ID1hGzE и т.д.
        match = re.search(r'ID([A-Za-z0-9]+)', url)
        return match.group(1) if match else None
    
    async def get_next_page_url(self, page):
        """Получаем URL следующей страницы"""
        try:
            # Ищем кнопку пагинации
            next_button = await page.query_selector('a[title="Go to next page"]')
            if not next_button:
                next_button = await page.query_selector('a.css-1msxzpe')
            
            if next_button:
                next_url = await next_button.get_attribute('href')
                if next_url and not next_url.startswith('http'):
                    return self.base_url + next_url
                return next_url
            
            # Пробуем получить следующую страницу через параметр ?page=
            current_url = page.url
            if '?page=' in current_url:
                import re
                match = re.search(r'page=(\d+)', current_url)
                if match:
                    current_page = int(match.group(1))
                    next_page = current_page + 1
                    return re.sub(r'page=\d+', f'page={next_page}', current_url)
            else:
                return current_url + '?page=2'
                
        except Exception as e:
            print(f"Ошибка поиска следующей страницы: {e}")
        
        return None
    
    async def save_results(self):
        """Сохраняем результаты"""
        if not self.scraped_data:
            print("⚠️ Нет данных для сохранения")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Сохраняем в JSON
        json_file = f"imovirtual_data_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.scraped_data, f, ensure_ascii=False, indent=2)
        print(f"\n✅ JSON сохранен: {json_file}")
        
        # Сохраняем в CSV (если есть данные)
        if self.scraped_data:
            csv_file = f"imovirtual_data_{timestamp}.csv"
            # Определяем все поля
            all_fields = set()
            for item in self.scraped_data:
                all_fields.update(item.keys())
            
            fieldnames = sorted(list(all_fields))
            
            with open(csv_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for item in self.scraped_data:
                    row = {field: item.get(field, '') for field in fieldnames}
                    writer.writerow(row)
            
            print(f"✅ CSV сохранен: {csv_file}")
        
        # Выводим статистику
        print(f"\n📊 СТАТИСТИКА:")
        print(f"   Всего объявлений: {len(self.scraped_data)}")
        
        if self.scraped_data:
            # Цены
            prices = [d.get('price') for d in self.scraped_data if d.get('price')]
            if prices:
                print(f"   Средняя цена: {sum(prices)/len(prices):.0f}€")
            
            # Адреса
            addresses = [d.get('address') for d in self.scraped_data if d.get('address')]
            if addresses:
                print(f"   Уникальных адресов: {len(set(addresses))}")
            
            # Заполненность полей
            print(f"\n   Заполненность данных:")
            total = len(self.scraped_data)
            fields_to_check = ['price', 'address', 'bedrooms', 'area', 'description']
            for field in fields_to_check:
                count = sum(1 for d in self.scraped_data if d.get(field))
                print(f"   - {field}: {count}/{total} ({count/total*100:.1f}%)")

async def main():
    # Запускаем упрощенный скрапер
    scraper = ImovirtualScraperSimple(
        max_pages=3,  # Начнем с 3 страниц
        headless=False  # Показываем браузер для дебага
    )
    await scraper.run()

if __name__ == "__main__":
    asyncio.run(main())