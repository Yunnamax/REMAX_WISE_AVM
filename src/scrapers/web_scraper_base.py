from scrapers.base_scraper import BaseScraper
from abc import abstractmethod
from typing import Dict, List, Any

class WebScraperBase(BaseScraper):
    """
    Base class for ALL web scrapers.
    Defines the common interface and logic for working with websites.
        NOTE ON LIFECYCLE:

    This class does not orchestrate scraping flow.
    The execution order is defined in BaseScraper.run().

    WebScraperBase provides:
    - web-specific contracts
    - infrastructure hooks
    - default policies

    Subclasses are expected to implement:
    - get_base_url()
    - get_search_url()
    - get_selectors()
    - _execute_scraping()
    """
    
    def __init__(self, source_name: str, **context_kwargs):
        super().__init__(source_name, **context_kwargs)
        self.driver = None  # Selenium/Playwright driver
        self.session = None  # requests session
        self.browser_context = None
        self._init_web_infrastructure()  # web infrastructure initialization

    # Determine source type
    @property
    def source_type(self) -> str: return "web"   

    def _init_web_infrastructure(self):
        """Web infrastructure initialization"""
        pass
    
    @abstractmethod
    def get_selectors(self) -> Dict[str, str]:
        """
        Should return a dictionary of CSS selectors for this site.
        Keys: field names, Values: CSS selectors.
        """
        pass
    
    @abstractmethod
    def get_base_url(self) -> str:
        """Should return the website's base URL."""
        pass
    
    @abstractmethod
    def get_search_url(self, **search_params) -> str:
        """
        Should return the URL for searching.
        Can accept any search parameters.
        """
        pass
    
    def get_search_url_with_context(self) -> str:
        """
        Returns search URL using current context.
        Default implementation - can be overridden.
        """
        return self.get_search_url(**self.context)
    
    def get_scraping_instructions(self) -> Dict[str, Any]:
        """
        Basic instructions for manual web scraping.
        Now uses context instead of hardcoded parameters.
        """
        example_path = self._generate_output_path()
        
        instructions = {
            "1": f"Open website: {self.get_base_url()}",
            "2": f"Search URL: {self.get_search_url_with_context()}",
            "3": "Collect data according to Bronze layer scheme",
            "4": f"Data will be saved to: {example_path.parent}",
            "5": "After collecting data, press Enter to continue"
        }
        
        if self.context:
            instructions["context"] = f"Current context: {self.context}"
        
        return instructions
    
    def validate_selectors(self) -> bool:
        """
        Basic selector validation.
        Now checks selectors from get_selectors().
        """
        selectors = self.get_selectors()
        
        # Bacik checks
        if not selectors:
            self.logger.warning("No selectors defined")
            return False
        
        if not isinstance(selectors, dict):
            self.logger.warning(f"Selectors must be dict, got {type(selectors)}")
            return False
        
        # All selecttors are strings check
        invalid_selectors = []
        for field, selector in selectors.items():
            if not isinstance(selector, str):
                invalid_selectors.append(field)
        
        if invalid_selectors:
            self.logger.warning(f"Invalid selectors (not strings): {invalid_selectors}")
            return False
        
        return True
    
    def get_pagination_strategy(self) -> str:
        """
        Pagination strategy. By default — manual.
        Can be overridden for automatic scrapers.
        """
        return "manual"  # или "infinite_scroll", "next_button", "page_numbers"
    
    def get_required_fields(self) -> List[str]:
        """
        Required fields for this type of scraper.
        Default is empty - should be overridden in subclasses.
        """
        return []
    
    def get_webdriver_config(self) -> Dict[str, Any]:
        """
        WebDriver configuration for automatic scraping.
        Default configuration - can be overridden.
        """
        return {
            'headless': True,
            'timeout': 30,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'window_size': (1920, 1080),
            'implicit_wait': 10
        }
    
    def get_request_config(self) -> Dict[str, Any]:
        """
        Request configuration for HTTP-based scrapers.
        """
        return {
            'timeout': 30,
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
            },
            'verify_ssl': True
        }
    
    # New web scraping methods
    
    def setup_webdriver(self):
        """Setup Selenium/Playwright webdriver"""
        
        # if web driver is being used
        pass
    
    def setup_requests_session(self):
        """Setup requests session"""
        # if requests is used
        pass
    
    def cleanup(self):
        """Cleanup resources (webdriver, sessions, etc.)"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
        
        if self.session:
            try:
                self.session.close()
            except:
                pass
    
    def _execute_scraping(self) -> List[Dict]:
        """
        Default implementation of abstract method.
        Should be overridden in child classes.
        """
        raise NotImplementedError("_execute_scraping must be implemented in child class")
    
    def __del__(self):
        """Cleanup on deletion"""
        self.cleanup()