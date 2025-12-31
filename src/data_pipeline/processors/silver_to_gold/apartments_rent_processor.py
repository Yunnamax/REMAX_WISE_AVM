from datetime import datetime, timedelta
from typing import Optional
from typing import List, Dict, Any
import pandas as pd
import json
from word2number import w2n
from pathlib import Path
import re
from ..base_gold_processor import BaseGoldProcessor


class ApartmentRentProcessor(BaseGoldProcessor):
    """
    Processor for apartments rent property data.
    Transforms silver format to enriched gold format with computed fields.
    """

    def get_municipality_coords(municipality_name):
        if pd.isna(municipality_name):
            return None, None
        
        
        coords_map = {
            'lisbon': (38.7223, -9.1393), 'cascais': (38.6979, -9.4214),
            'sintra': (38.8000, -9.3833), 'oeiras': (38.6910, -9.3100),
            'almada': (38.6803, -9.1583), 'porto': (41.1495, -8.6108),
            'vila_nova_de_gaia': (41.1333, -8.6167), 'coimbra': (40.2111, -8.4291),
            'leiria': (39.7436, -8.8070), 'aveiro': (40.6405, -8.6538)
        }
        
        return coords_map.get(str(municipality_name).lower().strip(), (None, None))
    #TODO - make mapping a function, not a field
    master_mapping = {
        # Common fields from Silver
        'property_id': ('property_id', None),
        'source_system': ('source', None),
        'listing_url': ('listing_url', None),
        'title': ('title', None),
        'description': ('description', None),
        'agent_name': ('agent_name', None),
        'location_text': ('location_text', None),
        'municipality': ('municipality', None),
        'data_quality_score': ('data_quality_score', None),
        
        # Calculated/constant fields
        'property_type': (None, lambda df: 'apartment_rent'),
        'transaction_type': (None, lambda df: 'rent'),
        'price_value': ('price_eur', None),
        'price_period': (None, lambda df: 'monthly'),
        'area_m2': ('area_m2', None),
        
        # Timestamps
        'scraped_at': ('scraping_timestamp', None),
        'source_updated_at': ('source_updated_at', None),
        'processed_at_gold': (None, lambda df: datetime.now()),  
        
        # Coordinates (placeholder for now)
        'municipality_latitude': (None, lambda df: df['municipality'].apply(
            lambda x: ApartmentRentProcessor.get_municipality_coords(x)[0]
        )),
        'municipality_longitude': (None, lambda df: df['municipality'].apply(
            lambda x: ApartmentRentProcessor.get_municipality_coords(x)[1]
        )),
    'district_latitude': (None, lambda df: pd.Series([None] * len(df))),
    'district_longitude': (None, lambda df: pd.Series([None] * len(df))),
        
        # SCD Type 2
        'valid_from': (None, lambda df: datetime.now()),
        'valid_to': (None, lambda df: pd.Series([None] * len(df))),
        'is_current': (None, lambda df: pd.Series([True] * len(df))),
        
        # NEW ENRICHED FIELDS
        # Price analysis
        'price_per_sqm': (None, lambda df: df['price_eur'] / df['area_m2'].replace(0, pd.NA)),
        'price_category': (None, lambda df: pd.qcut(
            df['price_eur'], 
            q=3, 
            labels=['budget', 'medium', 'premium'],
            duplicates='drop'
        )),
        
        # Location analysis
        'district': (None, lambda df: df['location_text'].str.extract(r'District\s+([^,]+)')[0]),
        'is_central_area': (None, lambda df: df['municipality'].str.contains(
            'lisbon|porto|central', case=False, na=False
        )),
        
        # Time analysis
        'days_since_last_update': (None, lambda df: (
            (pd.to_datetime(df['scraping_timestamp']) - pd.to_datetime(df['source_updated_at'])).dt.days
        )),
        
        # Text analysis
        'title_length': (None, lambda df: df['title'].str.len().fillna(0)),
        'description_length': (None, lambda df: df['description'].str.len().fillna(0)),
        'has_contact_info': (None, lambda df: df['description'].str.contains(
            r'contact|phone|email|tel\.|@', case=False, na=False
        )),
        'agent_type': (None, lambda df: df['agent_name'].apply(
            lambda x: 'professional' if pd.notna(x) and any(word in str(x).lower() for word in [
                'lda', 'ltd', 'inc', 'real estate', 'imobiliária', 'mediação', 'sociedade'
            ]) else 'private' if pd.notna(x) else None
        )),
    }
    
    # DETAILS MAPPING
    details_mapping = {
        # Basic fields
        'property_id': ('property_id', None),
        'num_bedrooms': ('num_bedrooms', None),
        'num_bathrooms': ('num_bathrooms', None),
        'floor_number': ('floor_number', None),
        'has_elevator': ('has_elevator', None),
        'furnished': ('furnished', None),
        'condition': ('condition', None),
        'energy_certificate': ('energy_certificate', None),
        
        # NEW ENRICHED FIELDS
        # Floor categorization
        'floor_category': ('floor_number', lambda x: pd.cut(
            x,
            bins=[-float('inf'), 0, 3, 7, float('inf')],
            labels=['ground', 'low', 'mid', 'high'],
            include_lowest=True
        )),
        
        # Condition normalization
        'condition_normalized': ('condition', lambda x: x.str.lower().map({
            'excellent': 'excellent',
            'good': 'good', 
            'renovated': 'excellent',
            'new': 'excellent',
            'requires renovation': 'fair',
            'to renovate': 'fair',
            'poor': 'poor'
        }).fillna('fair')),
        
        # Energy analysis
        'energy_rating': ('energy_certificate', lambda x: x.str.upper().str.strip()),
        'energy_efficiency_score': ('energy_certificate', lambda x: x.str.upper().map({
            'A': 7, 'B': 6, 'C': 5, 'D': 4, 'E': 3, 'F': 2, 'G': 1
        })),
        
        
        # Property age estimation from description
        'property_age_group': (None, lambda df: df['description'].str.contains(
            r'new|renovated|recent|remodeled|modern', case=False
        ).map({True: 'new', False: 'standard'})),
        
        # Features extracted from description
        'has_balcony': (None, lambda df: df['description'].str.contains(
            r'balcony|terrace|solarium', case=False, na=False
        )),
        'has_parking': (None, lambda df: df['description'].str.contains(
            r'parking|garage|estacionamento', case=False, na=False
        )),
    }

    def __init__(self, schema_registry, property_type: str):
        """Initialize with enriched schemas."""
        super().__init__(schema_registry, property_type)
        # Load enriched schemas instead of regular ones
        self._load_enriched_schemas()

        #path to admin reference book
        project_root = Path(__file__).parent.parent.parent.parent.parent 
        ref_path =  project_root / "config" / "geospatial"/ "location_names" / "districts_reference.json"
        with open(ref_path, 'r', encoding='utf-8') as f:
            self.geo_reference = json.load(f)

    #TODO - change terminal solution for district extrection 
    def _extract_district_smart(self, df: pd.DataFrame) -> pd.Series:
        """
        Интеллектуальный поиск района (freguesia) на основе португальского справочника.
        Выполняет трансляцию названий муниципалитетов с английского на португальский.
        """
        # 1. Словарь перевода: ваш Silver (EN) -> Справочник (PT)
        muni_translate = {
            "almada": "Almada",
            "aveiro": "Aveiro",
            "cascais": "Cascais",
            "coimbra": "Coimbra",
            "leiria": "Leiria",
            "lisbon": "Lisboa",
            "oeiras": "Oeiras",
            "porto": "Porto",
            "sintra": "Sintra",
            "vila_nova_de_gaia": "Vila Nova de Gaia"
        }

        def find_match(row):
            # Получаем название муниципалитета из строки, приводим к нижнему регистру
            raw_muni = str(row.get('municipality', '')).lower().strip()
            
            # Получаем португальский эквивалент для поиска в JSON
            pt_muni = muni_translate.get(raw_muni)
            
            # Если муниципалитет не найден в нашем списке перевода — выходим
            if not pt_muni:
                return None
                
            # Берем список районов для этого города из загруженного JSON-справочника
            districts = self.geo_reference.get(pt_muni, [])
            
            # Берем текст адреса для поиска
            address = str(row.get('location_text', '')).lower()
            
            # 3. Ищем точное упоминание района в тексте адреса
            for d_name in districts:
                # Переводим название района в нижний регистр для корректного поиска
                if d_name.lower() in address:
                    return d_name # Возвращаем официальное название (на португальском)
            
            return None

        # Применяем функцию к каждой строке датафрейма
        return df.apply(find_match, axis=1)

    def _load_enriched_schemas(self):
        """Load enriched Gold schemas from registry."""
        try:
            # Master schema is the same for all property types
            self.master_schema = self.schema_registry.load_gold_schema('master_properties')
            
            # Details schema is specific to property type
            self.details_schema = self.schema_registry.load_gold_schema(
                f'{self.property_type}_details'
            )
            
            self.logger.info(f"Loaded enriched Gold schemas")
            
        except Exception as e:
            self.logger.error(f"Error loading enriched Gold schemas: {e}")
            # Fall back to regular schemas
            self.logger.warning("Falling back to regular schemas")
            self._load_schemas()

    def _transform_data(self, silver_df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """
        Transform Silver DataFrame to enriched Gold format using mappings.
        Includes computed fields for price analysis, location analysis, and property features.
        """
        self.logger.info(f"Starting transformation of {len(silver_df)} records to enriched Gold format")
        
        try:
            # Process master fields
            master_data = self._process_mapping(silver_df, self.master_mapping, "master")
            
            # Process details fields
            details_data = self._process_mapping(silver_df, self.details_mapping, "details")
            
            # Add computed fields that require master data for details
            details_data = self._add_cross_computed_fields(details_data, master_data, silver_df)
            
            # Create DataFrames
            master_df = pd.DataFrame(master_data)
            details_df = pd.DataFrame(details_data)
            
            #TODO delete when mappinf is a method and _extract_district is in use
            master_df['district'] = self._extract_district_smart(silver_df)

            # Log success
            self.logger.info(f"Successfully transformed to enriched Gold format")
            self.logger.info(f"Master fields: {list(master_df.columns)}")
            self.logger.info(f"Details fields: {list(details_df.columns)}")
            
            return {
                'master': master_df,
                'details': details_df
            }
            
        except Exception as e:
            self.logger.error(f"Error in transformation: {e}")
            raise
    
    def _process_mapping(self, silver_df: pd.DataFrame, mapping: Dict, mapping_name: str) -> Dict:
        """Process a mapping dictionary to transform data."""
        result_data = {}
        
        for gold_field, (silver_field, transform_func) in mapping.items():
            try:
                # Case 1: Direct mapping
                if silver_field and transform_func is None:
                    if silver_field in silver_df.columns:
                        result_data[gold_field] = silver_df[silver_field]
                    else:
                        self.logger.warning(f"Silver field '{silver_field}' not found for {mapping_name} field '{gold_field}'")
                        result_data[gold_field] = pd.Series([None] * len(silver_df), name=gold_field)
                
                # Case 2: Transformation of single field
                elif silver_field and transform_func:
                    if silver_field in silver_df.columns:
                        result_data[gold_field] = transform_func(silver_df[silver_field])
                    else:
                        self.logger.warning(f"Silver field '{silver_field}' not found for {mapping_name} field '{gold_field}'")
                        result_data[gold_field] = pd.Series([None] * len(silver_df), name=gold_field)
                
                # Case 3: Calculated field using entire DataFrame
                elif silver_field is None and transform_func:
                    result_data[gold_field] = transform_func(silver_df)
                    
            except Exception as e:
                self.logger.error(f"Error processing {mapping_name} field '{gold_field}': {e}")
                result_data[gold_field] = pd.Series([None] * len(silver_df), name=gold_field)
        
        return result_data
    
    def _add_cross_computed_fields(self, details_data: Dict, master_data: Dict, silver_df: pd.DataFrame) -> Dict:
        """Add computed fields that require data from both master and details."""
        try:
            # Calculate price per bedroom (requires price from master and bedrooms from details)
            if 'num_bedrooms' in details_data and 'price_value' in master_data:
                price_series = master_data['price_value']
                bedrooms_series = details_data['num_bedrooms']
                details_data['price_per_bedroom'] = price_series / bedrooms_series.replace(0, pd.NA)
            
            # Calculate area per bedroom
            if 'num_bedrooms' in details_data and 'area_m2' in master_data:
                area_series = master_data['area_m2']
                bedrooms_series = details_data['num_bedrooms']
                details_data['area_per_bedroom'] = area_series / bedrooms_series.replace(0, pd.NA)
            
            return details_data
            
        except Exception as e:
            self.logger.error(f"Error adding cross-computed fields: {e}")
            return details_data

    # Helper methods for more complex calculations
    def _extract_district(self, location_text: pd.Series) -> pd.Series:
        """Extract district from location text."""
        if location_text is None:
            return pd.Series([None] * len(location_text))
        
        # Pattern: "District {district_name}, ..."
        pattern = r'District\s+([^,]+)'
        extracted = location_text.str.extract(pattern, expand=False)
        return extracted.str.strip() if extracted is not None else pd.Series([None] * len(location_text))
    
    def _categorize_price(self, price_series: pd.Series) -> pd.Series:
        """Categorize price into budget, medium, premium."""
        try:
            if len(price_series.dropna()) == 0:
                return pd.Series([None] * len(price_series))
            
            # Use quantiles for categorization
            q1 = price_series.quantile(0.33)
            q2 = price_series.quantile(0.67)
            
            def categorize(price):
                if pd.isna(price):
                    return None
                elif price <= q1:
                    return 'budget'
                elif price <= q2:
                    return 'medium'
                else:
                    return 'premium'
            
            return price_series.apply(categorize)
            
        except Exception as e:
            self.logger.error(f"Error categorizing price: {e}")
            return pd.Series([None] * len(price_series))