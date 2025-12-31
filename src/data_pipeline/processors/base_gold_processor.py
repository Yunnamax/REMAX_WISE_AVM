# src/data_pipeline/processors/silver_to_gold/base_gold_processor.py

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd
import logging
from datetime import datetime

class BaseGoldProcessor(ABC):
    """
    ABSTRACT BASE CLASS for Silver → Gold transformation.
    Handles multiple output files (master + details).
    """
    
    def __init__(self, schema_registry,  property_type: str):
        # Initialization
        self.schema_registry = schema_registry
        self.property_type = property_type
        self.logger = logging.getLogger(f"{property_type}_gold_processor")
        
        # Load Gold schemas 
        self.master_schema = None
        self.details_schema = None
        self._load_schemas()
        
        # Processing metrics
        self.processed_records = 0
        self.failed_records = 0
        self.processing_start_time = None
        
    # ==================== MAIN METHODS ====================
    
    def process_file(self, input_path: Path, output_dir: Path) -> bool: #change sigtanure after silvr layer refactoring and use instead of process_combined_data
        """
        Main method for Silver → Gold processing.
        Returns True if successful, False otherwise.
        """
        self.logger.info(f"Starting Gold processing: {input_path}")
        self.processing_start_time = datetime.now()
        
        try:
            # 1. EXTRACT from Silver (Parquet)
            silver_data = self._extract_data(input_path)
            if not silver_data:
                self.logger.warning(f"No data extracted from {input_path}")
                return False
            
            # 2. TRANSFORM to Gold format
            gold_data = self._transform_data(silver_data)
            if not gold_data:
                self.logger.warning(f"No data after transformation from {input_path}")
                return False
            
            # 3. VALIDATE against Gold schemas
            ##if not self._validate_data(gold_data):
                self.logger.error(f"Gold data validation failed for {input_path}")
                #return False
            
            # 4. SAVE to Gold layer
            self._save_data(gold_data, output_dir)
            
            # Update metrics
            self.processed_records = len(silver_data)
            
            processing_time = datetime.now() - self.processing_start_time
            self.logger.info(f"Successfully processed {len(silver_data)} records in {processing_time}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing {input_path}: {e}")
            self.failed_records += 1
            return False

    def process_combined_data(self, combined_df, master_path, details_path): 
        """
        Main method for Silver → Gold processing.
        Returns True if successful, False otherwise.
        """ 

        self.logger.info(f"Starting Gold processing: file")
        self.processing_start_time = datetime.now()

        try:
            # 1. TRANSFORM to Gold format
            gold_data = self._transform_data(combined_df)
            if not gold_data:
                self.logger.warning(f"No data after transformation from silver dataframe")
                return False
            
            # 2. VALIDATE against Gold schemas
            #if not self._validate_data(gold_data):
                #self.logger.error(f"Gold data validation failed for silver dataframe")
                #return False
            
            # 4. SAVE to Gold layer
            self._save_data(gold_data, master_path, details_path)

            return True
        except Exception as e:
            self.logger.error(f"Error: {e}")
            return False
                   
    # ==================== EXTRACTION ====================
    
    def _extract_data(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Extract data from Silver Parquet file.
        """
        try:
            df = pd.read_parquet(file_path)
            records = df.to_dict('records')
            self.logger.debug(f"Extracted {len(records)} records from {file_path}")
            return records
        except Exception as e:
            self.logger.error(f"Error extracting from {file_path}: {e}")
            return []
    
    # ==================== TRANSFORMATION (ABSTRACT) ====================
    
    @abstractmethod
    def _transform_data(self, silver_data: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """
        ABSTRACT METHOD: Transform Silver data to Gold format.
        Must return dictionary with 'master' and 'details' keys.
        Example: {'master': [...], 'details': [...]}
        """
        pass
    
    # ==================== VALIDATION ====================
    
    def _validate_data(self, gold_data: Dict[str, pd.DataFrame]) -> bool:
        """Validate both master and details DataFrames."""
        
        # Validate master
        if not self._validate_dataframe(
            gold_data.get('master'), 
            self.master_schema, 
            'master'
        ):
            return False
        
        # Validate details  
        if not self._validate_dataframe(
            gold_data.get('details'),
            self.details_schema,
            'details'
        ):
            return False
        
        return True


    def _validate_dataframe(self, df: pd.DataFrame, schema: Dict, name: str) -> bool:
        """Validate a single DataFrame against schema."""
        if df is None or df.empty:
            self.logger.warning(f"No {name} data to validate")
            return True  # или False, в зависимости от требований
        
        # Извлекаем обязательные поля из схемы
        required_fields = [
            field['name'] 
            for field in schema['fields'] 
            if field.get('required', False)
        ]
        
        # Проверяем наличие столбцов
        missing_columns = [
            field for field in required_fields 
            if field not in df.columns
        ]
        
        if missing_columns:
            self.logger.error(f"{name} DataFrame missing columns: {missing_columns}")
            return False
        
        return True
    
    
    # ==================== SAVING ====================
    
    def _save_data(self, gold_data: Dict[str, pd.DataFrame], 
                    master_path: Path, details_path: Path):
        """Save DataFrames directly to given paths."""
        gold_data['master'].to_parquet(master_path)
        gold_data['details'].to_parquet(details_path)
        
    # ==================== SCHEMA LOADING ====================
    
    def _load_schemas(self):
            """Load Gold schemas from registry."""
            try:
                # Master schema is the same for all property types
                self.master_schema = self.schema_registry.load_gold_schema('master_properties')
                
                # Details schema is specific to property type
                self.details_schema = self.schema_registry.load_gold_schema(
                    f'{self.property_type}_details'
                )
                
                self.logger.info(f"Loaded Gold schemas: master and {self.property_type}_details")
                
            except Exception as e:
                self.logger.error(f"Error loading Gold schemas: {e}")
                # If schemas don't exist, we can't proceed
                raise
    
    # ==================== UTILITY METHODS ====================
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return {
            'processed_records': self.processed_records,
            'failed_records': self.failed_records,
            'processing_time': str(datetime.now() - self.processing_start_time) 
                if self.processing_start_time else None,
            'source': self.source,
            'property_type': self.property_type
        }
    
    def _generate_property_id(self, silver_record: Dict) -> str:
        """
        Generate property ID for Gold layer.
        Can be overridden if different from Silver.
        """
        # Default: use existing property_id from Silver
        return silver_record.get('property_id')