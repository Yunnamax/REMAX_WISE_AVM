# processors/schema_registry.py
from pathlib import Path  
from typing import Dict, Any
import yaml
import logging
class SchemaRegistry:
    """
    CENTRAL SCHEMA REGISTRY - MAIN LOGIC:

    1. SINGLE ACCESS POINT ( all system components request schemas from here )
    2. CACHING  ( schemas are loaded once and cached in memory )
    3. AUTOMATIC PATH RESOLUTION
    4. VALIDATION INTERFACE
    """
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.schemas_base = project_root / "config" / "schemas"
        self._cache = {}  # cash - prevents multiple file uploads
        
    def load_bronze_schema(self, source: str, property_type: str) -> Dict:

        schema_key = f"bronze_{source}_{property_type}"
        
        if schema_key not in self._cache:
            #  automatic path rezolution
            schema_path = self.schemas_base / "bronze" / source / f"{property_type}_property.yaml"
            self._cache[schema_key] = self._load_schema_file(schema_path)
            
        return self._cache[schema_key]
    
    def load_silver_schema(self, source: str, property_type: str) -> Dict:

        schema_key = f"silver_{source}_{property_type}"
        
        if schema_key not in self._cache:
            schema_path = self.schemas_base / "silver" / f"{property_type}_property.yaml"
            self._cache[schema_key] = self._load_schema_file(schema_path)
            
        return self._cache[schema_key]

    def _load_schema_file(self, schema_path: Path) -> Dict:
  
        try:
            with open(schema_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            raise Exception(f"Failed to load schema from {schema_path}: {e}")
    
