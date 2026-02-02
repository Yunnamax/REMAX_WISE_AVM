"""
ImovirtualScraper - Concrete scraper implementation for Imovirtual portal.
"""
import hashlib
import re
import asyncio
import json
import random
import time
from datetime import datetime
import csv
from typing import Dict, List, Any, Optional
from playwright.async_api import async_playwright
from abc import ABC, abstractmethod
import random

from scrapers.real_estate_portal_scraper import RealEstatePortalScraper
from .imovirtual_strategies import (
    ImovirtualStrategy,
    ApartmentRentStrategy
)

class ImovirtualScraper(RealEstatePortalScraper):
    """
    Unified scraper for ALL property types on Imovirtual portal.
    
    Supports: apartment_rent, apartment_sale, house_rent, house_sale, etc.
    """
    # ===========================================
    # DEFAULT CONSTANTS (for all Imovirtual)
    # ===========================================


    # Browser settings temporary + stable spider approach

    # New canstants
    DETAIL_BUDGET_BEFORE_COOLDOWN = 40  # 40 детальных страниц за сессию
    COOLDOWN_SECONDS_RANGE = (120, 240)  # 2-4 минуты перерыва
    SKIP_FIRST_ADS = 5  # Пропустить первые 5 спонсированных объявлений
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) AppleWebKit/605.1.15 Safari/16.5',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/123.0.0.0 Safari/537.36',
    ]
    DEFAULT_HEADLESS = False
    DEFAULT_TIMEOUT = 60000  # 60 seconds (увеличили с 30)
    DEFAULT_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    DEFAULT_VIEWPORT = {'width': 1920, 'height': 1080}

    # Scraping settings
    DEFAULT_MAX_PAGES = 40              # 40 страниц (было 5)
    DEFAULT_MAX_LISTINGS_PER_PAGE = 0    # 0 = все объявления (было 3)
    DEFAULT_REQUEST_DELAY = (3, 7)       # 3-7 секунд (было 1-3)
    
    # Browser settings
    #DEFAULT_HEADLESS = True
    #DEFAULT_TIMEOUT = 30000  # 30 seconds
    #DEFAULT_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    #DEFAULT_VIEWPORT = {'width': 1920, 'height': 1080}

    # Scraping settings
    #DEFAULT_MAX_PAGES = 5
    #DEFAULT_MAX_LISTINGS_PER_PAGE = 3
    #DEFAULT_REQUEST_DELAY = (1, 3)  # seconds

    # Imovirtual constants
    BASE_URL = "https://www.imovirtual.com"

    def __init__(self, property_type: str, municipality: str, **kwargs):
            """
            Initialize Imovirtual scraper.

            Args:
                property_type: Type of property (apartment_rent, apartment_sale, etc.)
                municipality: Location to scrape (e.g., "lisbon", "porto")
                **kwargs: Additional configuration:
                    - max_pages: Maximum number of pages to scrape (default: 5)
                    - headless: Run browser in headless mode (default: True)
                    - max_listings_per_page: Limit listings per page for testing (default: 3)
                    - request_delay: Delay between requests in seconds (default: (1, 3))
            """

            # ===========================================
            # 1. ALL default parameters
            # ===========================================
            
            # Browser settings (from class constants)
            headless = self.DEFAULT_HEADLESS
            timeout = self.DEFAULT_TIMEOUT
            user_agent = self.DEFAULT_USER_AGENT
            viewport = self.DEFAULT_VIEWPORT
            
            # Scraping settings (from class constants)
            max_pages = self.DEFAULT_MAX_PAGES
            max_listings_per_page = self.DEFAULT_MAX_LISTINGS_PER_PAGE
            request_delay = self.DEFAULT_REQUEST_DELAY

            # ===========================================
            # 2. Save settings to self
            # ===========================================
            
            self.strategy = self._create_strategy(property_type)

            # Browser settings
            self.headless = headless
            self.timeout = timeout
            self.user_agent = user_agent
            self.viewport = viewport
            
            # Scraping settings
            self.max_pages = max_pages
            self.max_listings_per_page = max_listings_per_page
            self.request_delay_range = request_delay
            self.scraped_data = []

            # Call parent constructor
            super().__init__(
                source_name="imovirtual",
                property_type=property_type,
                municipality=municipality,
                **kwargs
            )

            # Detailed pages counter
            self.detail_visits = 0
            self.current_ua = random.choice(self.USER_AGENTS)  # Current User-Agent
            self.current_search_url = None

            # ===========================================
            # 3. Initialize web infrastructure
            # ===========================================

            self._init_web_infrastructure()

            self.logger.info(f"Initialized ImovirtualScraper for {property_type} in {municipality}")
    
    # Methods unique to all strategies:
    def _create_strategy(self, property_type: str) -> ImovirtualStrategy:
        """Factory method — creates a strategy based on the property type."""
        # Simple factory using if-elif branching
        if property_type == "apartment_rent":
            return ApartmentRentStrategy()
        else:
            raise ValueError(f"Unknown property type: {property_type}")
        
    def _init_web_infrastructure(self):
            """
            Initialize web infrastructure for Imovirtual.
            Sets up configuration but does NOT launch browser.
            
            Called automatically from __init__.
            """
            self.logger.info("Initializing Imovirtual web infrastructure (config only)")
            
            # Webdriver configuration (Playwright)
            self.webdriver_config = {
                'headless': self.headless,
                'timeout': 30000,  # 30 seconds
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'viewport': {'width': 1920, 'height': 1080},
                'args': [
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled'
                ]
            }
            
            # Browser state attributes (all None until launch)
            self.playwright = None      # Playwright instance
            self.browser = None        # Playwright browser  
            self.page = None           # Playwright page
            self.session = None        # Requests session (if needed)

    def _regenerate_browser_context(self):
        """
        Full regeneration of the browser context — like in that scraper.
        Closes the old context and creates a new one with a random UA and parameters.
        """
        if hasattr(self, 'browser_context') and self.browser_context:
            try:
                self.browser_context.close()
            except:
                pass
        
        # New random UA
        self.current_ua = random.choice(self.USER_AGENTS)
        
        # Create a new context with the new UA
        context = self.browser.new_context(
            user_agent=self.current_ua,
            locale='pt-PT',  # Portuguese locale
            timezone_id='Europe/Lisbon',  # Portugal timezone
            viewport={'width': random.randint(1200, 1440), 
                    'height': random.randint(800, 950)},
            extra_http_headers={
                'Accept-Language': 'pt-PT,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                'Referer': 'https://www.imovirtual.com/'
            }
        )
        
        # Apply resource blocking 
        def block_resources(route):
            resource_type = route.request.resource_type
            if resource_type in ["image", "font", "stylesheet"]:
                route.abort()
            else:
                route.continue_()

        # Apply resource blocking (you already have this)
        context.route("**/*", block_resources)
        
        self.browser_context = context
        self.page = context.new_page()
        

        if hasattr(self, 'current_search_url'):
            self.page.goto(self.current_search_url)
            time.sleep(3)  # Wait for page to load
            self._accept_cookies()

        self.detail_visits = 0  # Reset the counter

    def setup_webdriver(self):
        """
        Initialize and configure Playwright browser with comprehensive anti-detection measures.
        
        This implementation focuses on bypassing bot protection systems while maintaining
        the existing synchronous architecture. Key features include:
        - Resource blocking to prevent fingerprinting via images, fonts, and CSS
        - Realistic HTTP headers and user-agent rotation
        - Randomized viewport and behavioral patterns
        - Geographic emulation for Portugal
        - Anti-automation JavaScript injection
        
        The method is idempotent - subsequent calls return immediately if browser is already running.
        """
        
        # ===========================================
        # 1. Idempotency Check
        # ===========================================
        if self.page is not None:
            self.logger.info("Web driver already initialized, skipping setup...")
            return
        
        try:
            self.logger.info("Initializing Playwright browser with anti-detection measures...")
            
            # Import required modules
            from playwright.sync_api import sync_playwright
            import random
            import time
            
            # ===========================================
            # 2. Enhanced Browser Arguments for Stealth
            # ===========================================
            
            # Comprehensive stealth arguments based on analyzed working scraper
            stealth_args = self.webdriver_config.get('args', []) + [
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-accelerated-2d-canvas',
                '--disable-gpu',
                '--no-first-run',
                '--no-zygote',
                '--disable-web-security',
                '--disable-site-isolation-trials',
                '--disable-features=BlockInsecurePrivateNetworkRequests',
                '--disable-component-update',
                '--disable-default-apps',
                '--disable-background-networking',
                '--disable-sync',
                '--disable-translate',
                '--metrics-recording-only',
                '--disable-background-timer-throttling',
                '--disable-renderer-backgrounding',
                '--disable-backgrounding-occluded-windows',
            ]
            
            # ===========================================
            # 3. Realistic User-Agent Pool
            # ===========================================
            
            # Multiple realistic user agents from analyzed working scraper
            USER_AGENTS = [
                # Windows + Chrome (most common)
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                
                # Mac + Chrome
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                
                # Windows + Firefox
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) '
                'Gecko/20100101 Firefox/124.0',
                
                # Linux + Chrome (from analyzed scraper)
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            ]
            
            # Select random user agent for this session
            selected_user_agent = random.choice(USER_AGENTS)
            
            # ===========================================
            # 4. Initialize Playwright and Launch Browser
            # ===========================================
            
            # Start Playwright instance
            self.playwright = sync_playwright().start()
            
            # Launch browser with stealth configuration
            self.browser = self.playwright.chromium.launch(
                headless=self.headless,
                args=stealth_args,
                # Random slow motion between actions (from analyzed scraper: 80-150ms)
                slow_mo=random.randint(80, 150),
                timeout=45000,  # 45 second timeout
            )
            
            # ===========================================
            # 5. Create Browser Context with Portuguese Profile
            # ===========================================
            
            # Randomized viewport dimensions (matching analyzed scraper range)
            viewport_width = random.randint(1200, 1440)
            viewport_height = random.randint(800, 950)
            
            # HTTP headers from analyzed working scraper
            extra_headers = {
                'Accept-Language': 'pt-PT,pt;q=0.9,en-US;q=0.8,en;q=0.7', 
                'Accept': 'text/html,application/xhtml+xml,application/xml;'
                        'q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,'
                        'application/signed-exchange;v=b3;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Upgrade-Insecure-Requests': '1',
                'Connection': 'keep-alive',
                'Cache-Control': 'max-age=0',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Referer': 'https://www.google.com/',
            }
            
            # Create context with Portuguese user profile
            context = self.browser.new_context(
                # Identity
                user_agent=selected_user_agent,
                locale='pt-PT',  # Portuguese locale
                timezone_id='Europe/Lisbon',   #Portugal timezone
                #locale='en-US',
                #timezone_id='America/New_York',
                
                # Randomized viewport
                viewport={'width': viewport_width, 'height': viewport_height},
                
                # HTTP headers from working scraper
                extra_http_headers=extra_headers,
                
                # Geographic emulation (Portugal)
                geolocation={
                    "latitude": 38.7223,  # Lisbon
                    "longitude": -9.1393,
                    "accuracy": 50
                    #"latitude": 40.7128,
                    #"longitude": -74.0060,
                    #"accuracy": 50
                },
                
                # Device characteristics
                has_touch=False,
                is_mobile=False,
                device_scale_factor=1,
                
                # Privacy/security
                permissions=['geolocation'],
                color_scheme='light',
                
                # Fresh session each time
                storage_state=None,
            )
            
            # ===========================================
            # 6. Resource Blocking - CRITICAL for bot protection
            # ===========================================
            
            def block_unnecessary_resources(route):
                """
                Block resources that aid in bot detection but aren't needed for scraping.
                This significantly reduces fingerprinting and improves performance.
                """
                resource_type = route.request.resource_type
                
                # Block list from analyzed scraper: images, fonts, stylesheets
                if resource_type in ["image", "font", "stylesheet"]:
                    route.abort()
                else:
                    route.continue_()
            
            # Apply blocking to all routes
            context.route("**/*", block_unnecessary_resources)
            
            # ===========================================
            # 7. Create and Configure Page
            # ===========================================
            
            self.page = context.new_page()
            
            # Set timeouts
            self.page.set_default_timeout(self.timeout)
            self.page.set_default_navigation_timeout(self.timeout * 2)
            
            # ===========================================
            # 8. Anti-Detection JavaScript Injection
            # ===========================================
            
            anti_detection_script = """
                // Remove webdriver flag - essential for all bot protection systems
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                    configurable: true
                });
                
                // Mock plugins array
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                    configurable: true
                });
                
                // Mock languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['pt-PT', 'pt', 'en-US', 'en'],
                    configurable: true
                });
                
                // Hide Playwright/automation objects
                window.playwright = undefined;
                window.__playwright = undefined;
                
                // Override permissions API
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => {
                    if (parameters.name === 'notifications') {
                        return Promise.resolve({ state: Notification.permission });
                    }
                    return originalQuery(parameters);
                };
                
                console.debug('Anti-detection measures active');
            """
            
            self.page.add_init_script(anti_detection_script)
            
            # ===========================================
            # 9. Human Behavior Simulation
            # ===========================================
            
            # Simulate initial mouse movements (like real user opening browser)
            for _ in range(random.randint(3, 6)):
                x = random.randint(50, viewport_width - 50)
                y = random.randint(50, viewport_height - 50)
                self.page.mouse.move(x, y, steps=random.randint(5, 12))
                time.sleep(random.uniform(0.05, 0.15))

            # ===========================================
            # 10. Save context for current session
            # ===========================================

            self.browser_context = context
            self.page = context.new_page()
            
            # ===========================================
            # 11. Log Initialization Details
            # ===========================================
            
            #self.logger.info(f"""
            #Browser initialized with anti-detection measures:
            #• User-Agent: {selected_user_agent[:50]}...
            #• Viewport: {viewport_width}x{viewport_height}
            #• Locale: pt-PT | Timezone: Europe/Lisbon
            #• Resource blocking: Active (images, fonts, CSS)
            #• Slow motion: {random.randint(80, 150)}ms
            #""")

            self.logger.info(f"""
            Browser initialized with anti-detection measures:
            • User-Agent: {selected_user_agent[:50]}...
            • Viewport: {viewport_width}x{viewport_height}
            • Locale: en-US | Timezone: America/New_York
            • Accept-Language: en-US,en;q=0.9
            • Geolocation: New York, USA
            • Resource blocking: Active (images, fonts, CSS)
            • Slow motion: {random.randint(80, 150)}ms
            """)

            
        except Exception as e:
            self.logger.error(f"Failed to initialize browser: {str(e)}")
            
            # Clean up any partially initialized resources
            if hasattr(self, 'browser') and self.browser:
                self.browser.close()
            if hasattr(self, 'playwright') and self.playwright:
                self.playwright.stop()
            
            # Reset state
            self.playwright = None
            self.browser = None
            self.page = None
            
            raise RuntimeError(f"Browser setup failed: {str(e)}")

    def get_base_url(self) -> str:
        """
        Return the base URL for Imovirtual portal.
        
        Returns:
            Base URL string without trailing slash.
        """
        return "https://www.imovirtual.com"

    def get_search_url(self, **search_params) -> str:
        # Delegate to strategy
        search_params.pop('municipality', None)
        search_params.pop('property_type', None)
        return self.strategy.build_search_url(
        base_url=self.BASE_URL,
        municipality=self._municipality,  
        **search_params
        )
    

    def _accept_cookies(self):
        """
        Accept cookies on Imovirtual if popup appears.
        SYNCHRONOUS version for sync_playwright.
        """
        try:
            # Try multiple possible cookie accept selectors
            accept_selectors = [
                'button:has-text("Aceitar")',
                'button:has-text("Aceitar todos")',
                'button:has-text("Accept")',
                'button[data-testid="uc-accept-all-button"]',
                '#onetrust-accept-btn-handler',
            ]
            
            for selector in accept_selectors:
                try:
                    # В синхронной версии используем wait_for_selector
                    accept_button = self.page.wait_for_selector(selector, timeout=3000)
                    if accept_button:
                        accept_button.click()
                        self.logger.info("Accepted cookies")
                        time.sleep(1)  # Wait for popup to disappear
                        return
                except:
                    continue
                    
        except Exception as e:
            self.logger.debug(f"No cookie popup or error accepting: {e}") 

    def _collect_listing_links(self, current_page) -> List[str]:
        """
        Finds ALL listing links on the current search results page.
        
        Process:
        1. Wait for listing containers to load
        2. Get the 'link' selector from the strategy
        3. Extract all href attributes
        4. Convert URLs to absolute
        5. Return the list
        """
        # 1. Get selectors from the strategy
        selectors = self.get_selectors()
        
        # 2. Wait until at least one listing is loaded
        self.page.wait_for_selector(selectors['item_container'])
        
        # 3. Find all links
        links = []
        items = self.page.locator(selectors['item_container']).all()
        
        for item in items:
            link_elem = item.locator(selectors['link'])
            if link_elem.count():
                href = link_elem.get_attribute('href')
                if href:
                    # Convert to absolute URL
                    if href.startswith('/'):
                        href = f"{self.get_base_url()}{href}"
                    links.append(href)

        if current_page == 1 and self.SKIP_FIRST_ADS > 0:
            links = links[self.SKIP_FIRST_ADS:]
            self.logger.info(
                f"Skipped the first {self.SKIP_FIRST_ADS} sponsored listings"
            )
        
        return links 

    def _parse_single_listing(self, url: str) -> Dict:
        """
        Parses a single listing by its URL.
        """

        current_search_url = self.page.url

        # Limit check
        if self.detail_visits >= self.DETAIL_BUDGET_BEFORE_COOLDOWN:
            cooldown = random.randint(*self.COOLDOWN_SECONDS_RANGE)
            self.logger.info(
                f"Reached the limit of {self.DETAIL_BUDGET_BEFORE_COOLDOWN} requests. "
                f"Pausing for {cooldown} seconds..."
            )
            time.sleep(cooldown)
            
            # Full context regeneration
            self._regenerate_browser_context()

            # Recovere search url after  regeneration
            self.page.goto(current_search_url)
            time.sleep(2)
            self._accept_cookies()

        new_tab = self.browser_context.new_page()
        
        try:
            new_tab.goto(url)
            time.sleep(2)  # Wait for full load
            
            # Strategy extracts data WITHOUT metadata
            data = self.strategy.extract_listing_data(new_tab)
            
            # Add ALL metadata here (once!)
            data.update({
                'listing_url': url,
                'scraped_at': datetime.now().isoformat(),
                'municipality': self.context.get('municipality')
            })

            # Increase counter by 1
            self.detail_visits += 1
            return data
            
        finally:
            new_tab.close()   

    def _go_to_next_page(self) -> bool:
            """
            Navigates to the next search results page.
            
            Returns:
                True  - if navigation was successful
                False - if this is the last page
            """
            # 1. Look for the "Next" button
            next_buttons = [
                'a[title="Go to next page"]',
                'a:has-text("Próxima")',
                'a:has-text("Next")',
            ]
            
            for selector in next_buttons:
                button = self.page.locator(selector).first
                if button.count():
                    button.click()
                    self.page.wait_for_load_state("networkidle")
                    return True
            
            return False

    def _build_page_url(self, page_num: int) -> str:
        """
        Simple page URL construction.
        Example: appends ?page=2 to the existing URL
        """
        base_url = self.get_search_url_with_context()
        
        if '?' in base_url:
            # If parameters already exist, append page=
            return f"{base_url}&page={page_num}"
        else:
            # If there are no parameters, append ?page=
            return f"{base_url}?page={page_num}"
    
    def get_selectors(self) -> Dict[str, str]:
        """
        Delegate to strategy - it knows its selectors best.
        
        Returns:
            Dictionary of CSS selectors for the current property type.
        """
        return self.strategy.get_selectors()

    # Main method:
    def _execute_scraping(self) -> List[Dict]:
        """
        MAIN method — the entire scraping sequence with pagination.
        """
        # 1. SET UP the driver (launch the browser)
        self.setup_webdriver()
        
        # 2. INITIALIZE data collection
        all_data = []
        
        # 3. PAGINATION LOOP - using URL-based pagination
        for page_num in range(1, self.max_pages + 1):
            # 3.1. Build URL for this page
            page_url = self._build_page_url(page_num)
            self.current_search_url = page_url  # Save the current search URL
            
            # 3.2. Navigate to the page
            self.page.goto(page_url)
            
            # 3.3. Accept cookies on the first page
            if page_num == 1:
                self._accept_cookies()
            
            # 3.4. Wait a bit for the page to load
            time.sleep(2)
            
            # 3.5. Collect listing links from CURRENT page
            listing_links = self._collect_listing_links(page_num)
            
            # If no links, stop
            if not listing_links:
                self.logger.warning(f"No listing links found on page {page_num}. Stopping.")
                break
            
            # 3.6. Process each listing link
            if self.max_listings_per_page > 0:
                links_to_process = listing_links[:self.max_listings_per_page]
            else:
                links_to_process = listing_links

            for link in links_to_process:
                # Open each listing in NEW tab and parse
                listing_data = self._parse_single_listing(link)
                all_data.append(listing_data)
                
                # Add delay between requests
                time.sleep(random.uniform(*self.request_delay_range))
        
        # 4. CLEAN UP resources
        self.cleanup()
        
        return all_data
    
