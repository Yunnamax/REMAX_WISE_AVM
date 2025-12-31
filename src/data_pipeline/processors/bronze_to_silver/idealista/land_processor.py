from datetime import datetime
from typing import List, Dict, Any
import re
from ...base_processor import BaseProcessor


class IdealistaLandProcessor(BaseProcessor):
    """
    Processor for Idealista land property data.
    Transforms Idealista-specific bronze format to standardized silver format.
    """
    """
    def __init__(self, schema_registry):
        # Fixed parametrs for this processor
        super().__init__(
            schema_registry=schema_registry,
            source="idealista",      
            property_type="land"     
        )
    """
    def transform_data(self, raw_data: List[Dict]) -> List[Dict]:
        self.logger.info("Starting data transformation")
        transformed = []
        
        for i, record in enumerate(raw_data):
            try:
                # Log the type of each entry 
                if not isinstance(record, dict):
                    self.logger.error(f"Record {i} is not a dictionary: {type(record)} - {record}")
                    continue
                    
                transformed_record = self._transform_single_record(record)
                transformed.append(transformed_record)
                
            except Exception as e:
                self.logger.error(f"Error transforming record {i}: {e}")
                self.logger.error(f"Problematic record: {record}")
                continue
        
        self.logger.info(f"Successfully transformed {len(transformed)} records")
        return transformed
    
    def _transform_single_record(self, bronze_record: Dict) -> Dict:
        """
        Transform a single bronze record to silver format using schema as single source of truth.
        """
        silver_record = {}
        
        # Retrieve all fields from the Silver schema
        silver_fields = self.silver_schema['fields'] 

        # 1. Populate each field from the schema
        for field_config in silver_fields:
            field_name = field_config['name']
            silver_record[field_name] = self._get_field_value(field_name, field_config, bronze_record) 
        
        # 2. Computed fields that depend on other silver fields
        silver_record = self._calculate_computed_fields(silver_record)
        
        return silver_record

    def _get_field_value(self, field_name: str, field_config: Dict, bronze_record: Dict) -> Any:
        """
        Get value for a specific silver field from bronze record.
        """
        # Mapping of Idealista-specific fields
        field_mapping = {
            'property_id': lambda: self._generate_property_id(bronze_record),
            'price_eur': lambda: self._extract_price(bronze_record.get('scraped_price')),
            'area_m2': lambda: self._extract_area(bronze_record.get('area_sqm')),
            'municipality': lambda: self._normalize_municipality(bronze_record.get('scraped_city')),
            'source': lambda: self.source,
            'property_type': lambda: self.property_type,
            'processing_timestamp': lambda: datetime.now(),
            'title': lambda: bronze_record.get('scraped_title'),
            'land_status': lambda: bronze_record.get('land_status'),
            'agent_name': lambda: bronze_record.get('agent_name'),
            'description': lambda: bronze_record.get('description_text'),
            'energy_certificate': lambda: bronze_record.get('energy_certificate'),
            'last_update_date': lambda: self._parse_update_date(bronze_record.get('update_date')),
            'location_text': lambda: bronze_record.get('location_address'),
            'url': lambda: bronze_record.get('listing_url'),
            'scraping_timestamp': lambda: bronze_record.get('scraping_timestamp'),  # If present in bronze
            'data_quality_score': lambda: 0.0,  # Will be recalculated later
        }
        
        # Value resolution priorities:
        if field_name in field_mapping:
            # 1. Specific mapping for the field
            return field_mapping[field_name]()
        elif field_name in bronze_record:
            # 2. Direct copy if names match
            return bronze_record[field_name]
        elif 'default' in field_config:
            # 3. Default value from the schema
            return field_config['default']
        else:
            # 4. None if the field is not found
            return None

    def _calculate_computed_fields(self, silver_record: Dict) -> Dict:
        """
        Calculate computed fields that depend on other silver fields.
        """
        # Calculate price_per_sqm (if both values exist and area_m2 > 0)
        price = silver_record.get('price_eur')
        area = silver_record.get('area_m2')
        if price and area and area > 0:
            silver_record['price_per_sqm'] = round(price / area, 2)
        
        # Recalculate data_quality_score after all fields are populated
        silver_record['data_quality_score'] = self._calculate_data_quality_score(silver_record)
        
        return silver_record
    
    def _generate_property_id(self, record: Dict) -> str:
        """Generate unique property ID from Idealista listing_id"""
        listing_id = record.get('listing_id')
        if listing_id:
            return f"idealista_{listing_id}"
        else:
            # Fallback: generate from other fields
            return f"idealista_land_{hash(str(record))}"
    
    def _extract_price(self, price_str: str) -> float:
        """Extract numeric price from string like '249,000 €'"""
        if not price_str:
            return None
        
        try:
            # Remove currency symbol, spaces, and commas
            cleaned = re.sub(r'[^\d,]', '', price_str.strip())
            cleaned = cleaned.replace(',', '')
            return float(cleaned) if cleaned else None
        except (ValueError, TypeError):
            self.logger.warning(f"Failed to parse price: {price_str}")
            return None
    
    def _extract_area(self, area_str: str) -> float:
        """Extract numeric area from string like '331 m²'"""
        if not area_str:
            return None
        
        try:
            # Extract numbers (including decimals)
            match = re.search(r'(\d+[.,]?\d*)', area_str.strip())
            if match:
                area_value = match.group(1).replace(',', '.')
                return float(area_value)
            return None
        except (ValueError, TypeError):
            self.logger.warning(f"Failed to parse area: {area_str}")
            return None
    
    def _normalize_municipality(self, city: str) -> str:
        """Normalize municipality name"""
        if not city:
            return "unknown"
        
        # Basic normalization - lowercase, strip whitespace
        normalized = city.strip().lower()
        
        # Common normalizations
        normalizations = {
            "lisboa": "lisbon",
            "oporto": "porto",
        }
        
        return normalizations.get(normalized, normalized)
    
    def _parse_update_date(self, update_str: str) -> str:
        """Parse update date string to standard format"""
        if not update_str:
            return None
        
        # Simple parsing - can be enhanced later
        if "months" in update_str.lower() or "days" in update_str.lower():
            # For relative dates, use processing date
            return datetime.now().strftime('%Y-%m-%d')
        
        # TODO: Add more sophisticated date parsing if needed
        return update_str
    
    def _calculate_price_per_m2(self, price: float, area: float) -> float:
        """Calculate price per square meter"""
        if price and area and area > 0:
            return round(price / area, 2)
        return None
    
    def _calculate_data_quality_score(self, record: Dict) -> float:
        """Calculate data quality score for the record"""
        score = 0.0
        max_score = 0.0
        
        # Check critical fields
        critical_fields = ['property_id', 'price_eur', 'area_m2', 'municipality']
        for field in critical_fields:
            max_score += 1.0
            if record.get(field) not in [None, ""]:
                score += 1.0
        
        # Check important fields
        important_fields = ['title', 'location_text']
        for field in important_fields:
            max_score += 0.5
            if record.get(field) not in [None, ""]:
                score += 0.5
        
        # Normalize score (0-1)
        return round(score / max_score, 2) if max_score > 0 else 0.0