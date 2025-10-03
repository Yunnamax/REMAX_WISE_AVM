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
from datetime import datetime
from urllib.parse import urljoin

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

class IdealistaScraperTest:
    def __init__(self):
        self.load_configs()
        self.load_mapping()
        self.setup_selenium()
    
    def setup_selenium(self):
        """Configure Selenium WebDriver"""
        chrome_options = Options()
    
        # Basic settings
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
    
        # Stealth settings
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--disable-extensions')
    
        # User-Agent
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
        # Create driver
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
    
        # Stealth script
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    def load_configs(self):
        """Load main configurations"""
        with open('config/idealista/operations.json', 'r') as f:
            self.operations = json.load(f)
        with open('config/idealista/property_types.json', 'r') as f:
            self.property_types = json.load(f)
        with open('config/idealista/cities.json', 'r') as f:
            self.cities = json.load(f)
    
    def load_mapping(self):
        """Load mapping for parameter conversion"""
        with open('config/idealista/url_mapping.json', 'r') as f:
            self.mapping = json.load(f)
    
    def build_url(self, operation, property_type, city):
        """Build URL using mapping"""
        op_pt = self.mapping['operations'][operation]
        prop_pt = self.mapping['property_types'][property_type]
        city_pt = self.mapping['cities'][city]
        
        url_path = f"{op_pt}-{prop_pt}"
        return f"https://www.idealista.pt/en/{url_path}/{city_pt}/"
    
    def extract_listing_links_simple(self):
        """Extract listing links - UPDATED SELECTOR"""
        try:
            # Wait for listings to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a.item-link"))
            )
            
            link_elements = self.driver.find_elements(By.CSS_SELECTOR, "a.item-link")
            links = []
            
            for link in link_elements:
                href = link.get_attribute('href')
                if href:
                    if href.startswith('/'):
                        absolute_url = urljoin("https://www.idealista.pt", href)
                        links.append(absolute_url)
                    else:
                        links.append(href)
            
            print(f"Found links: {len(links)}")
            
            # Remove duplicates
            unique_links = list(set(links))
            print(f"Unique links: {len(unique_links)}")
            
            return unique_links
            
        except Exception as e:
            print(f"Error extracting links: {e}")
            return []
    
    def get_next_page_simple(self):
        """Find next page - UPDATED SELECTOR"""
        try:
            # Try different pagination selectors
            next_selectors = [
                "a.icon-arrow-right-after",  # Main selector for Idealista
                "li.pagination-next > a",
                "a[data-qa='pagination-next']",
                "a.next",
                ".pagination .next > a"
            ]
            
            for selector in next_selectors:
                try:
                    next_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if next_btn.is_enabled():
                        href = next_btn.get_attribute('href')
                        if href:
                            print(f"Found next page: {href}")
                            if href.startswith('/'):
                                return urljoin("https://www.idealista.pt", href)
                            return href
                except:
                    continue
            
            print("Next page not found")
            return None
            
        except Exception as e:
            print(f"Error finding next page: {e}")
            return None
    
    def download_single_listing(self, url, operation, property_type, city):
        """Download listing HTML - IMPROVED VERSION"""
        try:
            print(f"Downloading listing: {url}")
            self.driver.get(url)
            
            # Wait for page load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(random.uniform(3, 5))
            
            # Extract listing_id from URL
            listing_id = url.split('/')[-2] if '/' in url else f"temp_{hash(url)}"
            
            # Save HTML
            html_path = f"{self.run_path}/{operation}/{property_type}/{city}/listings/{listing_id}.html"
            os.makedirs(os.path.dirname(html_path), exist_ok=True)
            
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            
            # Try different selectors for title
            title = self.extract_title()
            print(f"Downloaded: {listing_id} - {title}")
            
            return True
            
        except Exception as e:
            print(f"Error downloading {url}: {e}")
            return False
    
    def extract_title(self):
        """Extract title using different methods"""
        try:
            # Try different title selectors
            title_selectors = [
                "h1.main-info__title",
                ".info-header h1",
                "[data-qa='ad-detail-title']",
                "h1.info-title",
                "a.item-link"  # From your HTML example
            ]
            
            for selector in title_selectors:
                try:
                    title_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    title = title_element.text.strip()
                    if title:
                        return title
                except:
                    continue
            
            # If not found by selectors, try to get from attribute
            try:
                title_element = self.driver.find_element(By.CSS_SELECTOR, "a.item-link")
                title = title_element.get_attribute('title')
                if title:
                    return title
            except:
                pass
                
            return "Title not found"
            
        except Exception as e:
            return f"Error extracting title: {e}"
    
    def process_lisbon_only(self):
        """Process Lisbon only - FIXED PAGINATION"""
        operation = self.operations[0]
        property_type = self.property_types[0]
        city = "lisbon"
        
        print(f"Testing: {operation} + {property_type} + {city}")
        
        base_url = self.build_url(operation, property_type, city)
        current_url = base_url
        page_num = 1
        max_pages = 3  # Increased to 3 pages
        processed_links = set()  # Track processed links
        
        while current_url and page_num <= max_pages:
            print(f"\n{'='*50}")
            print(f"PAGE {page_num}: {current_url}")
            print(f"{'='*50}")
            
            # Load list page
            self.driver.get(current_url)
            time.sleep(random.uniform(5, 7))  # Increased delay
            
            # Extract listing links
            listing_links = self.extract_listing_links_simple()
            
            if not listing_links:
                print("No listings found on page")
                break
            
            # Filter already processed links
            new_links = [link for link in listing_links if link not in processed_links]
            print(f"New listings to process: {len(new_links)}")
            
            # Process new listings (first 3 for test)
            for i, listing_url in enumerate(new_links[:3]):
                success = self.download_single_listing(listing_url, operation, property_type, city)
                if success:
                    processed_links.add(listing_url)
                    print(f"   Processed {i+1}/{len(new_links[:3])}")
                time.sleep(random.uniform(3, 5))  # Increased delay
            
            # Go to next page
            next_url = self.get_next_page_simple()
            
            if next_url and next_url != current_url:
                current_url = next_url
                page_num += 1
                print(f"Moving to page {page_num}...")
                time.sleep(random.uniform(4, 6))
            else:
                print("Pagination completed or page limit reached")
                break
    
    def extract_data_from_downloaded_files(self):
        """Extract data from downloaded HTML files"""
        import pandas as pd
        from bs4 import BeautifulSoup
    
        data = []
    
        # Walk through all downloaded files
        for root, dirs, files in os.walk(self.run_path):
            for file in files:
                if file.endswith('.html'):
                    file_path = os.path.join(root, file)
                
                    with open(file_path, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                
                    soup = BeautifulSoup(html_content, 'html.parser')
                
                    # Extract data (even without perfect selectors)
                    listing_id = file.replace('.html', '')
                
                    # Simple parsing - find <title> tag
                    title = soup.find('title')
                    title_text = title.get_text() if title else "Title not found"
                
                    # Or find any h1 on page
                    h1 = soup.find('h1')
                    h1_text = h1.get_text() if h1 else "H1 not found"
                
                    data.append({
                        'listing_id': listing_id,
                        'file_path': file_path,
                        'title_tag': title_text,
                        'h1_text': h1_text,
                        'url': f"https://www.idealista.pt/en/empreendimento/{listing_id}/"
                    })
    
        # Save to CSV
        df = pd.DataFrame(data)
        csv_path = f"{self.run_path}/extracted_data.csv"
        df.to_csv(csv_path, index=False, encoding='utf-8')
        print(f"CSV created: {csv_path}")
        return df

    def run(self):
        """Run test"""
        self.run_id = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        self.run_path = f"data/bronze/idealista/run_{self.run_id}/"
        
        print(f"STARTING TEST SCRAPER: {self.run_path}")
        print("GOAL: Test downloading individual listings with pagination")
        
        try:
            self.process_lisbon_only()
            self.extract_data_from_downloaded_files()
            print(f"\nTEST COMPLETED!")
            print(f"Files saved in: {self.run_path}")
            
        finally:
            self.driver.quit()
            print("Driver closed")

if __name__ == "__main__":
    scraper = IdealistaScraperTest()
    scraper.run()