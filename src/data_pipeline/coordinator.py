from pathlib import Path
from typing import List, Dict, Optional
import logging
from datetime import datetime
import time
import sys
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT))
from .processors.base_processor import BaseProcessor
from .processors.idealista.land_processor import IdealistaLandProcessor
from .processors.schema_registry import SchemaRegistry
from .pipeline_metrics import PipelineMetrics
from .idempotency_tracker import FileSystemTracker

class BronzeToSilverCoordinator:
    """
    Coordinator for automated processing of data from the Bronze layer to the Silver layer.
    Responsible for detecting, routing, and processing raw data.
    """

    def __init__(
        self,
        project_root: Path,
        supported_sources: Optional[List[str]] = None,
        bronze_base_path: str = "data/bronze",
        silver_base_path: str = "data/silver"
    ):
        self.project_root = Path(project_root)
        self.supported_sources = supported_sources or ["idealista"]  #idealista by default
        self.bronze_base_path = self.project_root / bronze_base_path
        self.silver_base_path = self.project_root / silver_base_path
        self.schema_registry = SchemaRegistry(project_root=self.project_root)
        self.logger = self._setup_logger()

    def _setup_logger(self):
        """logging configuration for the coordinator"""
        logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        # logging configuration will be here
        return logger    

    def discover_bronze_files(
        self,
        file_pattern: str = "raw_data.json"
    ) -> List[Dict[str, str]]:
        """
        Recursively discovers all raw files in the Bronze layer.
        
        Args:
            file_pattern: filename pattern to search for
            
        Returns:
            List of dictionaries with information about discovered files
        """
        # Step 1: Initialize an empty list for results
        discovered_files = []
        
        # Step 2: Log the start of the operation
        self.logger.info(f"Starting bronze files discovery in: {self.bronze_base_path}")
        self.logger.info(f"File pattern: {file_pattern}")
        self.logger.info(f"Supported sources: {self.supported_sources}")
        
        # Step 3: Check if the Bronze base directory exists
        if not self.bronze_base_path.exists():
            error_msg = f"Bronze directory does not exist: {self.bronze_base_path}"
            self.logger.error(error_msg)
            # Could also raise an exception, but for now return an empty list
            return discovered_files
        
        # Step 4: Check that bronze_base_path is a directory
        if not self.bronze_base_path.is_dir():
            error_msg = f"Bronze path is not a directory: {self.bronze_base_path}"
            self.logger.error(error_msg)
            return discovered_files
        
        # Step 5: Log successful start of search
        self.logger.debug("Bronze directory validation passed, starting file search...")

        # Step 6: Recursive file search by pattern
        try:
            # rglob recursively searches for all files matching the pattern
            found_files = list(self.bronze_base_path.rglob(file_pattern))
            self.logger.info(f"Found {len(found_files)} files matching pattern '{file_pattern}'")
            
            # Process each found file
            for file_path in found_files:
                self.logger.debug(f"Processing file: {file_path}")
                
                # Extract metadata from the path structure
                metadata = self._parse_bronze_path(file_path)
                
                # If metadata is successfully extracted and the source is supported
                if metadata and self._is_supported_source(metadata['source']):
                    discovered_files.append(metadata)
                    self.logger.debug(f"Added to processing list: {metadata}")
                elif metadata:
                    self.logger.debug(f"Skipping unsupported source: {metadata['source']}")
                else:
                    self.logger.warning(f"Could not parse metadata from path: {file_path}")
                    
        except Exception as e:
            self.logger.error(f"Error during file discovery: {e}")
            # More specific error handling could be added here

        # Step 7: Final logging of results
        self.logger.info(f"Discovery completed. Total files to process: {len(discovered_files)}")
        
        # [Continuation here - recursive file search]
        
        return discovered_files
    
    def _parse_bronze_path(self, file_path: Path) -> Optional[Dict[str, str]]:
        """
        Extracts metadata from the Bronze layer path structure.
        """
        try:
            # Get the relative path from bronze_base_path
            relative_path = file_path.relative_to(self.bronze_base_path)
            parts = relative_path.parts  # Разбиваем путь на части
            
            # Expected structure: source/property_type/municipality=xxx/date=xxx/file
            if len(parts) >= 4:
                source = parts[0]  # idealista
                property_type = parts[1]  # land
                municipality = parts[2].replace('municipality=', '')  # lisboa
                date = parts[3].replace('date=', '')  # 2025-11-14
                
                return {
                    'bronze_path': str(file_path),
                    'source': source,
                    'property_type': property_type,
                    'municipality': municipality,
                    'date': date
                }
            else:
                self.logger.warning(f"Unexpected path structure: {file_path}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error parsing path {file_path}: {e}")
            return None
        
    def _is_supported_source(self, source: str) -> bool:
        """Checks if the data source is supported"""
        return source in self.supported_sources   

    def _get_processor(self, source: str, property_type: str) -> BaseProcessor:
        """Returns the appropriate processor for source/property_type"""
        mapping = {
            ('idealista', 'land'): IdealistaLandProcessor,
            # Add new combinations here
        }
        processor_class = mapping.get((source, property_type))
        if processor_class:
            return processor_class(
                schema_registry=self.schema_registry,
                source=source,
                property_type=property_type
            )
        return None 
    
    def _process_single_file(self, metadata: Dict) -> Dict:
        """Processes a single file from start to finish"""
        # 1. Get the INITIALIZED processor (already ready to work)
        processor = self._get_processor(metadata['source'], metadata['property_type'])
        
        if not processor:
            return {
                'status': 'error',
                'error': f"No processor found for {metadata['source']}/{metadata['property_type']}",
                'metadata': metadata
            }
        
        # 2. Generate paths
        input_path = Path(metadata['bronze_path'])  # Where to get the data from
        output_path = self._generate_silver_path(metadata)  # Where to save the data
        output_path.parent.mkdir(parents=True, exist_ok=True) # if already exists
        
        # 3. CALL the main processor method
        success = processor.process_file(input_path, output_path)
        
        # 4. Return the processing result
        return {
            'status': 'success' if success else 'error',
            'input_path': input_path,
            'output_path': output_path,
            'metadata': metadata
        }
    
    def process_all_files(self) -> List[Dict]:
        """Main method that launches the entire process"""
        metrics = PipelineMetrics()
        metrics.start_pipeline()
        
        # tracer initialization
        tracker = FileSystemTracker()
        
        discovered_files = self.discover_bronze_files()
        metrics.set_total_files(len(discovered_files))
        processing_results = []
        
        for metadata in discovered_files:
            #bronze_path = metadata['bronze_path']
            bronze_path = Path(metadata['bronze_path'])
            
            # Idempotency check BEFORE processing
            if not tracker.should_process(bronze_path):
                print(f"file is already processed: {metadata['bronze_path']}")
                continue
            
            self.logger.info(f"Processing: {bronze_path}")
            file_start = time.time()
            
            try:
                # Process a single file
                result = self._process_single_file(metadata)
                processing_results.append(result)
                
                # MARK SUCCESS
                tracker.mark_processed(bronze_path, "")
                
            except Exception as e:
                # MARK FAILURE  
                tracker.mark_failed(bronze_path, "", str(e))
                processing_results.append({
                    'file_path': str(bronze_path),
                    'status': 'error',
                    'message': str(e)
                })
            
            file_time = time.time() - file_start
            metrics.record_file_result(
                success=(result['status'] == 'success'),
                processing_time=file_time
            )

        metrics.end_pipeline()
        summary = metrics.get_summary()
        self.logger.info(f"PIPELINE EXECUTION SUMMARY: {summary}")
        return processing_results
    
    def _generate_silver_path(self, metadata: Dict) -> Path:
        """Generates peth to Silver layer"""
        return (
            self.silver_base_path / 
            metadata['source'] / 
            metadata['property_type'] / 
            f"municipality={metadata['municipality']}" / 
            f"date={metadata['date']}" / 
            "processed_data.parquet"
        )
    
