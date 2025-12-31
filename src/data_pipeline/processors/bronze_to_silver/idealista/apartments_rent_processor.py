from datetime import datetime, timedelta
from typing import Optional
from typing import List, Dict, Any
from word2number import w2n
import re
from ...base_processor import BaseProcessor


class IdealistaApartmentRentProcessor(BaseProcessor):
    """
    Processor for Idealista apartments rent property data.
    Transforms Idealista-specific bronze format to standardized silver format.
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
            'property_id': lambda: bronze_record.get('listing_id'), #temporary take same exact id value
            'price_eur': lambda: self._extract_price(bronze_record.get('scraped_price')), 
            'area_m2': lambda: self._extract_area(bronze_record.get('area_sqm')), 
            'municipality': lambda: self._normalize_municipality(bronze_record.get('municipality')), # rewrite?
            'source': lambda: self.source, 
            'property_type': lambda: self.property_type,
            'processed_at': lambda: datetime.now().isoformat(),
            'title': lambda: bronze_record.get('title'),
            'agent_name': lambda: bronze_record.get('agent_name'),
            'description': lambda: bronze_record.get('description'),
            'energy_certificate': lambda: bronze_record.get('energy_certificate'),
            'source_updated_at': lambda: self._parse_update_date(bronze_record.get('update_date'), bronze_record.get('scraped_at')),# rewrite
            'location_text': lambda: bronze_record.get('location_address'),
            'condition': lambda: self._normalize_condition(bronze_record.get('condition')), # write
            'furnished': lambda: self._normalize_furnished(bronze_record.get('furnished')),  # write
            'num_bedrooms': lambda: self._normalize_num_bedrooms(bronze_record.get('num_bedrooms')), # write
            'num_bathrooms': lambda: self._normalize_num_bathrooms(bronze_record.get('num_bathrooms')),# write
            'floor_number': lambda: self._extract_floor_number(bronze_record.get('floor_number')), # write
            'has_elevator': lambda: self._normalize_elevator(bronze_record.get('has_elevator')), # write
            'listing_url': lambda: bronze_record.get('listing_url'),
            'scraping_timestamp': lambda: bronze_record.get('scraped_at'),
            'data_quality_score': lambda: self._calculate_data_quality_score(bronze_record),  # rewrite
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
        listing_id = record.get('listing_id')
        if listing_id:
            return f"idealista_{self.property_type}_{listing_id}"
        else:
            # Temporary: skip records without listing_id
            self.logger.warning(f"Skipping record without listing_id: {record}")
            return None
    
    def _extract_price(self, price_str: str) -> float:
        """Simplified version for consistent Idealista format"""
        if not price_str:
            return None
        
        try:
            # Remove all non-numeric symbols exept for commas
            cleaned = re.sub(r'[^\d,]', '', price_str.strip())
            # Remove commas (thousands separators)
            cleaned = cleaned.replace(',', '')
            return float(cleaned) if cleaned else None
            
        except (ValueError, TypeError) as e:
            self.logger.warning(f"Failed to parse price '{price_str}': {e}")
            return None
    
    def _extract_area(self, area_str: str) -> int:
        """Extract numeric area - prioritize floor area for rentals"""
        if not area_str:
            return None
        
        normalized = area_str.strip().lower()
        
        # 1. Priority: floor area (usable living space)
        # Example: "45 m² built, 40 m² floor area" → use 40
        floor_match = re.search(r'(\d+)\s*m²\s*floor', normalized)
        if floor_match:
            return int(floor_match.group(1))
        
        # 2. Fallback: built area (constructed area)
        built_match = re.search(r'(\d+)\s*m²\s*built', normalized)
        if built_match:
            return int(built_match.group(1))
        
        # 3. Generic "m²"
        simple_match = re.search(r'(\d+)\s*m²', normalized)
        if simple_match:
            return int(simple_match.group(1))
        
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
            "vial_nova_de_gaia": "vila_nova_de_gaia"
        }
        
        return normalizations.get(normalized, normalized)
    
    def _normalize_condition(self, raw_condition: str) -> str:
        """Minimal condition normalization for Idealista"""
        if not raw_condition:
            return "unknown"
        
        raw_lower = raw_condition.lower()
        
        if "second hand/good condition" in raw_lower:
            return "good"
        elif "second hand/needs renovating" in raw_lower:
            return "needs_renovation"
        else:
            return "unknown"
    
    def _normalize_furnished(self, furnished_str: str) -> Optional[bool]:
        """Normalize furnished status to boolean or None if unknown"""
        if not furnished_str:
            return None  # Unknown, not False!
        
        furnished_str = furnished_str.lower().strip()
        
        # Handle unknown cases first
        unknown_keywords = ['not indicated', 'unknown', 'n/a', 'not specified', '']
        if any(keyword in furnished_str for keyword in unknown_keywords):
            return None
        
        # Explicit false
        false_keywords = ['unfurnished', 'without furniture', 'no furniture', 'unfurnished house']
        if any(keyword in furnished_str for keyword in false_keywords):
            return False
        
        # Explicit true
        true_keywords = ['furnished', 'with furniture', 'equipped', 'furnished and with equipped kitchen']
        if any(keyword in furnished_str for keyword in true_keywords):
            return True
        
        # Special case: kitchen mentioned but furniture status unclear
        if 'kitchen' in furnished_str and 'furnished' not in furnished_str:
            return None  # Unknown – kitchen mentioned but furniture not specified
        
        return None  # Default to unknown

    def _normalize_num_bedrooms(self, bedrooms_str: str) -> int:
        """Normalize bedrooms count from various formats to integer"""
        if not bedrooms_str:
            return 0  # default value
        
        # Convert to lowercase for easier processing
        bedrooms_lower = bedrooms_str.lower().strip()
        
        # 1. Handle T-format labels (T0, T1, T2, T3, T4, T5, T6)
        t_match = re.search(r't([0-6])', bedrooms_lower)
        if t_match:
            return int(t_match.group(1))
        
        # 2. Handle numeric labels (1 bedroom, 2 bedrooms, etc.)
        num_match = re.search(r'(\d+)\s*bedrooms?', bedrooms_lower)
        if num_match:
            return int(num_match.group(1))
        
        # 3. Handle text-based labels (one bedroom, two bedrooms, etc.)
        text_numbers = {
            'one': 1, 'two': 2, 'three': 3, 'four': 4, 
            'five': 5, 'six': 6, 'seven': 7, 'eight': 8
        }
        for text, number in text_numbers.items():
            if text in bedrooms_lower and 'bedroom' in bedrooms_lower:
                return number
        
        # 4. If there is only the word "bedroom" without a number — assume 1 bedroom
        if 'bedroom' in bedrooms_lower and 'bedrooms' not in bedrooms_lower:
            return 1
        
        # 5. If the word "bedrooms" appears without a number — try extracting context
        if 'bedrooms' in bedrooms_lower:
            # Try to find any number in the string
            any_num_match = re.search(r'(\d+)', bedrooms_str)
            if any_num_match:
                return int(any_num_match.group(1))
            # If no numbers but "bedrooms" is present — suspicious, return 0
            return 0
        
        # 6. If the string contains only a number — use it
        simple_num_match = re.search(r'^\s*(\d+)\s*$', bedrooms_str)
        if simple_num_match:
            return int(simple_num_match.group(1))
        
        # 7. Fallback — try to find any number in the string
        fallback_match = re.search(r'(\d+)', bedrooms_str)
        if fallback_match:
            return int(fallback_match.group(1))
        
        # If nothing is recognized
        return 0

    
    def _normalize_num_bathrooms(self, bathrooms_str: str) -> int:
        """Normalize bathrooms count from string to integer"""
        if not bathrooms_str:
            return 0  # default value
        
        # Convert to lowercase for easier processing
        bathrooms_lower = bathrooms_str.lower().strip()
        
        # 1. Handle numeric representations (1 bathroom, 2 bathrooms, etc.)
        num_match = re.search(r'(\d+)\s*bathrooms?', bathrooms_lower)
        if num_match:
            return int(num_match.group(1))
        
        # 2. Handle textual representations (one bathroom, two bathrooms, etc.)
        text_numbers = {
            'one': 1, 'two': 2, 'three': 3, 'four': 4, 
            'five': 5, 'six': 6
        }
        for text, number in text_numbers.items():
            if text in bathrooms_lower and 'bathroom' in bathrooms_lower:
                return number
        
        # 3. If there is just the word "bathroom" without a number - assume 1 bathroom
        if 'bathroom' in bathrooms_lower and 'bathrooms' not in bathrooms_lower:
            return 1
        
        # 4. If there is the word "bathrooms" without a number - try to extract context
        if 'bathrooms' in bathrooms_lower:
            # Try to find any number in the string
            any_num_match = re.search(r'(\d+)', bathrooms_str)
            if any_num_match:
                return int(any_num_match.group(1))
            # If there are no numbers but "bathrooms" exists - suspicious, return 0
            return 0
        
        # 5. If the string contains just a number - use it
        simple_num_match = re.search(r'^\s*(\d+)\s*$', bathrooms_str)
        if simple_num_match:
            return int(simple_num_match.group(1))
        
        # 6. Fallback - try to find any number in the string
        fallback_match = re.search(r'(\d+)', bathrooms_str)
        if fallback_match:
            return int(fallback_match.group(1))
        
        # If nothing was recognized
        return 0

    def _extract_floor_number(self, floor_str: str) -> int:
        """Advanced floor extraction with full text number support"""
        if not floor_str or floor_str.lower() in ['not indicated', 'unknown', '']:
            return None
        
        floor_lower = floor_str.lower().strip()
        
        # Ground floor
        if any(term in floor_lower for term in ['ground floor', 'rez-de-chaussée', 'r/c']):
            return 0
        
        # Basement
        if 'basement' in floor_lower:
            # Attempt to extract the basement number
            basement_match = re.search(r'(\d+)\s*(?:st|nd|rd|th)?\s*basement', floor_lower)
            if basement_match:
                return -int(basement_match.group(1))
            
            # Attempt to recognize a textual number for the basement
            try:
                # Remove the word "basement" and try to parse the remaining text
                text_for_conversion = floor_lower.replace('basement', '').strip()
                if text_for_conversion:
                    number = w2n.word_to_num(text_for_conversion)
                    return -number
            except:
                pass
            
            return -1
        

        
        # Main number extraction logic
        # 1. First, search for numeric formats
        ordinal_match = re.search(r'(\d+)(?:st|nd|rd|th)', floor_lower)
        if ordinal_match:
            return int(ordinal_match.group(1))
        
        number_match = re.search(r'(\d+)', floor_str)
        if number_match:
            return int(number_match.group(1))
        
        # 2. Attempt to recognize a textual number representation
        try:
            # Remove the word "floor" and try to parse the remaining text
            text_for_conversion = floor_lower.replace('floor', '').strip()
            if text_for_conversion:
                return w2n.word_to_num(text_for_conversion)
        except:
            pass
        
        return None
    
    def _normalize_elevator(self, elevator_str: str) -> bool:
        """elevator normalization"""
        if not elevator_str:
            return None
        
        elevator_lower = elevator_str.lower().strip()
        
        if elevator_lower == "with lift":
            return True
        elif elevator_lower == "no lift":
            return False
        else:
            return None

    def _parse_update_date(self, update_str: str, scraping_timestamp: str) -> str:
        """Parse update date string relative to scraping timestamp"""
        if not update_str or not scraping_timestamp:
            return None
        
        try:
            # Parse scraping timestamp as reference point
            scraped_at = datetime.fromisoformat(scraping_timestamp.replace('Z', '+00:00'))
            update_str = update_str.lower().strip()
            
            # "just now", "today", "0 minutes" – use scraping timestamp
            if any(phrase in update_str for phrase in ["just now", "today", "0 minutes"]):
                return scraped_at.isoformat()
            
            # ADD: Extract minutes
            minutes_match = re.search(r'(\d+)\s*minutes?', update_str)
            if minutes_match:
                minutes = int(minutes_match.group(1))
                return (scraped_at - timedelta(minutes=minutes)).isoformat()
            
            # Extract hours
            hours_match = re.search(r'(\d+)\s*hours?', update_str)
            if hours_match:
                hours = int(hours_match.group(1))
                return (scraped_at - timedelta(hours=hours)).isoformat()
            
            # Extract days
            days_match = re.search(r'(\d+)\s*days?', update_str)
            if days_match:
                days = int(days_match.group(1))
                return (scraped_at - timedelta(days=days)).isoformat()
            
            # Extract weeks
            weeks_match = re.search(r'(\d+)\s*weeks?', update_str)
            if weeks_match:
                weeks = int(weeks_match.group(1))
                return (scraped_at - timedelta(weeks=weeks)).isoformat()
            
            # Handle "more than X month(s) ago" – use maximum boundary
            month_match = re.search(r'more than\s*(\d+)\s*months?', update_str)
            if month_match:
                months = int(month_match.group(1))
                estimated_days = months * 60  # Conservative estimate
                return (scraped_at - timedelta(days=estimated_days)).isoformat()
            
            # Regular months
            months_match = re.search(r'(\d+)\s*months?', update_str)
            if months_match:
                months = int(months_match.group(1))
                return (scraped_at - timedelta(days=months * 30)).isoformat()
            
            # ADD: Handle "more than 1 year ago"
            year_match = re.search(r'more than\s*(\d+)\s*years?', update_str)
            if year_match:
                years = int(year_match.group(1))
                estimated_days = years * 365  # Conservative estimate
                return (scraped_at - timedelta(days=estimated_days)).isoformat()
            
            self.logger.warning(f"Could not parse update date: {update_str}")
            return None
            
        except Exception as e:
            self.logger.warning(f"Error parsing update date '{update_str}': {e}")
            return None


    def _calculate_data_quality_score(self, record: Dict) -> float:
        """Calculate detailed data quality score"""
        weights = {
            'price_eur': 0.2,
            'area_m2': 0.2,
            'num_bedrooms': 0.15,
            'num_bathrooms': 0.15,
            'location_text': 0.1,
            'energy_certificate': 0.05,
            'condition': 0.05,
            'floor_number': 0.05,
            'has_elevator': 0.05,
        }
        
        score = 0.0
        total_weight = 0.0
        
        for field, weight in weights.items():
            value = record.get(field)
            if self._is_field_high_quality(value):
                score += weight
            total_weight += weight
        
        return round(score / total_weight if total_weight > 0 else 0, 2)

    def _is_field_high_quality(self, value: Any) -> bool:
        """More sophisticated quality check"""
        if value is None:
            return False
        
        if isinstance(value, str):
            normalized = value.strip().lower()
            return bool(normalized) and normalized not in [
                'unknown', 'not indicated', 'n/a', '', 'not available'
            ]
        
        if isinstance(value, (int, float)):
            # For area and price, verify realistic ranges
            if value <= 0:
                return False
            # Additional context-specific checks can be added here
            return True
        
        return True