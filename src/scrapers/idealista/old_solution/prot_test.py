import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import random
import csv
import os
from datetime import datetime
from urllib.parse import urljoin

# --- ИМПОРТ КОНФИГА ---
# Убедитесь, что эти файлы существуют в той же папке!
from proxy_config import PROXY_ADDRESS, PROXY_CONFIG, PROFILES, ACTIVE_PROFILE 

# --- 1. ПАРАМЕТРЫ POC (КОНФИГУРАЦИЯ БЕРЕТСЯ ИЗ СЛОВАРЯ) ---
CONFIG = PROFILES[ACTIVE_PROFILE]

BASE_URL = CONFIG['BASE_URL']
PAGINATION_QUERY = CONFIG['PAGINATION_QUERY']
MAX_PAGES_TO_SCRAPE = CONFIG['MAX_PAGES_TO_SCRAPE']
LINK_CONTAINER_SELECTOR = CONFIG['LINK_CONTAINER_SELECTOR']
LINK_SELECTOR = CONFIG['LINK_SELECTOR']
MIN_DELAY_REQUEST = CONFIG['MIN_DELAY_REQUEST']

MAX_DELAY_PAGINATION = 12.0 # Общая константа для паузы между страницами

# --- 2. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

def get_download_path():
    """Определяет путь к папке 'Загрузки'"""
    home = os.path.expanduser("~")
    return os.path.join(home, "Downloads")

