from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd
import json
import logging
from datetime import datetime

class BaseProcessor(ABC):
    """
    ABSTRACT BASE CLASS for all data processors.
    Implements the common logic for Bronze → Silver transformation.
    """
    
    def __init__(self, schema_registry, source: str, property_type: str):
        # Initialization of common components
        self.schema_registry = schema_registry
        self.source = source
        self.property_type = property_type
        self.logger = logging.getLogger(f"{source}_{property_type}_processor")
        
        # Schemas upload
        self.bronze_schema = None
        self.silver_schema = None
        self._load_schemas()
        
        # Processing metrics
        self.processed_records = 0
        self.failed_records = 0
        self.processing_start_time = None
        
    # ==================== Main methods ====================
    
    def process_file(self, input_path: Path) -> pd.DataFrame:
        """
        Main file-processing method.
        
        Processes a file from Bronze layer and returns a DataFrame with transformed data.
        Used by the coordinator for group processing.
        
        Args:
            input_path: Path to the Bronze layer JSON file
            
        Returns:
            DataFrame with processed data ready for Silver layer
            
        Raises:
            ValueError: If no data extracted, transformed, or validation failed
            Exception: Any other processing error
        """
        self.logger.info(f"Starting processing: {input_path}")
        self.processing_start_time = datetime.now()
        
        try:
            # 1. EXTRACT - read JSON data
            raw_data = self.extract_data(input_path)
            if not raw_data:
                error_msg = f"No data extracted from {input_path}"
                self.logger.warning(error_msg)
                raise ValueError(error_msg)
            
            # 2. TRANSFORM - apply business logic
            transformed_data = self.transform_data(raw_data)
            if not transformed_data:
                error_msg = f"No data after transformation from {input_path}"
                self.logger.warning(error_msg)
                raise ValueError(error_msg)
            
            # 3. VALIDATE - check against Silver schema
            if not self.validate_data(transformed_data):
                error_msg = f"Data validation failed for {input_path}"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
            
            # 4. CREATE DATAFRAME - convert to DataFrame
            df = pd.DataFrame(transformed_data)
            
            # 5. UPDATE METRICS (optional - для внутренней статистики процессора)
            self.processed_records += len(transformed_data)
            
            self.logger.info(
                f"Successfully processed {len(transformed_data)} records from {input_path}"
            )
            return df
            
        except Exception as e:
            self.logger.error(f"Error processing {input_path}: {e}")
            # Rethrow the exception so that coordinator can handle it
            raise

    def extract_data(self, file_path: Path) -> List[Dict[str, Any]]:
        """JSON file data extraction from Bronze layer"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Direct upload - expecting list format
            if isinstance(data, list):
                return data
            else:
                self.logger.error(f"Expected list in {file_path}, got {type(data)}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error extracting data from {file_path}: {e}")
            return []

    @abstractmethod
    def transform_data(self, raw_data: List[Dict]) -> List[Dict]:
        """ABSTRACT: Data-specific transformation"""
        pass

    def validate_data(self, data: List[Dict]) -> bool:
        """Transformed data validation against Silver schema"""
        if not data:
            self.logger.warning("No data to validate")
            return False
        
        # Get required fields from Silver schema
        required_fields = [field['name'] for field in self.silver_schema['fields'] 
                        if field.get('required', False)]
        
        # Check only for required fields presence
        for record in data:
            missing_fields = [field for field in required_fields if field not in record or record[field] is None]
            if missing_fields:
                self.logger.warning(f"Missing required Silver fields: {missing_fields}")
                return False
        
        return True  # Simple validation - only checks required fields exist

    # ==================== HELPER METHODS ====================

    def _load_schemas(self):
        """Load schemas from the registry"""
        try:
            self.bronze_schema = self.schema_registry.load_bronze_schema(
                self.source, self.property_type
            )
            self.silver_schema = self.schema_registry.load_silver_schema(
                self.source, self.property_type
            )
            self.logger.info("Schemas loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Error loading schemas: {e}")
            raise

    # leave the remaining methods as stubs for future use
    def _calculate_data_quality_score(self, record: Dict) -> float:
        """Calculate the data quality score for a record"""
        pass

    def _generate_property_id(self, record: Dict) -> str:
        """Generate a unique property ID"""
        pass

    def _normalize_common_fields(self, record: Dict) -> Dict:
        """Normalize common fields (price, area, etc.)"""
        pass

    def get_processing_stats(self) -> Dict[str, Any]:
        """Retrieve processing statistics"""
        pass

    def _should_skip_record(self, record: Dict) -> bool:
        """Determine whether to skip a record"""
        pass