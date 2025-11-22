from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
import pandas as pd
import time
import random
import csv
import os
from urllib.parse import urljoin, quote

class ArchitizerScraper:
    def __init__(self, headless=True, target_city="Cascais"):
        self.setup_driver(headless)
        self.wait = WebDriverWait(self.driver, 15)
        
        self.target_city = target_city
        self.selectors = {
            'company_container': 'div.columns.small-12:has(a.black.fw-medium.ellipsis)',
            'company_container_alt1': 'div.row > div.columns.small-12.medium-6:has(a.black.fw-medium.ellipsis)',
            'company_container_alt2': 'div.columns.small-12 > div.row > div.columns:has(a.black.fw-medium.ellipsis)',
            
            'link_selector': 'a.black.fw-medium.ellipsis.flex-container.flex-dir-row',
            'company_name': 'h1.name',
            'address': 'div[id$="-locations"] span',
            'phone': 'div[id$="-phone_numbers"] div.js-rendered-content a',
            'email': 'div[id$="-email_addresses"] div.js-rendered-content a',
            'website': 'div[id$="-websites"] div.js-rendered-content a',
            'portfolio': 'div.projects',
            'summary': 'div.company-description-full',
            'specialization': 'div.the-description span',
        }
    
    def get_search_url(self):
        """Формирует URL для поиска компаний в указанном городе"""
        encoded_city = quote(self.target_city)
        url = f"https://architizer.com/firms/firm-location={encoded_city}%2C%20Portugal"
        print(f"Сформирован URL для поиска: {url}")
        return url
    
    def setup_driver(self, headless):
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        chrome_options.add_argument("--window-size=1920,1080")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    def random_delay(self, min_sec=2, max_sec=5):
        time.sleep(random.uniform(min_sec, max_sec))
    
    def safe_find_element(self, selector, parent=None, multiple=False, timeout=10):
        try:
            base = parent if parent else self.driver
            if multiple:
                return WebDriverWait(base, timeout).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                )
            else:
                return WebDriverWait(base, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
        except (NoSuchElementException, TimeoutException):
            return None if not multiple else []
    
    def safe_get_text(self, selector, parent=None):
        element = self.safe_find_element(selector, parent)
        return element.text.strip() if element else None
    
    def safe_get_attribute(self, selector, attribute, parent=None):
        element = self.safe_find_element(selector, parent)
        return element.get_attribute(attribute) if element else None
    
    def get_company_containers(self):
        """Находит контейнеры компаний, пробуя разные селекторы"""
        containers = self.safe_find_element(self.selectors['company_container'], multiple=True)
        
        if containers and len(containers) > 0:
            print(f"Найдено контейнеров компаний (основной селектор): {len(containers)}")
            return containers
        
        for i, selector in enumerate([self.selectors['company_container_alt1'], 
                                    self.selectors['company_container_alt2']], 1):
            containers = self.safe_find_element(selector, multiple=True)
            if containers and len(containers) > 0:
                print(f"Найдено контейнеров компаний (альтернативный селектор {i}): {len(containers)}")
                return containers
        
        print("Использую общий подход для поиска компаний...")
        company_links = self.safe_find_element(self.selectors['link_selector'], multiple=True)
        if not company_links:
            print("Не найдено ссылок на компании")
            return []
        
        containers = []
        for link in company_links:
            try:
                container = link.find_element(By.XPATH, "./ancestor::div[contains(@class, 'columns')][contains(@class, 'small-12')]")
                if container and container not in containers:
                    containers.append(container)
            except:
                continue
        
        print(f"Найдено контейнеров через общий подход: {len(containers)}")
        return containers
    
    def extract_unique_company_urls(self, containers, base_url):
        """Извлекает уникальные ссылки на компании из контейнеров"""
        unique_urls = set()
        
        for container in containers:
            try:
                if not container.is_displayed():
                    continue
                    
                link_element = self.safe_find_element(self.selectors['link_selector'], container)
                if link_element and link_element.is_displayed():
                    relative_url = link_element.get_attribute('href')
                    if relative_url:
                        full_url = urljoin(base_url, relative_url)
                        # Извлекаем уникальный идентификатор компании из URL
                        company_id = self.extract_company_id_from_url(full_url)
                        if company_id:
                            unique_urls.add((company_id, full_url))
            except StaleElementReferenceException:
                continue
        
        print(f"Найдено уникальных компаний: {len(unique_urls)}")
        
        # Возвращаем только URL (без ID)
        return [url for _, url in unique_urls]
    
    def extract_company_id_from_url(self, url):
        """Извлекает уникальный идентификатор компании из URL"""
        try:
            # Пример URL: https://architizer.com/firms/antonio-costa-lima-arquitectos/
            # Идентификатор: "antonio-costa-lima-arquitectos"
            parts = url.rstrip('/').split('/')
            if len(parts) >= 2:
                return parts[-1]
            return None
        except:
            return None
    
    def click_load_more(self):
        """Пытается найти и нажать кнопку Load More"""
        try:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            load_more_xpaths = [
                "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'load more')]",
                "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'load more')]",
                "//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'load more')]",
                "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show more')]"
            ]
            
            for xpath in load_more_xpaths:
                try:
                    button = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    if button and button.is_displayed():
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                        time.sleep(1)
                        self.driver.execute_script("arguments[0].click();", button)
                        print("Нажата кнопка Load More")
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            print(f"Ошибка при клике на Load More: {e}")
            return False
    
    def load_all_companies(self, url):
        """Загружает все компании, кликая на Load More пока это возможно"""
        print("Начинаю загрузку всех компаний с динамической подгрузкой")
        
        self.driver.get(url)
        self.random_delay(4, 6)
        
        initial_containers = self.get_company_containers()
        if not initial_containers:
            print("Не найдено ни одной компании на странице")
            return []
        
        print(f"Первоначально загружено контейнеров: {len(initial_containers)}")
        
        # Сразу извлекаем уникальные URL из начальных контейнеров
        unique_urls = self.extract_unique_company_urls(initial_containers, url)
        print(f"Первоначально уникальных компаний: {len(unique_urls)}")
        
        load_more_attempts = 0
        max_attempts = 15
        no_new_companies_count = 0
        
        while load_more_attempts < max_attempts and no_new_companies_count < 3:
            previous_unique_count = len(unique_urls)
            
            if not self.click_load_more():
                print("Кнопка Load More не найдена - все компании загружены")
                break
            
            print("Ожидаю загрузки новых компаний...")
            time.sleep(4)
            
            current_containers = self.get_company_containers()
            if not current_containers:
                print("Контейнеры компаний не найдены после загрузки")
                break
            
            # Извлекаем новые уникальные URL
            new_unique_urls = self.extract_unique_company_urls(current_containers, url)
            current_unique_count = len(set(unique_urls + new_unique_urls))
            
            if current_unique_count > previous_unique_count:
                new_companies = current_unique_count - previous_unique_count
                print(f"Загружено новых уникальных компаний: {new_companies}")
                print(f"Всего уникальных компаний: {current_unique_count}")
                unique_urls = list(set(unique_urls + new_unique_urls))
                no_new_companies_count = 0
            else:
                no_new_companies_count += 1
                print(f"Попытка {no_new_companies_count}/3: Новые компании не обнаружены")
            
            load_more_attempts += 1
            
            if no_new_companies_count >= 3:
                print("Прерываю загрузку: 3 попытки подряд без новых компаний")
                break
            
            self.random_delay(2, 3)
        
        if load_more_attempts >= max_attempts:
            print("Достигнут лимит нажатий Load More")
        
        print(f"Загрузка завершена. Всего уникальных компаний: {len(unique_urls)}")
        return unique_urls

    # Остальные методы без изменений
    def extract_portfolio(self, parent=None):
        """Извлекает портфолио проектов"""
        portfolio_container = self.safe_find_element(self.selectors['portfolio'], parent)
        if not portfolio_container:
            return None
        
        project_elements = self.safe_find_element('.thumb-block', portfolio_container, multiple=True)
        if not project_elements:
            return None
        
        projects = []
        for project in project_elements:
            name = self.safe_get_text('a.txt h4', project)
            if name:
                projects.append(name)
        
        return " | ".join(projects) if projects else None
    
    def extract_phones(self, parent=None):
        """Извлекает все телефоны компании"""
        try:
            phone_elements = self.safe_find_element(self.selectors['phone'], parent, multiple=True)
            if not phone_elements:
                return None
            
            phones = [elem.text.strip() for elem in phone_elements if elem.text.strip()]
            return " | ".join(phones) if phones else None
        except Exception as e:
            print(f"Error extracting phones: {e}")
            return None

    def extract_emails(self, parent=None):
        """Извлекает все email компании"""
        try:
            email_elements = self.safe_find_element(self.selectors['email'], parent, multiple=True)
            if not email_elements:
                return None
            
            emails = [elem.text.strip() for elem in email_elements if elem.text.strip()]
            return " | ".join(emails) if emails else None
        except Exception as e:
            print(f"Error extracting emails: {e}")
            return None

    def extract_websites(self, parent=None):
        """Извлекает все сайты компании"""
        try:
            website_elements = self.safe_find_element(self.selectors['website'], parent, multiple=True)
            if not website_elements:
                return None
            
            websites = [elem.get_attribute('href') for elem in website_elements if elem.get_attribute('href')]
            return " | ".join(websites) if websites else None
        except Exception as e:
            print(f"Error extracting websites: {e}")
            return None
    
    def extract_address(self, parent=None):
        """Извлекает адрес компании"""
        return self.safe_get_text(self.selectors['address'], parent)
    
    def scrape_company_page(self, url):
        """Собирает данные с одной страницы компании"""
        try:
            self.driver.get(url)
            self.random_delay(3, 6)
            
            company_name = self.safe_get_text(self.selectors['company_name'])
            summary = self.safe_get_text(self.selectors['summary'])
            
            data = {
                'company_name': company_name,
                'address': self.extract_address(),
                'phone': self.extract_phones(),
                'website': self.extract_websites(),
                'municipality': self.target_city,
                'data_source': 'Architizer', 
                'specialization': self.safe_get_text(self.selectors['specialization']),
                'general_summary': summary,
                'portfolio': self.extract_portfolio(),
                'contact_email': self.extract_emails(),
                'company_url': url,
                'scraped_at': pd.Timestamp.now().isoformat()
            }
            
            print(f"Собрана компания: {data['company_name'] or 'без названия'}")
            return data
            
        except Exception as e:
            print(f"Ошибка при сборе данных с {url}: {str(e)}")
            return {
                'company_url': url,
                'error': str(e),
                'data_source': 'Architizer'
            }
    
    def scrape_with_load_more(self):
        """Собирает все компании с динамической подгрузкой для указанного города"""
        base_url = self.get_search_url()
        
        print(f"Начинаю сбор всех компаний в городе: {self.target_city}")
        print(f"URL: {base_url}")
        
        # Теперь load_all_companies возвращает сразу уникальные URL
        unique_company_urls = self.load_all_companies(base_url)
        
        if not unique_company_urls:
            print("Не удалось загрузить компании")
            return []
        
        print(f"Начинаю обработку {len(unique_company_urls)} уникальных компаний")
        
        # Собираем данные по каждой уникальной компании
        all_data = []
        for i, url in enumerate(unique_company_urls, 1):
            print(f"\nОбрабатываю компанию {i}/{len(unique_company_urls)}")
            print(f"URL: {url}")
            
            company_data = self.scrape_company_page(url)
            all_data.append(company_data)
            
            if i % 10 == 0:
                self.save_to_csv(all_data, f"progress_{self.target_city}_batch_{i//10}")
                print(f"Сохранен промежуточный результат (батч {i//10})")
            
            if i < len(unique_company_urls):
                delay = random.uniform(5, 15)
                print(f"Задержка {delay:.1f} сек...")
                time.sleep(delay)
        
        return all_data
    
    def save_to_csv(self, data, suffix=""):
        """Сохраняет данные в CSV файл"""
        if suffix:
            filename = f"architizer_companies_{suffix}.csv"
        else:
            filename = f"architizer_companies_{self.target_city}_complete.csv"
        
        if not data:
            print("Нет данных для сохранения")
            return
        
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False, sep=';', quoting=csv.QUOTE_ALL, encoding='utf-8-sig')
        print(f"Данные сохранены в файл: {filename}")
        print(f"Записей в файле: {len(data)}")

    def close(self):
        """Закрывает браузер"""
        if self.driver:
            self.driver.quit()
            print("Браузер закрыт")

def main():
    scraper = None
    try:
        print("Запуск Architizer Scraper с динамической подгрузкой...")
        
        target_city = "Lisbon"
        
        scraper = ArchitizerScraper(headless=False, target_city=target_city)
        
        print(f"Поиск компаний в городе: {target_city}")
        print("Начинаю сбор всех компаний...")
        
        start_time = time.time()
        all_data = scraper.scrape_with_load_more()
        end_time = time.time()
        
        if all_data:
            scraper.save_to_csv(all_data, f"final_{target_city}")
        
        print(f"\n{'='*60}")
        print(f"СКРАПИНГ ЗАВЕРШЕН!")
        print(f"Город поиска: {target_city}")
        print(f"Затраченное время: {(end_time - start_time)/60:.1f} минут")
        print(f"Всего собрано компаний: {len(all_data)}")
        print(f"Файлы сохранены в текущей директории")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"Критическая ошибка: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        if scraper:
            scraper.close()

if __name__ == "__main__":
    main()