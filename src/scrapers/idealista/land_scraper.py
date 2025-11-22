import sys
import os
import yaml
from pathlib import Path
from typing import Dict
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, project_root)
from src.scrapers.web_scraper_base import BaseScraper
from typing import Dict, List, Any
import pandas as pd

class IdealistaLandScraper(BaseScraper):
    """
    Scraper for collecting land plot data from the Idealista portal.
Inherits all infrastructure from BaseScraper.
    """
    def __init__(self, municipality: str):
        super().__init__(
            source_name="idealista",      
            property_type="land",          
            municipality=municipality    
        )

    def get_base_url(self) -> str:
        return "https://www.idealista.pt/en/"
    
    def get_search_url(self) -> str:
        base_url = self.get_base_url()
        #normalized_municipality = self._normalize_municipality_name(municipality)
        return f"{base_url}/comprar-terrenos/{self.municipality}/"
    
    def get_scraping_instructions(self) -> str:
        return {
            "1": "Open the website",
            "2": "Collect data manually",
            "3": "Save files",
            "4": "Return and press Enter"
        }
    
    def get_selectors(self) -> Dict[str, str]:
        """
        oads CSS selectors from a YAML configuration file.
        """
        # determine selectors configuration file path
        config_path = (
            self.project_root / 
            "config" / 
            "selectors" / 
            "idealista" / 
            "land.yaml"
        )
        
        # Check if file exists
        if not config_path.exists():
            raise FileNotFoundError(
                f"Selector configuration file not found: {config_path}"
            )
        
        # loading YAML file
        with open(config_path, 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
        
        # Return only selectors section
        return config.get('selectors', {})
    
    def _execute_scraping(self) -> List[Dict]:
        """
        Основная логика сбора данных.
        Для MVP - просто используем ручной сбор из базового класса.
        """
        return self._handle_manual_scraping()
    

 