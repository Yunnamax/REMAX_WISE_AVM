from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import sys
import os
import logging
import logging.config
import yaml
import json
import time
import random
import csv
from datetime import datetime
from urllib.parse import urljoin
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

class IdealistaScraperCSV:
    """
    Selenium-based scraper for Idealista real estate listings (Portugal).
    - Collects property data (title, price, area, location, etc.)
    - Handles anti-bot detection and pagination
    - Outputs structured CSV files under data/bronze/idealista/
    """ 
    def setup_logger(self, site_name="idealista"):
        """Setup logger with dynamic file paths per site"""
        try:
            # 1. Сначала создаем папки
            os.makedirs("logs/scraping", exist_ok=True)
            os.makedirs("logs/errors", exist_ok=True)
            
            # 2. Создаем логгер с нуля вместо использования конфига
            self.logger = logging.getLogger(f'scraper_{site_name}')
            self.logger.setLevel(logging.INFO)
            
            # Очищаем старые обработчики
            for handler in self.logger.handlers[:]:
                self.logger.removeHandler(handler)
            
            # 3. Создаем форматтер
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            
            # 4. Обработчик для основного лога
            scraping_handler = logging.FileHandler(
                f"logs/scraping/{site_name}.log", 
                encoding='utf-8'
            )
            scraping_handler.setLevel(logging.INFO)
            scraping_handler.setFormatter(formatter)
            self.logger.addHandler(scraping_handler)
            
            # 5. Обработчик для ошибок
            error_handler = logging.FileHandler(
                f"logs/errors/{site_name}_errors.log", 
                encoding='utf-8'
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(formatter)
            self.logger.addHandler(error_handler)
            
            # 6. Консольный обработчик для отладки
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
            
            # Тестовое сообщение
            self.logger.info(f"Logger setup completed for {site_name}")
            
        except Exception as e:
            # Простой fallback
            print(f"Error setting up logger: {e}")
            self.logger = logging.getLogger('scraper_fallback')
            if not self.logger.handlers:
                handler = logging.StreamHandler()
                handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
                self.logger.addHandler(handler)
                self.logger.setLevel(logging.INFO)
            self.logger.error(f"Failed to setup proper logger: {e}")
    def __init__(self, site_name="idealista"):
        # Сначала настраиваем логгер
        self.setup_logger(site_name=site_name)
        
        # Потом загружаем конфиги (они используют уже настроенный логгер)
        self.load_configs()
        self.load_mapping()
        
        # Остальное без изменений
        self.setup_selenium()
        self.csv_file = None
        self.csv_writer = None
     
    def setup_selenium(self):
        """Configure Selenium WebDriver - FIXED JAVASCRIPT ERROR"""
        chrome_options = Options()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # FIXED JavaScript - removed arrow function
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: function() { return undefined; }})")
    
    def load_configs(self):
        """Load main configurations"""
        try:
            with open('config/idealista/operations.json', 'r') as f:
                self.operations = json.load(f)
            with open('config/idealista/property_types.json', 'r') as f:
                self.property_types = json.load(f)
            with open('config/idealista/cities.json', 'r') as f:
                self.cities = json.load(f)
            
            # ИСПРАВИЛ: используем self.logger вместо print
            self.logger.info("Configs loaded successfully")
            
        except Exception as e:
            # ИСПРАВИЛ: используем self.logger для ошибок
            self.logger.error(f"Error loading configs: {e}")
            
            # Default values for testing
            self.operations = ["sale"]
            self.property_types = ["apartments"]
            self.cities = ["lisbon"]
    
    def load_mapping(self):
        """Load mapping for parameter conversion"""
        try:
            with open('config/idealista/url_mapping.json', 'r') as f:
                self.mapping = json.load(f)
            
            # ИСПРАВИЛ: используем self.logger
            self.logger.info("Mapping loaded successfully")
            
        except Exception as e:
            # ИСПРАВИЛ: используем self.logger
            self.logger.error(f"Error loading mapping: {e}")
            
            # Default mapping for testing
            self.mapping = {
                'operations': {'sale': 'venda'},
                'property_types': {'apartments': 'apartamento'},
                'cities': {'lisbon': 'lisboa'}
            }
    
    def build_url(self, operation, property_type, city):
        """Build URL using mapping"""
        try:
            op_pt = self.mapping['operations'].get(operation, operation)
            prop_pt = self.mapping['property_types'].get(property_type, property_type)
            city_pt = self.mapping['cities'].get(city, city)
            
            url_path = f"{op_pt}-{prop_pt}"
            """self.logger.info(f"URL built successfully: {url}")"""
            return f"https://www.idealista.pt/en/comprar-casas/lisboa/"
        except Exception as e:
            print(f"Error building URL: {e}")
            self.logger.error(f"Error building URL: {e}")
            return f"https://www.idealista.pt/en/comprar-casas/lisboa/"
    
    def setup_csv(self):
        """Initialize CSV file with headers"""
        csv_path = f"{self.run_path}/idealista_data.csv"
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        
        self.csv_file = open(csv_path, 'w', newline='', encoding='utf-8')
        self.csv_writer = csv.writer(self.csv_file)
        
        headers = [
            'listing_id', 'url', 'scraped_at', 'operation', 'property_type', 'city',
            'title', 'price', 'area', 'bedrooms', 'bathrooms', 'location',
            'description', 'property_type_detail', 'update_date', 
            'agency', 'energy_certificate'
        ]
        
        self.csv_writer.writerow(headers)
        self.logger.info(f"CSV created: {csv_path}")
        return csv_path
    
    def close_csv(self):
        """Close CSV file properly"""
        if self.csv_file:
            self.csv_file.close()
            self.logger.info("CSV file closed")
    
    def extract_listing_links_simple(self):
        """Find listings through article.item containers - RELIABLE VERSION"""
        try:
            # Wait for listing containers to load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "article.item"))
            )
            
            # 1. First find ALL listing containers
            article_containers = self.driver.find_elements(By.CSS_SELECTOR, "article.item")
            print(f"Found listing containers (article.item): {len(article_containers)}")
            
            links = []
            
            # 2. Extract link from each container
            for article in article_containers:
                try:
                    # Find link inside container
                    link_element = article.find_element(By.CSS_SELECTOR, "a.item-link")
                    href = link_element.get_attribute('href')
                    
                    if href:
                        if href.startswith('/'):
                            absolute_url = urljoin("https://www.idealista.pt", href)
                            links.append(absolute_url)
                        else:
                            links.append(href)
                            
                except Exception as e:
                    # If one container doesn't have link - skip
                    continue
            
            print(f"Links extracted from containers: {len(links)}")
            
            # DEBUG: show types of found links
            if links:
                imovel_count = sum(1 for link in links if '/imovel/' in link)
                empreendimento_count = sum(1 for link in links if '/empreendimento/' in link)
                print(f"Regular listings: {imovel_count}")
                print(f"New developments: {empreendimento_count}")
                
                # Show examples
                for i, link in enumerate(links[:2]):
                    print(f"   Example {i+1}: {link}")
            
            return links
            
        except Exception as e:
            print(f"Error extracting links through containers: {e}")
            return []
    
    def get_next_page_reliable(self):
        try:
            print("next page search...")
            
            try:
                next_element = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "li.next a"))
                )
                href = self.driver.execute_script('return arguments[0].getAttribute("href")', next_element)
                
                if href:
                    print(f"next page is found: {href}")
                    if href.startswith('/'):
                        return "https://www.idealista.pt" + href
                    return href
                    
            except Exception as e:
                print(f"first selector has is not working: {e}")
            
            # trying alternative selector
            try:
                next_element = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a.icon-arrow-right-after"))
                )
                href = self.driver.execute_script('return arguments[0].getAttribute("href")', next_element)
                
                if href:
                    print(f"next page is found (alternative selector): {href}")
                    if href.startswith('/'):
                        return "https://www.idealista.pt" + href
                    return href
                    
            except Exception as e:
                print(f"alternative selector did not work: {e}")
            
            # text search
            try:
                next_element = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//a[contains(text(), 'Next') or contains(text(), 'Seguinte')]"))
                )
                href = self.driver.execute_script('return arguments[0].getAttribute("href")', next_element)
                
                if href:
                    print(f"next page is found in text: {href}")
                    if href.startswith('/'):
                        return "https://www.idealista.pt" + href
                    return href
                    
            except Exception as e:
                print(f"in text did not work: {e}")
            
            print("could not find the next page")
            return None
            
        except Exception as e:
            print(f"general pafination mistake: {e}")
            return None
    
    def debug_page_content(self, url):
        """Debug method to see what's on the page"""
        try:
            print(f"PAGE DEBUG: {url}")
            
            # Check page title
            title = self.driver.title
            print(f"   Page title: {title}")
            
            # Check if it's a new development page
            if 'empreendimento' in url:
                print("   This is a new development page (empreendimento)")
            
            # Try to find any price elements
            price_selectors = ["[class*='price']", "[class*='Price']", ".price", ".preco"]
            for selector in price_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        print(f"   Found elements with selector '{selector}': {len(elements)}")
                        for i, elem in enumerate(elements[:2]):
                            print(f"     Element {i+1}: {elem.text[:50]}...")
                except:
                    pass
                    
        except Exception as e:
            print(f"Debug error: {e}")
    
    def extract_listing_data(self, url, operation, property_type, city):
        """Extract structured data from listing page - IMPROVED VERSION"""
        try:
            print(f"Processing listing: {url}")
            self.driver.get(url)
            
            # Wait for page load
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(random.uniform(3, 5))
            
            # Debug page content
            self.debug_page_content(url)
            
            # Extract listing ID from URL
            listing_id = url.split('/')[-2] if '/' in url else f"temp_{hash(url)}"
            
            # Initialize data dictionary
            data = {
                'listing_id': listing_id,
                'url': url,
                'scraped_at': datetime.now().isoformat(),
                'operation': operation,
                'property_type': property_type,
                'city': city
            }
            
            # Extract basic info
            data.update(self.extract_basic_info())
            
            # Save to CSV
            self.save_to_csv(data)
            print(f"Data saved: {data.get('title', 'N/A')}")
            
            return True
            
        except Exception as e:
            print(f"Error processing {url}: {e}")
            return False

    def extract_features_from_details(self, description=''):
        """IMPROVED version - extracts all features using JavaScript"""
        features_data = {
            'bathrooms': None,
            'bedrooms': None,
            'property_type_detail': None,
            'completion_year': None,
            'status': None,
            'energy_certificate': None,
            'update_date': None,
            'agency': None
        }
        
        try:
            # 1. Search ALL elements with features using JavaScript
            features_text = self.safe_extract_text_js(".details-property_features") or \
                        self.safe_extract_text_js(".info-features") or \
                        self.safe_extract_text_js(".details-property")
            
            if not features_text:
                print("   Features block not found")
                # Continue execution for other fields
            else:
                text_lower = features_text.lower()
                print(f"   Features text: '{features_text}'")
                
                # 2. BATHROOMS - improved search
                bathroom_patterns = [
                    r'(\d+)\s*bathroom',
                    r'(\d+)\s*banho',
                    r'(\d+)\s*casa de banho',
                    r'(\d+)\s*wc',
                    r'(\d+)\s*bath'
                ]
                
                for pattern in bathroom_patterns:
                    match = re.search(pattern, text_lower)
                    if match:
                        features_data['bathrooms'] = int(match.group(1))
                        print(f"   Bathrooms found: {features_data['bathrooms']}")
                        break
                
                # 3. BEDROOMS - improved search
                bedroom_patterns = [
                    r'(\d+)\s*bedroom', 
                    r'(\d+)\s*quarto',
                    r't(\d+)',  # T3, T2 etc.
                    r'(\d+)\s*quartos',
                    r'(\d+)\s*room',
                    r'(\d+)\s*hab'
                ]
                
                for pattern in bedroom_patterns:
                    match = re.search(pattern, text_lower)
                    if match:
                        features_data['bedrooms'] = int(match.group(1))
                        print(f"   Bedrooms found: {features_data['bedrooms']}")
                        break
                
                # 4. ADDITIONAL CHARACTERISTICS
                # Property type (apartment, house, etc.)
                type_patterns = [
                    r'terraced house', r'apartment', r'studio', r'villa', 
                    r'house', r'flat', r'penthouse'
                ]
                
                for pattern in type_patterns:
                    if re.search(pattern, text_lower):
                        features_data['property_type_detail'] = pattern.replace('_', ' ')
                        print(f"   Property type: {features_data['property_type_detail']}")
                        break
                
                # 5. CONSTRUCTION YEAR / DELIVERY DATE
                year_match = re.search(r'(\d{4})', features_text)
                if year_match:
                    year = int(year_match.group(1))
                    if 1900 < year < 2030:  # Realistic range
                        features_data['completion_year'] = year
                        print(f"   Completion year: {features_data['completion_year']}")
                
                # 6. STATUS (new, renovated, etc.)
                status_patterns = [
                    r'new build', r'new construction', r'renovated', r'to renovate',
                    r'new home', r'brand new'
                ]
                
                for pattern in status_patterns:
                    if re.search(pattern, text_lower):
                        features_data['status'] = pattern.replace('_', ' ')
                        print(f"   Status: {features_data['status']}")
                        break

            # 7. LISTING UPDATE DATE
            try:
                update_element = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".stats-text"))
                )
                features_data['update_date'] = self.driver.execute_script('return arguments[0].textContent', update_element).strip()
                print(f"   Update date FOUND: '{features_data['update_date']}'")
            except Exception as e:
                print(f"   Update date not found: {e}")

            # 9. ENERGY CERTIFICATE - improved search
            if description:
                energy_patterns = [
                    r'Energy Rating:\s*([A-Z][+\-]?)',
                    r'Energy Certificate:\s*([A-Z][+\-]?)', 
                    r'Energy certification:\s*([A-Z][+\-]?)',
                    r'Certificado Energético:\s*([A-Z][+\-]?)',
                    r'Classificação Energética:\s*([A-Z][+\-]?)'
                ]
                
                for pattern in energy_patterns:
                    energy_match = re.search(pattern, description, re.IGNORECASE)
                    if energy_match:
                        features_data['energy_certificate'] = energy_match.group(1)
                        print(f"   Energy certificate: {features_data['energy_certificate']}")
                        break
                else:
                    # If not found in description, search in other places
                    try:
                        energy_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Energy Rating') or contains(text(), 'Certificado')]")
                        for elem in energy_elements:
                            text = self.driver.execute_script('return arguments[0].textContent', elem)
                            for pattern in energy_patterns:
                                energy_match = re.search(pattern, text, re.IGNORECASE)
                                if energy_match:
                                    features_data['energy_certificate'] = energy_match.group(1)
                                    print(f"   Energy certificate (alternative): {features_data['energy_certificate']}")
                                    break
                            if features_data['energy_certificate']:
                                break
                    except:
                        pass

        except Exception as e:
            print(f"   Error extracting features: {e}")

        return features_data

    def safe_extract_text_js(self, css_selector, timeout=10):
        """Universal method for extracting text via JavaScript"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, css_selector))
            )
            return self.driver.execute_script('return arguments[0].textContent', element).strip()
        except:
            return ""

    def extract_basic_info(self):
        """FIXED version using JavaScript for hidden elements"""
        data = {}
        
        # Give time for full load
        time.sleep(3)
        
        # 1. TITLE - use JavaScript for hidden elements
        try:
            title_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".main-info__title-main"))
            )
            # FIXED: get text via JavaScript
            data['title'] = self.driver.execute_script('return arguments[0].textContent', title_element).strip()
            print(f"   Title FOUND: '{data['title']}'")
        except Exception as e:
            print(f"   Title not found: {e}")
            data['title'] = ""

        # 2. PRICE - also use JavaScript
        try:
            price_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".info-data-price"))
            )
            data['price'] = self.driver.execute_script('return arguments[0].textContent', price_element).strip()
            print(f"   Price FOUND: '{data['price']}'")
        except Exception as e:
            print(f"   Price not found: {e}")
            data['price'] = ""

        # 3. AREA - use JavaScript
        try:
            # Find element containing m² via XPath, but get text via JS
            area_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'm²')]"))
            )
            data['area'] = self.driver.execute_script('return arguments[0].textContent', area_element).strip()
            print(f"   Area FOUND: '{data['area']}'")
        except Exception as e:
            print(f"   Area not found: {e}")
            data['area'] = ""

        # 4. LOCATION - use JavaScript
        try:
            location_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".main-info__title-minor"))
            )
            data['location'] = self.driver.execute_script('return arguments[0].textContent', location_element).strip()
            print(f"   Location FOUND: '{data['location']}'")
        except Exception as e:
            print(f"   Location not found: {e}")
            data['location'] = ""

        # 5. DESCRIPTION - use JavaScript
        try:
            desc_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".adCommentsLanguage"))
            )
            full_description = self.driver.execute_script('return arguments[0].textContent', desc_element).strip()
            data['description'] = full_description[:200] + "..." if len(full_description) > 200 else full_description
            print(f"   Description FOUND: '{data['description'][:100]}...'")
        except Exception as e:
            print(f"   Description not found: {e}")
            data['description'] = ""

        # 6. CHARACTERISTICS (bedrooms, bathrooms)
        features_data = self.extract_features_from_details(data.get('description', ''))
        data.update(features_data)
        # Listing update date
        try:
            update_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".stats-text"))
            )
            data['update_date'] = self.driver.execute_script('return arguments[0].textContent', update_element).strip()
            print(f"   Update date FOUND: '{data['update_date']}'")
        except Exception as e:
            print(f"   Update date not found: {e}")
            data['update_date'] = ""

        # Agency
        try:
            agency_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".professional-name .name"))
            )
            data['agency'] = self.driver.execute_script('return arguments[0].textContent', agency_element).strip()
            print(f"   Agency FOUND: '{data['agency']}'")
        except Exception as e:
            print(f"   Agency not found: {e}")
            data['agency'] = ""
        
        return data

    def safe_extract_text(self, selectors, max_chars=None):
        """Safely extract text using multiple selectors"""
        for selector in selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                text = element.text.strip()
                if text:
                    if max_chars:
                        text = text[:max_chars]
                    return text
            except:
                continue
        return ""
    
    def save_to_csv(self, data):
        """Save extracted data to CSV with updated fields"""
        try:
            row = [
                data.get('listing_id', ''),
                data.get('url', ''),
                data.get('scraped_at', ''),
                data.get('operation', ''),
                data.get('property_type', ''),
                data.get('city', ''),
                data.get('title', ''),
                data.get('price', ''),
                data.get('area', ''),
                data.get('bedrooms', ''),
                data.get('bathrooms', ''),
                data.get('location', ''),
                data.get('description', ''),
                data.get('property_type_detail', ''),
                data.get('update_date', ''),
                data.get('agency', ''),                    # Agency
                data.get('energy_certificate', '')         # Energy certificate
            ]
            self.csv_writer.writerow(row)
            return True
        except Exception as e:
            print(f"Error writing to CSV: {e}")
            return False
    
    def process_lisbon_apartments(self):
        """Process Lisbon apartments (regular listings, not new developments)"""
        operation = "sale"
        property_type = "apartments" 
        city = "lisbon"
        
        print(f"Testing: {operation} + {property_type} + {city}")
        
        base_url = self.build_url(operation, property_type, city)
        current_url = base_url
        page_num = 1
        max_pages = 100  # Increased page limit
        processed_links = set()
        total_listings = 0
        
        while current_url and page_num <= max_pages:
            print(f"\n{'='*60}")
            print(f"PAGE {page_num}: {current_url}")
            print(f"{'='*60}")
            
            # Load list page
            self.driver.get(current_url)
            time.sleep(random.uniform(5, 7))
            
            # Extract listing links
            listing_links = self.extract_listing_links_simple()
            
            if not listing_links:
                print("No listings found on page")
                # Try to find next page even if no listings
                next_url = self.get_next_page_simple()
                if next_url and next_url != current_url:
                    current_url = next_url
                    page_num += 1
                    continue
                else:
                    break
            
            # Filter already processed links
            new_links = [link for link in listing_links if link not in processed_links]
            print(f"New listings to process: {len(new_links)}")
            
            # FIX: remove [:3] limitation - process ALL new links
            for i, listing_url in enumerate(new_links):  # ← REMOVED [:3]
                success = self.extract_listing_data(listing_url, operation, property_type, city)
                if success:
                    processed_links.add(listing_url)
                    total_listings += 1
                    print(f"   Processed {i+1}/{len(new_links)} (total: {total_listings})")
                time.sleep(random.uniform(2, 4))  # Reduced delay
            
            # Go to next page
            next_url = self.get_next_page_reliable()
            
            if next_url and next_url != current_url:
                current_url = next_url
                page_num += 1
                print(f"Moving to page {page_num}...")
                time.sleep(random.uniform(3, 5))
            else:
                print("Pagination completed or page limit reached")
                break
        
        print(f"\nTOTAL: Processed {total_listings} listings")
        return total_listings
    
    def run(self):
        """Run the scraper with direct CSV output"""
        self.run_id = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        self.run_path = f"data/bronze/idealista/run_{self.run_id}/"
        
        print(f"SCRAPER START: {self.run_path}")
        print("TARGET: Regular listings (apartments) instead of new developments")
        
        try:
            csv_path = self.setup_csv()
            
            total_processed = self.process_lisbon_apartments()
            
            print(f"\nSCRAPING COMPLETED!")
            print(f"Processed listings: {total_processed}")
            print(f"Data saved to: {csv_path}")
            
        except Exception as e:
            print(f"Critical error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.close_csv()
            self.driver.quit()
            print("Driver closed")

if __name__ == "__main__":
    scraper = IdealistaScraperCSV()
    scraper.run()