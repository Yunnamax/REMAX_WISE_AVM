from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pandas as pd
import time
import random
import csv
import os
from urllib.parse import urljoin

class ArchelloScraper:
    def __init__(self, headless=True):
        self.setup_driver(headless)
        self.wait = WebDriverWait(self.driver, 10)
        
        # Селекторы
        self.selectors = {
            'company_container': 'div.brand-content__grid-item',
            'link_selector': 'div.short-item__bottom-brand a.text-dark[href^="/brand/"]',
            'description': 'div.short-item__bottom-description',
            'company_name': 'h1.profile-name span.font-weight-bold',
            'address': 'div.grid-item-info-content',
            'portfolio': '#brand-projects-grid',
            'summary': 'div.profile-description',
        }
    
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
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    def random_delay(self, min_sec=2, max_sec=5):
        time.sleep(random.uniform(min_sec, max_sec))
    
    def safe_find_element(self, selector, parent=None, multiple=False):
        try:
            base = parent if parent else self.driver
            if multiple:
                return base.find_elements(By.CSS_SELECTOR, selector)
            else:
                return base.find_element(By.CSS_SELECTOR, selector)
        except NoSuchElementException:
            return None if not multiple else []
    
    def safe_get_text(self, selector, parent=None):
        element = self.safe_find_element(selector, parent)
        return element.text.strip() if element else None
    
    def safe_get_attribute(self, selector, attribute, parent=None):
        element = self.safe_find_element(selector, parent)
        return element.get_attribute(attribute) if element else None
    
    def has_valid_description(self, container):
        description = self.safe_find_element(self.selectors['description'], container)
        if not description:
            return True
        text = description.text.strip().lower()
        return "no description available" not in text
    
    def extract_address(self, parent=None):
        elements = self.safe_find_element(self.selectors['address'], parent, multiple=True)
        if not elements:
            return None
        
        for element in elements:
            text = element.text.strip().lower()
            if any(keyword in text for keyword in ['portugal', 'lisboa', 'porto', 'faro']):
                return element.text.strip()
        return None
    
    def extract_phone(self, parent=None):
        elements = self.safe_find_element(self.selectors['address'], parent, multiple=True)
        if not elements:
            return None
        
        for element in elements:
            text = element.text.strip()
            # Проверка форматов телефона
            if any([
                len(text) > 7 and text.replace(' ', '').replace('-', '').replace('(', '').replace(')', '').isdigit(),
                '+' in text and any(c.isdigit() for c in text),
                'phone' in text.lower()
            ]):
                return text
        return None
    
    def extract_website(self, parent=None):
        elements = self.safe_find_element(self.selectors['address'], parent, multiple=True)
        if not elements:
            return None
        
        for element in elements:
            link = self.safe_find_element('a[href^="http"]', element)
            if link:
                href = link.get_attribute('href')
                if href and not any(social in href for social in ['facebook', 'linkedin', 'instagram', 'archello']):
                    return href
        return None
    
    def extract_portfolio(self, parent=None):
        portfolio_container = self.safe_find_element(self.selectors['portfolio'], parent)
        if not portfolio_container:
            return None
        
        project_elements = self.safe_find_element('.grid-item__card-col', portfolio_container, multiple=True)
        if not project_elements:
            return None
        
        projects = []
        for project in project_elements:
            description = self.safe_find_element('.grid-item-description', project)
            if not description:
                continue
            
            name_element = self.safe_find_element('b', description)
            link_element = self.safe_find_element('a', description)
            
            name = name_element.text.strip() if name_element else None
            link = link_element.get_attribute('href') if link_element else None
            
            if name and link:
                projects.append(f"{name}: {link}")
        
        return " | ".join(projects) if projects else None
    
    def scrape_company_page(self, url):
        """Собирает данные с одной страницы компании"""
        try:
            self.driver.get(url)
            self.random_delay(3, 6)
            
            data = {
                'company_name': self.safe_get_text(self.selectors['company_name']),
                'address': self.extract_address(),
                'phone': self.extract_phone(),
                'website': self.extract_website(),
                'municipality': 'Setúbal',
                'general_summary': self.safe_get_text(self.selectors['summary']),
                'portfolio': self.extract_portfolio(),
                'data_source': 'Archello',
                'company_url': url,
                'scraped_city': 'Setúbal',
                'scraped_at': pd.Timestamp.now().isoformat()
            }
            
            print(f"✅ Собрана компания: {data['company_name'] or 'без названия'}")
            return data
            
        except Exception as e:
            print(f"❌ Ошибка при сборе данных с {url}: {str(e)}")
            return {
                'company_url': url,
                'error': str(e),
                'data_source': 'Archello',
                'scraped_city': 'Setúbal'
            }
    
    def scrape_search_page(self, page_number):
        """Собирает ссылки на компании со страницы поиска"""
        url = f"https://archello.com/brands/architects?location=Setúbal%2C+Portugal&country_code=PT&city_name=Setúbal&page={page_number}&per-page=18"
        print(f"📄 Обрабатываю страницу {page_number}: {url}")
        
        try:
            self.driver.get(url)
            self.random_delay(4, 7)
            
            # Ждем загрузки контейнеров
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['company_container'])))
            
            company_containers = self.safe_find_element(self.selectors['company_container'], multiple=True)
            if not company_containers:
                print("⚠️ На странице не найдено компаний")
                return []
            
            company_urls = []
            skipped_count = 0
            
            for container in company_containers:
                if not self.has_valid_description(container):
                    skipped_count += 1
                    continue
                
                link_element = self.safe_find_element(self.selectors['link_selector'], container)
                if link_element:
                    relative_url = link_element.get_attribute('href')
                    full_url = urljoin(url, relative_url)
                    company_urls.append(full_url)
            
            print(f"📊 Найдено компаний: {len(company_containers)}")
            print(f"✅ После фильтрации: {len(company_urls)}")
            print(f"❌ Отфильтровано: {skipped_count} компаний без описания")
            
            return company_urls
            
        except Exception as e:
            print(f"❌ Ошибка при обработке страницы {page_number}: {str(e)}")
            return []
    
    def scrape_multiple_pages(self, start_page=1, end_page=10, delay_between_pages=10):
        """Собирает данные с нескольких страниц"""
        all_data = []
        
        for page in range(start_page, end_page + 1):
            print(f"\n{'='*50}")
            print(f"🔄 Начинаю обработку страницы {page}")
            print(f"{'='*50}")
            
            # Собираем ссылки со страницы поиска
            company_urls = self.scrape_search_page(page)
            
            if not company_urls:
                print(f"⏭️ Пропускаю страницу {page} - нет компаний для обработки")
                continue
            
            # Собираем данные по каждой компании
            page_data = []
            for i, url in enumerate(company_urls, 1):
                print(f"\n📋 Компания {i}/{len(company_urls)}")
                company_data = self.scrape_company_page(url)
                page_data.append(company_data)
                
                # Случайная задержка между компаниями
                if i < len(company_urls):
                    delay = random.uniform(5, 15)
                    print(f"⏳ Задержка {delay:.1f} сек...")
                    time.sleep(delay)
            
            # Сохраняем данные страницы
            if page_data:
                self.save_to_csv(page_data, page)
                all_data.extend(page_data)
            
            # Задержка между страницами
            if page < end_page:
                print(f"\n🕒 Задержка {delay_between_pages} сек перед следующей страницей...")
                time.sleep(delay_between_pages)
        
        return all_data
    
    def save_to_csv(self, data, page_number):
        """Сохраняет данные в CSV файл"""
        filename = f"archello_companies_Setúbal_page{page_number}.csv"
        
        if not data:
            print("⚠️ Нет данных для сохранения")
            return
        
        # Создаем DataFrame и сохраняем
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False, sep=';', quoting=csv.QUOTE_ALL, encoding='utf-8-sig')
        print(f"💾 Данные сохранены в файл: {filename}")
        print(f"📊 Записей в файле: {len(data)}")
    
    def close(self):
        """Закрывает браузер"""
        if self.driver:
            self.driver.quit()
            print("🔚 Браузер закрыт")

def main():
    # Настройки скрапинга
    START_PAGE = 1
    END_PAGE = 1  # Сколько страниц обработать
    DELAY_BETWEEN_PAGES = 15  # Задержка между страницами в секундах
    
    scraper = None
    try:
        print("🚀 Запуск Archello Scraper...")
        scraper = ArchelloScraper(headless=False)  # False для отладки, True для продакшн
        
        print(f"🎯 Цель: страницы с {START_PAGE} по {END_PAGE}")
        print("⏰ Ориентировочное время: 10-15 минут на страницу")
        
        # Запуск скрапинга
        all_data = scraper.scrape_multiple_pages(
            start_page=START_PAGE,
            end_page=END_PAGE,
            delay_between_pages=DELAY_BETWEEN_PAGES
        )
        
        print(f"\n{'='*50}")
        print(f"🎉 СКРАПИНГ ЗАВЕРШЕН!")
        print(f"📊 Всего собрано компаний: {len(all_data)}")
        print(f"💾 Файлы сохранены в текущей директории")
        print(f"{'='*50}")
        
    except Exception as e:
        print(f"💥 Критическая ошибка: {str(e)}")
    finally:
        if scraper:
            scraper.close()

if __name__ == "__main__":
    main()