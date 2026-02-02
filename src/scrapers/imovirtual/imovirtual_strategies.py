from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import re

class ImovirtualStrategy(ABC):

    @abstractmethod
    def extract_listing_data(self, page) -> Dict[str, Any]:
        """
        Extracts ALL data for a single listing of THIS property type.
        
        Must return a dictionary with fields specific to this property type.
        Implementation will use:
        - get_selectors() for CSS-based extraction
        - Custom functions for complex data extraction
        
        Returns:
            Dictionary with ALL fields for this property type.
        """
        pass

    @abstractmethod
    def get_selectors(self): pass

    @abstractmethod
    def _extract_non_selector_data(self, page) -> Dict[str, Any]:
        """
        Extracts data that CANNOT be obtained via CSS selectors.
        
        Examples:
        - Property condition (new building, renovated, needs renovation)
        - Approximate area inferred from the description
        - Features (parking, elevator, air conditioning)
        - Year of construction (if not explicitly stated)
        """
        pass
    
    @abstractmethod
    def build_search_url(self): pass

# Strategy:
class ApartmentRentStrategy:

    SCHEMA_FIELDS = [
        'listing_id',
        'listing_url',
        'title',
        'description', 
        'agent_name',
        'location_address',
        'municipality',
        'condition',
        'furnished',
        'energy_certificate',
        'scraped_price',
        'area_sqm',
        'num_bedrooms',
        'num_bathrooms',
        'floor_number',
        'has_elevator',
        'scraped_at',
        'update_date'
    ]

    # Fields from get_selectors()
    SELECTOR_FIELDS = [
        'item_container',    # service
        'link',              # service  
        'title',
        'description',
        'agent_name',
        'location_address',
        'scraped_price',
        'area_sqm',
        'num_bedrooms',
        'num_bathrooms',
        'floor_number',      # WILL BE EXTRACTED SEPARATELY
        'update_date',       # WILL BE EXTRACTED SEPARATELY
        'listing_id'
    ]
    def build_search_url(self, base_url: str, municipality: str, **kwargs) -> str:
        """
        Build URL for apartment rentals.
        
        Example: https://www.imovirtual.com/pt/resultados/arrendar/apartamento/lisboa/
        
        Args:
            base_url: Base URL of the site
            municipality: City/district name
            **kwargs: Additional filters (price range, rooms, etc.)
        
        Returns:
            Complete search URL
        """
        # Simple Portuguese mapping for now
        municipality_map = {
            'lisbon': 'lisboa',
            'porto': 'porto',
            'coimbra': 'coimbra',
            # Add more as needed
        }
        
        # Get Portuguese name or use original (lowercase, replace spaces)
        pt_municipality = municipality_map.get(municipality.lower(), municipality.lower())
        pt_municipality = pt_municipality.replace(' ', '-')
        
        # Build base URL
        url = f"{base_url}/pt/resultados/arrendar/apartamento/{pt_municipality}/"
        
        # Add optional filters
        filters = []
        
        # Price filter example
        if kwargs.get('max_price'):
            filters.append(f"priceMax={kwargs['max_price']}")
        
        # Rooms filter example  
        if kwargs.get('min_rooms'):
            filters.append(f"roomsNumber={kwargs['min_rooms']}")
        
        if filters:
            url += "?" + "&".join(filters)
        
        return url

    def extract_listing_data(self, page) -> Dict[str, Any]:
        """
        Extracts ALL 15 fields for apartment rental listings.
        
        Combines:
        1. 12 fields extracted directly via CSS selectors from get_selectors()
        2. 3 fields extracted using specialized methods:
        - condition: via _extract_condition()
        - furnished: via _extract_furnished()
        - has_elevator: via _extract_has_elevator()
        
        Returns:
            Dictionary with exactly these 15 fields (some may be None/empty):
            - listing_id
            - title
            - description
            - agent_name
            - location_address
            - condition
            - furnished
            - energy_certificate
            - scraped_price
            - area_sqm
            - num_bedrooms
            - num_bathrooms
            - floor_number
            - has_elevator
            - update_date
        """
        data = {}
        
        # 1. Extract 12 fields using CSS selectors from get_selectors()
        selectors = self.get_selectors()
        
        # Extract simple fields via CSS selectors
        for field_name, selector in selectors.items():
            # Skip container and link selectors (only for listing pages)
            if field_name in ['item_container', 'listing_link', 'link', 'next_page_button', 'energy_certificate' , 'floor_number']:
                continue
                
            try:
                element = page.locator(selector).first
                if element.count():
                    text = element.text_content()
                    if text and text.strip():
                        data[field_name] = text.strip()
                    else:
                        data[field_name] = None
                else:
                    data[field_name] = None
            except Exception:
                data[field_name] = None

        non_selector_data = self.extract_non_selector_data(page, data)
        data.update(non_selector_data)

        # TODO: 
        # temporary workaround, 
        # will replace later with proper implementation

        # 1. Define which fields MUST exist (from the schema)
        required_fields = [
            'listing_id', 'listing_url', 'title', 'description',
            'agent_name', 'location_address', 'municipality',
            'condition', 'furnished', 'energy_certificate',
            'scraped_price', 'area_sqm', 'num_bedrooms',
            'num_bathrooms', 'floor_number', 'has_elevator',
            'scraped_at', 'update_date'
        ]

        # 2. Create the final dictionary with ALL fields
        final_data = {}

        # 3. Copy what already exists
        for field in required_fields:
            if field in data:
                final_data[field] = data[field]
            else:
                final_data[field] = None  # If field is missing, set None

        # 4. Small debug log
        missing = [f for f in required_fields if final_data[f] is None]
        if missing:
            print(f"Missing fields: {missing}")

        return final_data
        # END OF ADDED CODE


    def get_selectors(self) -> Dict[str, str]:

        """
        Return CSS selectors specific to Imovirtual website structure.
        
        These selectors are based on the actual HTML structure of Imovirtual
        and should be updated if the website changes.
        
        Returns:
            Dictionary mapping field names to CSS selectors or XPaths.
        """
        return {
            'item_container': 'article[data-sentry-component="AdvertCard"]',
            'link': 'a[data-cy="listing-item-link"]',
            'title': '[data-cy="adPageAdTitle"]',
            'description': '[data-cy="adPageAdDescription"]',
            'agent_name': '[data-cy="ad-contact-form-content"] p:first-of-type',
            'location_address': '[data-sentry-component="MapLink"] a',
            'scraped_price': 'strong[data-cy="adPageHeaderPrice"]',
            'area_sqm': 'div[data-sentry-element="ItemGridContainer"]:has-text("Área") div:nth-child(2)',
            'num_bedrooms': 'div[data-sentry-element="ItemGridContainer"]:has-text("Tipologia") div:nth-child(2)',
            'num_bathrooms': 'div[data-sentry-element="ItemGridContainer"]:has-text("Casas de banho") div:nth-child(2)',
            'floor_number': 'div[data-sentry-element="ItemGridContainer"]:has-text("Walk") div:nth-child(2)',
            'update_date': 'p[data-nx-name="NexusText"]',
            'listing_id':'p[data-sentry-element="DetailsProperty"]:has-text("ID"),[data-sentry-source-file="AdMetadata.tsx"] p:has-text("ID"),.css-1fla28g:has-text("ID")',
        }
    
    def extract_non_selector_data(self, page, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Extracts data that CANNOT be obtained through CSS selectors.
        
        For ApartmentRentStrategy, this includes the following 3 fields:
        1. condition (str): The condition of the apartment extracted from description
        Possible values: 'novo', 'bom', 'excelente', 'renovar', 'usado', or None
        
        2. furnished (str): Whether the apartment is furnished
        Possible values: 'yes', 'no', or None if not found
        
        3. has_elevator (str): Whether the building has an elevator
        Possible values: 'yes', 'no', raw string value from page, or empty string if not found
        
        Args:
            page: Playwright page object for the listing detail page
        
        Returns:
            Dictionary containing the 3 non-selector fields:
            {
                'condition': str or None,
                'furnished': str or None, 
                'has_elevator': str or None
                'energy_certificate': str or None
                'floor_number': str or None
                'update_date': str or None
            }
        """
        # Get description for condition extraction
        description = None
        try:
            description_element = page.locator(self.get_selectors()['description']).first
            if description_element.count():
                description = description_element.text_content()
        except:
            description = None
        
        # Extract the 3 non-selector fields
        data['condition'] = self._extract_condition(data) if description else None
        data['furnished'] = self._extract_furnished(page, data)
        data['has_elevator'] = self._extract_has_elevator(page, data)
        data['energy_certificate'] = self._extract_energy_certificate(page, data)
        data['floor_number'] = self._extract_floor(page, data)
        data['update_date'] = self._extract_update_date(page, data)
        
        return data

    #strategy methods for non selector fields

    def _extract_furnished(self, page, data: Dict[str, Any]) -> Optional[str]:
        """
        Extract furnished status from the Equipment section.
        
        Returns 'yes' if furniture/mobilado is mentioned, 'no' otherwise.
        """
        containers = page.query_selector_all('div[data-sentry-element="ItemGridContainer"]')
        
        for container in containers:
            try:
                label = container.query_selector('div:nth-child(1)').inner_text().strip().lower()
                if label.startswith("equipment") or label.startswith("equipamento"):
                   
                    items_div = container.query_selector('div:nth-child(2)')
                    if not items_div:
                        return None
                    spans = items_div.query_selector_all('span')
                    for span in spans:
                        text = span.inner_text().strip().lower()
                        if "furniture" in text or "mobilado" in text:
                            return "yes"
                    
                    return None
            except Exception:
                continue

        # 
        return None

    def _extract_has_elevator(self, page, data: Dict[str, Any]) -> Optional[str]:
        """
        Extract elevator information.
        
        Returns:
            "yes"  -> elevator present
            "n/a"  -> explicitly no elevator
            "no"   -> no information / unknown / not specified
            None   -> function failed to find info
        """
        containers = page.query_selector_all('div[data-sentry-element="ItemGridContainer"]')

        for item in containers:
            try:
                text = item.text_content()
                if not text:
                    continue

                text_lower = text.lower()

                if "elevador" in text_lower or "lift" in text_lower:
                    value_el = item.query_selector(':scope > div:nth-child(2)')
                    if not value_el:
                        return "no"  

                    value = value_el.text_content().strip().lower()

                    
                    if value in ["sim", "yes", "aye"]:
                        return "yes"

                    
                    if value in ["não", "nao", "no"]:
                        return "n/a"

                    
                    if value in ["sem informação", "n/a", "", "-", "—"]:
                        return "no"

                    
                    return value

            except Exception:
                continue

        
        return None

    def _extract_condition(self, data: Dict[str, Any]) -> Optional[str]:
        """
        Extracts property condition using structured fields + description.

        Returns:
            'novo', 'excelente', 'bom', 'renovar', 'usado', or None
        """

        # -------- 1. STRUCTURED SIGNALS (highest confidence) --------

        # New construction (Portuguese / English / boolean-safe)
        new_construction = str(data.get('new_construction', '')).lower()
        if new_construction in ('sim', 'yes', 'true', '1'):
            return 'novo'

        # Year of construction
        year = data.get('construction_year')
        try:
            year = int(year)
            if year >= 2022:
                return 'novo'
        except (TypeError, ValueError):
            pass

        # Finishing phase
        finishing = str(data.get('finishing_phase', '')).lower()
        if finishing in ('pronto a habitar', 'ready to move in', 'novo'):
            return 'novo'

        # -------- 2. DESCRIPTION-BASED LOGIC --------

        description = data.get('description', '')
        if not description:
            return "n/a"

        desc_lower = description.lower()

        patterns = [
            # Portuguese — specific first
            (r'(?:nova?|novo)\s+construç[aã]o', 'novo'),
            (r'pronto\s+a\s+habitar', 'novo'),
            (r'acabamentos?\s+de\s+luxo', 'excelente'),
            (r'excelente\s+(?:estado|condiç[aã]o)', 'excelente'),
            (r'ótim[oa]\s+(?:estado|condiç[aã]o)', 'excelente'),
            (r'bom\s+(?:estado|condiç[aã]o)', 'bom'),
            (r'em\s+bom\s+estado', 'bom'),
            (r'(?:precisa|necessita)\s+de\s+renovaç[aã]o', 'renovar'),
            (r'para\s+renovar|a\s+renovar', 'renovar'),
            (r'usado|habitad[oa]', 'usado'),

            # English fallback
            (r'new\s+construction|brand\s+new', 'novo'),
            (r'excellent\s+condition', 'excelente'),
            (r'good\s+condition', 'bom'),
            (r'needs?\s+renovat', 'renovar'),
            (r'used|previously\s+owned', 'usado'),
        ]

        for pattern, condition in patterns:
            if re.search(pattern, desc_lower, re.IGNORECASE):
                return condition

        # -------- 3. WEAK FALLBACK HEURISTICS --------

        if any(word in desc_lower for word in ['luxo', 'premium', 'exclusive']):
            return 'excelente'

        return None

    def _extract_energy_certificate(self, page, data) -> Optional[str]:
        """
        Extract the energy certificate (Certificado energético) from listing details.

        Returns:
            Certificate value (e.g. "A", "B", "C", "F")
            "n/a"  
            None   
        """
        containers = page.query_selector_all(
            'div[data-sentry-element="ItemGridContainer"]'
        )

        for item in containers:
            try:
                full_text = item.text_content()

                if not full_text:
                    continue

                text_lower = full_text.lower()

                
                if "certificado energético" in text_lower or "categoria energética" in text_lower:
                    value_el = item.query_selector(':scope > div:nth-child(2)')

                    if not value_el:
                        return None  

                    value = value_el.text_content().strip()

                    
                    if value.lower() in ["sem informação", "não informado", "n/a", "", "-", "—"]:
                        return "n/a"

                    
                    return value

            except Exception:
                continue

    
        return None

    def _extract_floor(self, page, data):
        containers = page.query_selector_all(
            'div[data-sentry-element="ItemGridContainer"]'
        )

        for item in containers:
            try:
                label_el = item.query_selector(':scope > *:nth-child(1)')
                value_el = item.query_selector(':scope > *:nth-child(2)')

                if not label_el or not value_el:
                    continue

                label = label_el.inner_text().strip().lower()
                label = label.replace(":", "")

                if "andar" in label:
                    value = value_el.inner_text().strip().lower()

                    if value in ["sem informação", "n/a", "", "-", "—"]:
                        return "n/a"

                    return value

            except Exception:
                continue

        return None
    
    def _extract_update_date(self, page, data: Dict[str, Any]) -> Optional[str]:
        """
        Extract the 'Last updated' date from the AdHistoryBase container.

        Args:
            page: Playwright page object
            data: dictionary with already extracted data (unused here)

        Returns:
            Date string in format 'dd.mm.yyyy', or 'without information' if not found
        """
        try:
            # 1. 
            container = page.query_selector('div[data-sentry-component="AdHistoryBase"]')
            if not container:
                return 'without information'

            # 2. 
            el = container.query_selector('p[data-nx-name="NexusText"]')
            if not el:
                return 'without information'

            # 3. 
            text = el.text_content().strip()
            match = re.search(r'(\d{2}\.\d{2}\.\d{4})', text)
            return match.group(1) if match else text

        except Exception:
            return None