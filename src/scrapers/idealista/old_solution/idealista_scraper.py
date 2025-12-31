from selenium import webdriver
from selenium_stealth import stealth
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time
import random
import logging

class IdealistaNavigationTest:
    
    def __init__(self):
        self.setup_logger()  # ← ТЕПЕРЬ ЭТОТ МЕТОД СУЩЕСТВУЕТ
        self.setup_selenium_stealth()
        self.apply_stealth()
    
    def setup_logger(self):
        """Простой логгер"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info("🚀 Starting Navigation Test")
    
    def setup_selenium_stealth(self):
        """Улучшенная настройка с stealth опциями"""
        chrome_options = Options()
        
        # ⚠️ ОСТАВЛЯЕМ ОКНО ВИДИМЫМ для отладки
        # chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--start-maximized')
        
        # STEALTH НАСТРОЙКИ:
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--disable-extensions')
        
        # Случайный User-Agent
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        ]
        chrome_options.add_argument(f'--user-agent={random.choice(user_agents)}')
        
        # Дополнительные опции для маскировки
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--allow-running-insecure-content')
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        
        self.logger.info("✅ Stealth Selenium ready")
    
    def apply_stealth(self):
        """Применяем selenium-stealth для обхода детекции"""
        try:
            stealth(self.driver,
                languages=["en-US", "en"],
                vendor="Google Inc.",
                platform="Win32",
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True,
            )
            self.logger.info("✅ Stealth mode applied")
        except Exception as e:
            self.logger.warning(f"⚠️ Stealth failed: {e}")

    def human_like_behavior(self):
        """Имитация человеческого поведения"""
        try:
            # Случайная прокрутка
            scrolls = random.randint(2, 4)
            for i in range(scrolls):
                scroll_px = random.randint(200, 600)
                self.driver.execute_script(f"window.scrollBy(0, {scroll_px});")
                time.sleep(random.uniform(1, 3))
            
            # Случайные движения мыши
            actions = webdriver.ActionChains(self.driver)
            actions.move_by_offset(random.randint(50, 200), random.randint(50, 200))
            actions.perform()
            time.sleep(0.5)
            
        except Exception as e:
            self.logger.debug(f"Human behavior simulation: {e}")

    def wait_and_check_blocking(self, timeout=30):
        """Умное ожидание с проверкой блокировки"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Проверяем текущее состояние страницы
                current_url = self.driver.current_url
                page_title = self.driver.title.lower()
                page_source = self.driver.page_source.lower()
                
                # Признаки успешной загрузки
                success_indicators = ['article.item', 'listing', 'property', 'imovel']
                if any(indicator in page_source for indicator in success_indicators):
                    self.logger.info("✅ Page loaded successfully")
                    return True
                
                # Признаки блокировки
                block_indicators = ['captcha', 'challenge', 'security check', 'access denied', 'blocked']
                if any(indicator in page_source or indicator in page_title for indicator in block_indicators):
                    self.logger.warning("🛑 Blocking detected")
                    return False
                
                # Имитируем человеческое поведение во время ожидания
                if random.random() < 0.3:  # 30% chance
                    self.human_like_behavior()
                
                time.sleep(2)
                
            except Exception as e:
                self.logger.error(f"❌ Error during wait: {e}")
                return False
        
        self.logger.warning("⏰ Timeout waiting for page load")
        return False

    def test_basic_navigation(self):
        """Тест базовой навигации с улучшенной обработкой блокировки"""
        test_url = "https://www.idealista.pt/en/comprar-casas/lisboa/"
        
        try:
            self.logger.info(f"📄 Loading: {test_url}")
            self.driver.get(test_url)
            
            # Умное ожидание загрузки
            if not self.wait_and_check_blocking():
                self.logger.error("❌ Page blocked or failed to load")
                
                # Сохраняем скриншот для анализа
                self.driver.save_screenshot("blocked_debug.png")
                self.logger.info("📸 Screenshot saved: blocked_debug.png")
                
                # Показываем что видит скрипт
                current_url = self.driver.current_url
                page_title = self.driver.title
                self.logger.info(f"🔍 Current URL: {current_url}")
                self.logger.info(f"🔍 Page title: {page_title}")
                
                return False
            
            # Если дошли сюда - страница загрузилась успешно
            current_url = self.driver.current_url
            page_title = self.driver.title
            self.logger.info(f"📍 Current URL: {current_url}")
            self.logger.info(f"📝 Page title: {page_title}")
            
            # Имитируем человеческое поведение перед поиском элементов
            self.human_like_behavior()
            
            # Пробуем найти контейнеры объявлений
            try:
                containers = self.driver.find_elements(By.CSS_SELECTOR, "article.item")
                self.logger.info(f"📦 Found {len(containers)} article.item containers")
                
                if containers:
                    # Показываем несколько ссылок для демонстрации
                    links_found = 0
                    for i, container in enumerate(containers[:3]):
                        try:
                            link = container.find_element(By.CSS_SELECTOR, "a.item-link")
                            href = link.get_attribute('href')
                            if href and '/imovel/' in href:
                                links_found += 1
                                self.logger.info(f"   🔗 Link {i+1}: {href[:80]}...")
                        except:
                            continue
                    
                    self.logger.info(f"✅ Found {links_found} listing links")
                    return True
                else:
                    self.logger.warning("⚠️ No containers found")
                    return False
                    
            except Exception as e:
                self.logger.error(f"❌ Could not find containers: {e}")
                return False
                
        except Exception as e:
            self.logger.error(f"💥 Test failed: {e}")
            return False

    def run_tests(self):
        """Запуск всех тестов"""
        try:
            self.logger.info("\n" + "="*70)
            self.logger.info("🧪 STARTING IDEALISTA STEALTH NAVIGATION TESTS")
            self.logger.info("="*70)
            
            # Тест базовой навигации
            test_result = self.test_basic_navigation()
            
            if test_result:
                self.logger.info("\n🎉 BASIC NAVIGATION TEST PASSED!")
                # Можно добавить тест пагинации здесь
            else:
                self.logger.error("\n💥 BASIC NAVIGATION TEST FAILED")
                
        except Exception as e:
            self.logger.error(f"💥 Test suite failed: {e}")
        finally:
            input("\n🛑 Press Enter to close browser...")
            self.driver.quit()
            self.logger.info("✅ Browser closed")

if __name__ == "__main__":
    tester = IdealistaNavigationTest()
    tester.run_tests()