class UniversalScraperPoC: 
    
    def __init__(self):
        self.portal_name = ACTIVE_PROFILE
        print(f"--- {self.portal_name} PoC STARTED (WITH PROXY ROTATION) ---")
        self.output_path = os.path.join(get_download_path(), f"{self.portal_name}_links_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        
        # --- ИНИЦИАЛИЗАЦИЯ КРИТИЧЕСКИХ АТРИБУТОВ ---
        self.driver = self.initialize_uc_driver(proxy_address=PROXY_ADDRESS)
        self.csv_file, self.csv_writer = self.initialize_csv_file() # <--- csv_writer ОПРЕДЕЛЕН
        self.total_links_found = 0

    def initialize_uc_driver(self, proxy_address=None):
        """Инициализация Undetected ChromeDriver с опциями прокси"""
        options = Options()
        
        # --- НАСТРОЙКА PROXY ---
        if proxy_address:
            # Использование только хоста и порта для --proxy-server
            proxy_host_port = f"{PROXY_CONFIG['GATEWAY_HOST']}:{PROXY_CONFIG['PORT']}"
            options.add_argument(f'--proxy-server={proxy_host_port}')
            print(f"📡 Используется PROXY GATEWAY: {proxy_host_port}")
            
        # --- АРГУМЕНТЫ ДЛЯ СОКРЫТИЯ (HEADFUL) ---
        options.add_argument('window-size=1920,1080')
        options.add_argument("--start-maximized")
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        # Случайный User-Agent 
        user_agent = random.choice([
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
        ])
        options.add_argument(f'user-agent={user_agent}')
        
        # Инициализация UC
        driver = uc.Chrome(options=options)
        driver.implicitly_wait(10)
        return driver

    def restart_driver(self, proxy_address):
        """
        КРИТИЧЕСКАЯ ФУНКЦИЯ: Закрывает текущую сессию и запускает новую,
        чтобы заставить Evomi назначить новый IP-адрес.
        """
        print("\n🔄 РОТАЦИЯ: Перезапуск драйвера для нового IP...")
        try:
            self.driver.close()
            self.driver.quit()
        except Exception:
            pass # Игнорируем ошибки при закрытии
            
        # Запускаем новый, чистый драйвер с прокси
        self.driver = self.initialize_uc_driver(proxy_address=proxy_address)

    def initialize_csv_file(self):
        """Создание CSV-файла и запись заголовка"""
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        csv_file = open(self.output_path, 'w', newline='', encoding='utf-8')
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(['scraped_at', 'page_number', 'listing_url'])
        print(f"✅ CSV-файл создан: {self.output_path}")
        return csv_file, csv_writer

    def close_csv(self):
        """Корректно закрывает файл"""
        if self.csv_file:
            self.csv_file.close()

    def check_for_block(self):
        """Базовая проверка на капчу или блокировку"""
        page_source = self.driver.page_source.lower()
        if any(indicator in page_source for indicator in ['captcha', 'access denied', 'blocked', 'robot']):
            self.driver.save_screenshot(f"{self.portal_name}_blocked_page.png")
            print("❌ БЛОКИРОВКА / CAPTCHA ОБНАРУЖЕНА! PoC провален.")
            return True
        return False

    def extract_links_from_page(self, page_num):
        """Извлечение всех ссылок на объявления со страницы"""
        
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, LINK_CONTAINER_SELECTOR))
            )
        except Exception as e:
            print(f"⚠️ Ошибка: Контейнеры объявлений не загружены. Проверьте, не осталась ли страница на CAPTCHA. {e}")
            return []

        link_containers = self.driver.find_elements(By.CSS_SELECTOR, LINK_CONTAINER_SELECTOR)
        links = []
        
        for container in link_containers:
            try:
                link_element = container.find_element(By.CSS_SELECTOR, LINK_SELECTOR)
                href = link_element.get_attribute('href')
                
                if href:
                    final_url = urljoin(BASE_URL, href)
                    links.append(final_url)
                    
                    # --- ИСПОЛЬЗУЕМ self.csv_writer ---
                    self.csv_writer.writerow([
                        datetime.now().isoformat(),
                        page_num,
                        final_url
                    ])
                    self.total_links_found += 1
            except Exception:
                continue
                
        return links

    def run_poc(self):
        """Основной цикл PoC: проход по страницам с ротацией"""
        
        for page_num in range(1, MAX_PAGES_TO_SCRAPE + 1):
            
            # --- ШАГ РОТАЦИИ ---
            if page_num > 1:
                self.restart_driver(PROXY_ADDRESS) 
            
            current_url = BASE_URL
            if page_num > 1:
                current_url = f"{BASE_URL}{PAGINATION_QUERY}{page_num}"
            
            print(f"\n--- PAGE {page_num}/{MAX_PAGES_TO_SCRAPE} --- URL: {current_url}")
            
            # 1. ЭТИЧЕСКАЯ ЗАДЕРЖКА ПЕРЕД ЗАГРУЗКОЙ
            delay = random.uniform(MIN_DELAY_REQUEST, MIN_DELAY_REQUEST + 2.0)
            print(f"⏳ Ожидание (Request Delay): {delay:.1f}s...")
            time.sleep(delay)
            
            # 2. Загрузка страницы
            try:
                self.driver.get(current_url)
            except Exception as e:
                print(f"❌ Критическая ошибка при загрузке URL (Сетевая проблема с прокси): {e}")
                break

            # 3. ПРОВЕРКА НА БЛОКИРОВКУ
            if self.check_for_block():
                break
                
            # 4. Сбор и сохранение ссылок
            links_found = self.extract_links_from_page(page_num)
            print(f"✅ На странице {page_num} найдено и сохранено {len(links_found)} ссылок.")

            # 5. ДЛИТЕЛЬНАЯ ЗАДЕРЖКА МЕЖДУ СТРАНИЦАМИ
            if page_num < MAX_PAGES_TO_SCRAPE:
                delay = random.uniform(MAX_DELAY_PAGINATION - 2, MAX_DELAY_PAGINATION)
                print(f"⏳ Длительное ожидание (Pagination Delay): {delay:.1f}s...")
                time.sleep(delay)
                
        print("\n--- PoC ЗАВЕРШЕН ---")
        print(f"ИТОГО: Собрано {self.total_links_found} ссылок.")

    def run(self):
        """Запуск и очистка"""
        try:
            self.run_poc()
        finally:
            self.close_csv()
            try:
                self.driver.close()
                self.driver.quit()
            except:
                pass 
            print("Driver закрыт. Файл сохранен.")

# --- ЗАПУСК ---
if __name__ == "__main__":
    scraper = UniversalScraperPoC()
    scraper.run()