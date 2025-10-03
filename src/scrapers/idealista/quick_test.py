from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import sys
import os
import json
import time
import random
import requests
from datetime import datetime
from urllib.parse import urljoin

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

class IdealistaScraperWithMapping:
    def __init__(self):
        self.load_configs()
        self.load_mapping()
        self.setup_selenium()     
    
    def setup_selenium(self):
        """Настраиваем Selenium WebDriver"""
        chrome_options = Options()
    
        # Базовые настройки
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
    
        # STEALTH НАСТРОЙКИ (добавь эти строки!)
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--disable-extensions')
    
        # User-Agent
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
        # СОЗДАЕМ ДРАЙВЕР
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
    
        # STEALTH СКРИПТ (добавь эту строку!)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    def load_configs(self):
        """Загружаем основные конфиги"""
        with open('config/idealista/operations.json', 'r') as f:
            self.operations = json.load(f)
        with open('config/idealista/property_types.json', 'r') as f:
            self.property_types = json.load(f)
        with open('config/idealista/cities.json', 'r') as f:
            self.cities = json.load(f)
    
    def load_mapping(self):
        """Загружаем маппинг для преобразования параметров"""
        with open('config/idealista/url_mapping.json', 'r') as f:
            self.mapping = json.load(f)
    
    def build_url(self, operation, property_type, city):
        """Формируем URL используя маппинг"""
        # Преобразуем через маппинг
        op_pt = self.mapping['operations'][operation]
        prop_pt = self.mapping['property_types'][property_type]
        city_pt = self.mapping['cities'][city]  # Используем другое имя переменной, чтобы не перезаписать city
        
        # Склеиваем через дефис как один параметр
        url_path = f"{op_pt}-{prop_pt}"
        
        return f"https://www.idealista.pt/en/{url_path}/{city_pt}/"  # Убрал /en/ для португальской версии
    
    def download_page(self, url, save_path):
        """Downloading one page using Selenium"""
        try:
            print(f"🌐 Загружаю: {url}")
            self.driver.get(url)
            
            # Ждем загрузки тела страницы
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Дополнительная пауза для полной загрузки
            time.sleep(random.uniform(5, 8))
            
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            
            print(f"✅ Успешно сохранено: {os.path.basename(save_path)}")
            return True
            
        except Exception as e:
            print(f" Error: {url} - {e}")
            return False
    
    def run(self):
        """General lounch"""
        self.run_id = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        self.run_path = f"data/bronze/idealista/run_{self.run_id}/"
        
        print(f"  Selenium scraper lounch: {self.run_path}")
        
        try:
            for operation in self.operations:
                for property_type in self.property_types:
                    for city in self.cities[:3]:  # Только 3 города для теста
                        url = self.build_url(operation, property_type, city)
                        
                        # Сохраняем в структурированные папки
                        filename = f"{self.run_path}/{operation}/{property_type}/{city}/page_1.html"
                        
                        print(f" {operation} + {property_type} + {city}")
                        print(f"   → {url}")
                        
                        self.download_page(url, filename)
                        time.sleep(random.uniform(2, 4))  # Случайная пауза между запросами
        finally:
            # Закрываем драйвер после завершения
            self.driver.quit()
            print("🔚 Драйвер закрыт")

if __name__ == "__main__":
    scraper = IdealistaScraperWithMapping()
    scraper.run()