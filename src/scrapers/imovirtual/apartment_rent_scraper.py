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


from scrapers.real_estate_portal_scraper import RealEstatePortalScraper


class ImovirtualScraper(RealEstatePortalScraper):
    """
    Unified scraper for ALL property types on Imovirtual portal.
    
    Supports: apartment_rent, apartment_sale, house_rent, house_sale, etc.
    """

    # ==================== INITIALIZATION ====================
    def __init__(self, property_type: str, municipality: str, **kwargs):
        """
        Initialize Imovirtual scraper for apartment rentals.
        
        Args:
            property_type: Must be "apartment_rent" for this scraper
            municipality: Location to scrape (e.g., "lisbon", "porto")
            **kwargs: Additional configuration:
                - max_pages: Maximum pages to scrape (default: 5)
                - headless: Run browser in headless mode (default: False)
                - max_listings_per_page: For testing (default: 3)
                - request_delay: Delay between requests in seconds (default: 1-3)
        """
        # Configuration for all types of real estate
        PROPERTY_CONFIGS = {
            'apartment_rent': {
                'url_parts': ('arrendar', 'apartamento'),
                'description': 'Apartment for rent on Imovirtual',
                'specific_fields': ['furnished', 'has_elevator', 'condition', 'floor_number']
            },
        }

        # Property type validation
        if property_type not in self.PROPERTY_CONFIGS:
            supported = list(self.PROPERTY_CONFIGS.keys())
            raise ValueError(
                f"ImovirtualScraper supports: {supported}, got: {property_type}"
            )
        
        # Save this type configuration
        self.property_config = self.PROPERTY_CONFIGS[property_type]
        
        # Call parent constructor with fixed source_name
        super().__init__(
            source_name="imovirtual",  # Fixed for Imovirtual
            property_type=property_type,
            municipality=municipality,
            **kwargs
        )
        
        # Imovirtual specific configuration
        self.max_pages = kwargs.get('max_pages', 5)
        self.headless = kwargs.get('headless', False)
        self.max_listings_per_page = kwargs.get('max_listings_per_page', 3)  # For testing
        self.request_delay_range = kwargs.get('request_delay', (1, 3))
        
        # Initialize data storage
        self.scraped_data = []
        
        # Log initialization
        self.logger.info(f"Initialized ApartmentRentScraper for {municipality}")

    # ==================== UNIVERSAL METHODS ====================
    # ========== ABSTRACT METHOD IMPLEMENTATIONS ==========

    def get_selectors(self) -> Dict[str, str]:

        """
        Return CSS selectors specific to Imovirtual website structure.
        
        These selectors are based on the actual HTML structure of Imovirtual
        and should be updated if the website changes.
        
        Returns:
            Dictionary mapping field names to CSS selectors or XPaths.
        """
        return {
            'title': '[data-cy="adPageAdTitle"]',
            'description': '[data-testid="ad-description"]',
            'agent_name': '[data-cy="ad-contact-form-content"] p:first-of-type',
            'location_address': '[data-sentry-component="MapLink"] a',
            'scraped_price': 'strong[data-cy="adPageHeaderPrice"]',
            'energy_certificate': 'div[data-sentry-element="ItemGridContainer"]:has-text("Energy certificate") div:nth-child(2)',
            'area_sqm': 'div[data-sentry-element="ItemGridContainer"]:has-text("Área") div:nth-child(2)',
            'num_bedrooms': 'div[data-sentry-element="ItemGridContainer"]:has-text("Tipologia") div:nth-child(2)',
            'num_bathrooms': 'div[data-sentry-element="ItemGridContainer"]:has-text("Casas de banho") div:nth-child(2)',
            'floor_number': 'div[data-sentry-element="ItemGridContainer"]:has-text("Walk") div:nth-child(2)',
            'update_date': 'div[data-sentry-component="AdHistoryBase"]',
            'listing_id':'p[data-sentry-element="DetailsProperty"]:has-text("ID"),[data-sentry-source-file="AdMetadata.tsx"] p:has-text("ID"),.css-1fla28g:has-text("ID")',
        }

    def get_search_url(self, **search_params) -> str:
        """
        Build search URL for Imovirtual based on property type and municipality.
        
        Correct URL structure:
        https://www.imovirtual.com/pt/resultados/arrendar/apartamento/lisboa/lisboa?ownerTypeSingleSelect=ALL
        
        Args:
            **search_params: Additional search filters
        Returns:
            Complete search URL string with optional query parameters.
        """
        # Get property type and municipality
        property_type = search_params.get('property_type', self._property_type)
        municipality = search_params.get('municipality', self._municipality)
        
        # Map English municipality names to Portuguese
        municipality_mapping = {
            'lisbon': 'lisboa',
            'porto': 'porto',
            'coimbra': 'coimbra',
            'braga': 'braga',
            'faro': 'faro',
            'aveiro': 'aveiro',
            'setubal': 'setubal',
            'viana do castelo': 'viana-do-castelo',
            'vila real': 'vila-real',
            'viseu': 'viseu',
            'guarda': 'guarda',
            'castelo branco': 'castelo-branco',
            'santarem': 'santarem',
            'portalegre': 'portalegre',
            'evora': 'evora',
            'beja': 'beja',
            'funchal': 'funchal',
            'pontadelgada': 'ponta-delgada',
        }
        
        # Convert to Portuguese name if needed
        municipality_lower = municipality.lower()
        if municipality_lower in municipality_mapping:
            municipality_clean = municipality_mapping[municipality_lower]
        else:
            municipality_clean = municipality_lower.replace(' ', '-')
        
        # Map property_type to URL parts - CORRECT ORDER: transaction/property
        property_type_mapping = {
            'apartment_rent': ('arrendar', 'apartamento'),
            'apartment_sale': ('comprar', 'apartamento'),
            'house_rent': ('arrendar', 'moradia'),
            'house_sale': ('comprar', 'moradia'),
        }
        
        if property_type not in property_type_mapping:
            raise ValueError(f"Unsupported property_type: {property_type}")
        
        transaction_type_url, property_type_url = property_type_mapping[property_type]
        
        # Build base URL path - NOTE: double municipality for district/city structure
        base_url = self.get_base_url()
        url = f"{base_url}/pt/resultados/{transaction_type_url}/{property_type_url}/{municipality_clean}/{municipality_clean}/"
        
        # Add query parameters if provided (keep existing logic but simpler)
        query_params = {}
        
        for key, value in search_params.items():
            if key not in ['property_type', 'municipality'] and value is not None:
                # Add parameters as-is (e.g., ownerTypeSingleSelect=ALL)
                query_params[key] = value
        
        if query_params:
            import urllib.parse
            query_string = urllib.parse.urlencode(query_params)
            url = f"{url}?{query_string}"
        
        return url

    def get_base_url(self) -> str:
        """
        Return the base URL for Imovirtual portal.
        
        Returns:
            Base URL string without trailing slash.
        """
        return "https://www.imovirtual.com"

    def get_scraping_instructions(self) -> Dict[str, Any]:
        """
        Return manual scraping instructions for Imovirtual
        
        Overrides parent method to provide Imovirtual-specific instructions.
        
        Returns:
            Dictionary with step-by-step instructions
        """
        # TODO: Implement or use parent implementation
        # Can use parent's method and add Imovirtual-specific steps
        pass

    async def _scrape_with_playwright(self) -> List[Dict]:
        """
        Main async scraping method that extracts real data from Imovirtual.
        
        This method:
        1. Opens browser and navigates to search page
        2. Accepts cookies
        3. Finds listing links
        4. Extracts data from each listing
        5. Returns list of real listing data
        
        Returns:
            List of dictionaries, each containing 18 fields from bronze schema
        """
        from datetime import datetime
        
        self.logger.info("Starting real Imovirtual scraping...")
        
        async with async_playwright() as pw:
            # 1. Launch browser
            browser = await pw.chromium.launch(
                headless=self.headless,
                args=['--disable-blink-features=AutomationControlled']
            )
            
            # Create browser context with realistic settings
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='pt-PT',
                timezone_id='Europe/Lisbon'
            )
            
            # Create main page
            page = await context.new_page()
            
            try:
                # 2. Go to search URL
                search_url = self.get_search_url()
                self.logger.info(f"Navigating to search URL: {search_url}")
                await page.goto(search_url, wait_until='domcontentloaded')
                
                # 3. Accept cookies if popup appears
                await self._accept_cookies_imovirtual(page)
                
                # 4. Wait for listings to load
                await page.wait_for_selector('[data-cy="listing-item-link"]', timeout=10000)
                
                # 5. Find listing links
                self.logger.info("Finding listing links...")
                listing_urls = await self._find_listing_links_imovirtual(page)
                
                if not listing_urls:
                    self.logger.warning("No listing links found!")
                    return []
                
                self.logger.info(f"Found {len(listing_urls)} listing links")
                
                # Limit for testing if specified
                if self.max_listings_per_page:
                    listing_urls = listing_urls[:self.max_listings_per_page]
                    self.logger.info(f"Limiting to {self.max_listings_per_page} listings for testing")
                
                # 6. Process each listing
                all_listings_data = []
                
                for i, listing_url in enumerate(listing_urls, 1):
                    try:
                        self.logger.info(f"Processing listing {i}/{len(listing_urls)}: {listing_url}")
                        
                        # Create new page for listing
                        listing_page = await context.new_page()
                        
                        # Navigate to listing with timeout
                        await listing_page.goto(listing_url, wait_until='domcontentloaded', timeout=15000)
                        
                        # Wait for main content
                        await listing_page.wait_for_selector('[data-cy="adPageAdTitle"]', timeout=10000)
                        
                        # Extract data using our main method
                        listing_data = await self._extract_listing_data_imovirtual(listing_page)
                        
                        # Add to results
                        all_listings_data.append(listing_data)
                        
                        # Close listing page
                        await listing_page.close()
                        
                        # Log progress
                        self.logger.info(f"Successfully extracted data for listing {i}: {listing_data.get('listing_id', 'unknown')}")
                        
                        # Add random delay between requests (respectful scraping)
                        if i < len(listing_urls):  # No delay after last one
                            delay = random.uniform(*self.request_delay_range)
                            self.logger.debug(f"Waiting {delay:.2f} seconds before next request")
                            await asyncio.sleep(delay)
                        
                    except Exception as e:
                        self.logger.error(f"Failed to process listing {listing_url}: {str(e)}")
                        continue  # Skip failed listing and continue with next
                
                # 7. Log final results
                self.logger.info(f"Scraping completed. Successfully extracted {len(all_listings_data)} listings")
                
                return all_listings_data
                
            except Exception as e:
                self.logger.error(f"Scraping failed with error: {str(e)}")
                raise
            finally:
                # Always close browser
                await browser.close()
                self.logger.info("Browser closed")

    # ==================== IMOVITRUAL SPECIFIC METHODS ====================
    #These methods contain logic unique to Imovirtual's website structure

    async def _extract_text_by_selector(self, page, selector_key: str) -> Optional[str]:
        """
        Extract text content from an element using CSS selector from get_selectors() dictionary.
        
        This method centralizes text extraction logic, handles errors gracefully,
        and ensures consistent behavior across all field extraction methods.
        
        Args:
            page: Playwright page object for the current listing page
            selector_key: Key from get_selectors() dictionary (e.g., 'title', 'description')
            
        Returns:
            Extracted text content as string (stripped of whitespace), 
            or None if element not found or extraction fails.
            
        Example:
            title = await self._extract_text_by_selector(page, 'title')
            description = await self._extract_text_by_selector(page, 'description')
        """
        # Get the CSS selector from get_selectors() dictionary
        selectors = self.get_selectors()
        if selector_key not in selectors:
            self.logger.warning(f"Selector key '{selector_key}' not found in get_selectors()")
            return None
        
        css_selector = selectors[selector_key]
        
        try:
            # Find element using CSS selector
            element = await page.query_selector(css_selector)
            
            if element:
                # Extract text content from element
                text_content = await element.text_content()
                
                # Return stripped text if not empty
                if text_content:
                    return text_content.strip()
        
        except Exception as e:
            # Log debugging information without breaking the entire scraping process
            self.logger.debug(
                f"Failed to extract text for '{selector_key}' "
                f"using selector '{css_selector}': {str(e)}"
            )
        
        # Return None if element not found, empty, or extraction failed
        return None
 
    async def _find_listing_links_imovirtual(self, page) -> List[str]:
        """
        Find listing links on Imovirtual search results page.
        
        Args:
            page: Playwright page object for search results page
            
        Returns:
            List of URLs to individual listings (absolute URLs)
        """
        try:
            # Wait for listings to load
            await page.wait_for_selector('[data-cy="listing-item-link"]', timeout=10000)
            
            # Find all listing links using data-cy attribute
            links = await page.eval_on_selector_all(
                '[data-cy="listing-item-link"]',
                'elements => elements.map(el => el.href)'
            )
            
            # Alternative if the above doesn't work - use Playwright's locator API
            if not links:
                link_elements = await page.query_selector_all('[data-cy="listing-item-link"]')
                links = []
                for element in link_elements:
                    href = await element.get_attribute('href')
                    if href:
                        # Convert relative URLs to absolute
                        if href.startswith('/'):
                            base_url = self.get_base_url()
                            href = f"{base_url}{href}"
                        links.append(href)
            
            # Remove duplicates and None values
            unique_links = []
            seen = set()
            
            for link in links:
                if link and link not in seen:
                    seen.add(link)
                    unique_links.append(link)
            
            self.logger.info(f"Found {len(unique_links)} listing links on page")
            return unique_links
            
        except Exception as e:
            self.logger.error(f"Error finding listing links: {str(e)}")
            return []

    async def _accept_cookies_imovirtual(self, page):
        """
        Accept cookies on Imovirtual if popup appears.
        
        Args:
            page: Playwright page object
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
                    accept_button = await page.wait_for_selector(selector, timeout=3000)
                    if accept_button:
                        await accept_button.click()
                        self.logger.info("Accepted cookies")
                        await asyncio.sleep(1)  # Wait for popup to disappear
                        return
                except:
                    continue
                    
        except Exception as e:
            self.logger.debug(f"No cookie popup or error accepting: {e}")

    async def _handle_pagination_imovirtual(self, page, current_page: int) -> Optional[str]:
        """
        Handle pagination on Imovirtual
        
        Args:
            page: Playwright page object
            current_page: Current page number
            
        Returns:
            URL of next page or None if no more pages
        """
        # TODO: Implement Imovirtual-specific pagination
        # Look for "Go to next page" button
        # Or construct URL with ?page= parameter
        pass
    
    # ========== CONFIGURABLE METHODS ==========
    # ========== Use configuration and adapt to a specific property type ========== 

    #  APARTMENT RENT 
    async def _apartment_rent_extract_furnished(self, page) -> str:
        """Extract furnished status without clicking accordion elements"""
        # 1. Look inside characteristics_grid (already present on the page)
        containers = await page.query_selector_all('div[data-sentry-element="ItemGridContainer"]')
        
        for container in containers:
            text = await container.text_content()
            # Look for the container with Equipment
            if 'Equipment:' in text or 'Equipamento:' in text:
                # Check for furniture / mobilado inside
                if 'furniture' in text.lower() or 'mobilado' in text.lower():
                    return 'yes'
                else:
                    return 'no'  # Equipment section exists, but no furniture mentioned
        
        # 2. Look in features (if there is a separate block)
        features = await page.query_selector_all('[data-testid="ad-features"] li')
        for feature in features:
            text = await feature.text_content()
            if 'furniture' in text.lower() or 'mobilado' in text.lower():
                return 'yes'
        
        # 3. Look in the description
        description = await self._extract_text_by_selector(page, 'description')
        if description and ('furniture' in description.lower() or 'mobilado' in description.lower()):
            return 'yes'
        
        return 'no'  # Default

    async def _apartment_rent_extract_has_elevator(self, page) -> str:
        """
        Extract information about an elevator (has_elevator).
        Searches in characteristics, features, and description.
        Returns the raw string value as-is: 'yes', 'no', 'aye', 'sim', 'não', etc.
        """
        
        # 1. First, search in characteristics containers (even if the accordion is closed)
        containers = await page.query_selector_all('div[data-sentry-element="ItemGridContainer"]')
        
        for container in containers:
            # Get the text of the entire container
            text = await container.text_content()
            
            # Look for a container with "Lift" or "Elevador"
            if 'Lift:' in text or 'Elevador:' in text:
                # Found the correct container; now get the value (second div)
                value_element = await container.query_selector('div:nth-child(2)')
                if value_element:
                    value_text = await value_element.text_content()
                    # Clean and return as-is
                    return value_text.strip()
        
        # 2. Search in features (if there is a separate block)
        features = await page.query_selector_all('[data-testid="ad-features"] li')
        for feature in features:
            text = await feature.text_content()
            text_lower = text.lower()
            
            # Look for elevator mentions in features
            if 'elevador' in text_lower or 'lift' in text_lower:
                # Check for negation
                if 'no' in text_lower or 'sem' in text_lower or 'without' in text_lower:
                    return 'no'
                else:
                    return 'yes'
        
        # 3. Search in the description
        description = await self._extract_text_by_selector(page, 'description')
        if description:
            desc_lower = description.lower()
            
            # Look for elevator mentions in the description
            if 'elevador' in desc_lower or 'lift' in desc_lower:
                # Check context
                if any(negation in desc_lower for negation in ['sem elevador', 'no lift', 'without lift', 'não tem elevador']):
                    return 'no'
                else:
                    return 'yes'
        
        # 4. Default — no information found
        return ''  # or 'no' if we want to be more conservative
    
    async def _apartment_rent_extract_features_list(self, page) -> List[str]:
        """Вспомогательная: извлекает список features"""
        elements = await page.query_selector_all('[data-testid="ad-features"] li')
        return [await el.text_content() for el in elements if await el.text_content()]
    
    def _apartment_rent_extract_condition(self, description: str) -> str:
        """
        Simple function to extract the condition from a description.
        Returns: 'novo', 'bom', 'excelente', 'renovar', 'usado', or None
        """
        if not description:
            return None
        
        desc_lower = description.lower()
        
        # Order matters: from more specific phrases to more general ones
        patterns = [
            # Portuguese
            (r'(?:excelente|ótimo)\s+(?:estado|condições)', 'excelente'),
            (r'bom\s+(?:estado|condições)', 'bom'),
            (r'em\s+bom\s+estado', 'bom'),
            (r'(?:precisa|necessita)\s+de?\s+renovação', 'renovar'),
            (r'(?:a\s+)?renovar', 'renovar'),
            (r'para\s+renovar', 'renovar'),
            (r'(?:novo|nova)(?:\s+construção)?', 'novo'),
            (r'usado|usada|já usado', 'usado'),
            
            # English (just in case)
            (r'excellent\s+condition', 'excelente'),
            (r'good\s+condition', 'bom'),
            (r'needs?\s+(?:renovation|repair|work)', 'renovar'),
            (r'new(?:\s+construction)?', 'novo'),
            (r'used', 'usado'),
        ]
        
        for pattern, condition in patterns:
            if re.search(pattern, desc_lower, re.IGNORECASE):
                return condition
        
        # If no explicit phrases were found, look for individual words
        if any(word in desc_lower for word in ['excelente', 'excellent']):
            return 'excelente'
        if any(word in desc_lower for word in ['bom', 'good']):
            return 'bom'
        if any(word in desc_lower for word in ['novo', 'new']):
            return 'novo'
        if any(word in desc_lower for word in ['renovar', 'renovation']):
            return 'renovar'
        if any(word in desc_lower for word in ['usado', 'used']):
            return 'usado'
        
        return None

    # ==================== HELPER METHODS ====================
    def _generate_listing_id_fallback(self, url: str) -> str:
        """
        Generate a fallback listing ID from URL when not found on page.
        
        Args:
            url: Listing URL
            
        Returns:
            Generated unique ID in format "imovirtual_XXXX"
        """
        import re
        import hashlib
        
        # Try to extract numeric ID from URL (pattern: /ID1hJVk)
        match = re.search(r'/ID([A-Za-z0-9]+)', url)
        if match:
            return f"imovirtual_{match.group(1)}"
        
        # If no ID found, create hash from URL
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        return f"imovirtual_{url_hash}"
   
    async def _extract_listing_data_imovirtual(self, page) -> Dict[str, Any]:
        """
        Extract ALL 18 fields from a single Imovirtual listing page.
        
        This method orchestrates the extraction of every field in the bronze schema:
        1. Extract 12 fields using CSS selectors from get_selectors()
        2. Extract 3 fields using specialized methods (furnished, has_elevator, condition)
        3. Add 3 fields from context (listing_url, scraped_at, municipality)
        
        Args:
            page: Playwright page object for a single listing page
            
        Returns:
            Dictionary with exactly these 18 keys (some may be None/empty):
            - listing_id
            - listing_url
            - title
            - description
            - agent_name
            - location_address
            - municipality
            - condition
            - furnished
            - energy_certificate
            - scraped_price
            - area_sqm
            - num_bedrooms
            - num_bathrooms
            - floor_number
            - has_elevator
            - scraped_at
            - update_date
        """
        from datetime import datetime
        
        data = {}
        
        # 1. Extract fields using CSS selectors (12 fields)
        selector_fields = [
            'title', 'description', 'agent_name', 'location_address',
            'scraped_price', 'energy_certificate', 'area_sqm', 'num_bedrooms',
            'num_bathrooms', 'floor_number', 'update_date', 'listing_id'
        ]
        
        for field in selector_fields:
            value = await self._extract_text_by_selector(page, field)
            data[field] = value  # Could be None
        
        # 2. Extract fields using specialized methods (3 fields)
        data['furnished'] = await self._apartment_rent_extract_furnished(page)
        data['has_elevator'] = await self._apartment_rent_extract_has_elevator(page)
        
        # Extract condition from description
        description = data.get('description')
        if description:
            data['condition'] = self._apartment_rent_extract_condition(description)
        else:
            data['condition'] = None
        
        # 3. Add contextual fields (3 fields)
        data['listing_url'] = page.url
        data['scraped_at'] = datetime.now().isoformat()
        data['municipality'] = self._municipality
        
        # 4. Handle special cases
        # Generate listing_id if not found on page
        if not data.get('listing_id'):
            data['listing_id'] = self._generate_listing_id_fallback(page.url)
        
        # Log successful extraction
        self.logger.debug(f"Extracted data for listing: {data.get('listing_id')}")
        
        return data

    
    def _execute_scraping(self) -> List[Dict]:
        """
        Main synchronous scraping method.
        
        This method:
        1. Runs the async Playwright scraping logic
        2. Handles errors and retries
        3. Returns collected data for saving to bronze layer
        
        Returns:
            List of dictionaries containing scraped listing data
        """
        try:
            self.logger.info("Starting Imovirtual scraping...")
            
            # Log current configuration
            self.logger.info(f"Configuration: "
                            f"max_pages={self.max_pages}, "
                            f"headless={self.headless}, "
                            f"municipality={self._municipality}")
            
            # Run async scraping with Playwright
            # asyncio.run() is used to run async code from synchronous context
            self.scraped_data = asyncio.run(self._scrape_with_playwright())
            
            # Log completion
            self.logger.info(f"Scraping completed. Collected {len(self.scraped_data)} listings")
            
            # Return data for automatic saving by BaseScraper
            return self.scraped_data
            
        except Exception as e:
            self.logger.error(f"Scraping failed: {str(e)}")
            # Re-raise the exception so BaseScraper can handle it properly
            raise
    

    def _parse_price_imovirtual(self, price_text: str) -> Dict[str, Any]:
        """
        Parse price text from Imovirtual listing
        
        Args:
            price_text: Raw price text (e.g., "1.500 €/mês")
            
        Returns:
            Dictionary with parsed price components
        """
        # TODO: Implement price parsing for Imovirtual format
        pass
    
    def _parse_area_imovirtual(self, area_text: str) -> Dict[str, Any]:
        """
        Parse area text from Imovirtual listing
        
        Args:
            area_text: Raw area text (e.g., "120 m²")
            
        Returns:
            Dictionary with parsed area components
        """
        # TODO: Implement area parsing for Imovirtual format
        pass
    
    def _extract_features_imovirtual(self, page) -> List[str]:
        """
        Extract features list from Imovirtual listing
        
        Args:
            page: Playwright page object
            
        Returns:
            List of feature strings
        """
        # TODO: Implement feature extraction for Imovirtual
        pass
    
    # ========== HELPER METHODS ==========
    
    def _generate_listing_id(self, url: str) -> str:
        """
        Generate unique listing ID from URL
        
        Args:
            url: Listing URL
            
        Returns:
            Unique ID string
        """
        # TODO: Implement ID generation
        # Extract ID from URL or generate hash
        pass
    
    def _should_skip_listing(self, data: Dict[str, Any]) -> bool:
        """
        Determine if a listing should be skipped
        
        Args:
            data: Extracted listing data
            
        Returns:
            True if listing should be skipped
        """
        # TODO: Implement skip logic
        # Check for missing required fields
        # Check for duplicates
        pass
    
    # ========== ERROR HANDLING ==========
    
    async def _handle_scraping_error(self, error: Exception, context: str):
        """
        Handle scraping errors with appropriate logging
        
        Args:
            error: Exception that occurred
            context: Context description (e.g., "extracting price")
        """
        # TODO: Implement error handling
        # Log error with context
        # Decide if should retry or skip
        pass
    
    def _setup_retry_logic(self):
        """
        Setup retry logic for failed requests
        """
        # TODO: Implement retry logic
        pass
    
    # ========== CONFIGURATION METHODS ==========
    
    def get_imovirtual_config(self) -> Dict[str, Any]:
        """
        Get Imovirtual-specific configuration
        
        Returns:
            Dictionary with configuration
        """
        # TODO: Return Imovirtual-specific config
        # Timeouts, selectors, URL patterns, etc.
        pass