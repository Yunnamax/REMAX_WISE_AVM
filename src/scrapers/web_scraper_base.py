from scrapers.base_scraper import BaseScraper
from abc import abstractmethod
from typing import Dict, List

class WebScraperBase(BaseScraper):
    """
    Base class for ALL web scrapers.
    Defines the common interface and logic for working with websites.
    """
    
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
    def get_search_url(self, municipality: str) -> str:
        """
        Should return the URL for searching in the specified municipality.
        May include search parameters, filters, etc.
        """
        pass

    def get_scraping_instructions(self) -> Dict[str, any]:
        """
        Basic instructions for manual web scraping.
        Can be overridden in child classes for clarification.
        """
        example_path = self._generate_output_path()
        return {
            "1": f"Open website: {self.get_base_url()}",
            "2": f"Follow the search link: {self.get_search_url(self.municipality)}",
            "3": "Collect data according to Bronze layer scheme",
            "4": f"Go back and press Enter"
        }
    
    def validate_selectors(self) -> bool:
        """
        Basic selector validation.
        Checks that all required selectors are present.
        """
        selectors = self.get_selectors()
        required = ['price', 'area']  # Minimal set
        missing = [field for field in required if field not in selectors]
        
        if missing:
            self.logger.warning(f"Missing selectors: {missing}")
            return False
        return True

    """
    implement later:
    """
    def get_pagination_strategy(self) -> str:
        """
        agination strategy. By default — manual.
        Can be overridden for automatic scrapers.
        """
        return "manual"  # или "infinite_scroll", "next_button", "page_numbers"
    
    def get_required_fields(self) -> List[str]:
        """
        Required fields for this type of scraper.
        Helps with data validation.
        """
        return ['listing_id', 'price', 'area', 'location']
    
    def get_browser_config(self) -> Dict[str, any]:
        """
        Browser configuration for automatic scraping.
        May be used in the future with Selenium/Playwright.
        """
        return {
            'headless': True,
            'timeout': 30,
            'user_agent': 'Mozilla/5.0...'
        }