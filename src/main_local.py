import sys
from pathlib import Path

# КРИТИЧЕСКИ ВАЖНО: добавляем путь к проекту
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT / "src"))

from scrapers.imovirtual.imovirtual_scraper import ImovirtualScraper

def main():
    """Main entry point for Imovirtual scraper."""
    
    # Only 2 required parameters 
    scraper = ImovirtualScraper(
        property_type="apartment_rent",
        municipality="lisbon"
    )

    #TODO setup batch scraping later 
    
    # EVERYTHING else is inside run()
    data = scraper.run()
    
    # Minimal output
    if data:
        print(f"Successfully collected {len(data)} listings")
        return 0
    else:
        print("Failed to collect data")
        return 1

if __name__ == "__main__":
    sys.exit(main())