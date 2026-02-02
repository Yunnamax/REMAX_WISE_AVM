from scrapers.web_scraper_base import WebScraperBase
from abc import abstractmethod
from typing import Dict, List, Any
from pathlib import Path
from datetime import datetime

class RealEstatePortalScraper(WebScraperBase):
    def __init__(self, source_name: str, property_type: str, municipality: str, **kwargs):
        context = {
            'property_type': property_type,
            'municipality': municipality,
            **kwargs
        }
        super().__init__(source_name, **context)
        
        self._property_type = property_type
        self._municipality = municipality
        #self.source_type = "real_estate_portal"
    def _generate_output_path(self) -> Path:
        """
        Generates path for real estate portal scrapers.
        Format: data/bronze/{source_name}/{property_type}/{municipality}/date=.../raw_data.json
        
        Removes all other context parameters from path - they go to metadata only.
        """
        date = datetime.now().strftime('%Y-%m-%d')
        
        # 1. Base structure for ALL real estate portals
        path_parts = [
            self.project_root,
            "data",
            "bronze",
            self.source_name,          # portal_name (imovirtual, idealista)
            self._property_type,       # apartment_rent, apartment_sale
            self._municipality,        # lisbon, porto
            f"date={date}",
            "raw_data.json"
        ]
        
        return Path(*path_parts)