from pathlib import Path
from typing import List, Dict, Optional
import logging
from datetime import datetime
import pandas as pd
import time
import sys
from typing import List, Dict, Optional, Tuple
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT))
from .processors.base_gold_processor import BaseGoldProcessor
from .processors.silver_to_gold.apartments_rent_processor import ApartmentRentProcessor
from .processors.schema_registry import SchemaRegistry
from .pipeline_metrics import PipelineMetrics
from .idempotency_tracker import FileSystemTracker

class SilverToGoldCoordinator:
    """
    Coordinator for automated processing of data from the Silver layer to the Gold layer.
    Responsible for detecting, routing, processing and enreaching silver data.
    """

    def __init__(
        self,
        project_root: Path,
        supported_sources: Optional[List[str]] = None,
        silver_base_path: str = "data/silver",
        gold_base_path: str = "data/gold"
    ):
        self.project_root = Path(project_root)
        self.silver_base_path = self.project_root / silver_base_path
        self.gold_base_path = self.project_root / gold_base_path
        self.schema_registry = SchemaRegistry(project_root=self.project_root)
        self.logger = self._setup_logger()   

    def _setup_logger(self):
        """logging configuration for the coordinator"""
        logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        # TODO: logging configuration will be here
        return logger 
    
    def discover_silver_files(
        self,
        file_pattern: str = "processed_data.parquet"
    ) -> List[Dict[str, str]]:
        """
        Recursively discovers all  files in the Silver layer.
        
        Args:
            file_pattern: filename pattern to search for
            
        Returns:
            List of dictionaries with information about discovered files
        """
        # Step 1: Initialize an empty list for results
        discovered_files = []
        
        # Step 2: Log the start of the operation
        self.logger.info(f"Starting silver files discovery in: {self.silver_base_path}")
        self.logger.info(f"File pattern: {file_pattern}")
        
        # Step 3: Check if the Silver base directory exists
        if not self.silver_base_path.exists():
            error_msg = f"Silver directory does not exist: {self.silver_base_path}"
            self.logger.error(error_msg)
            # Could also raise an exception, but for now return an empty list
            return discovered_files
        
        # Step 4: Check that silver_base_path is a directory
        if not self.silver_base_path.is_dir():
            error_msg = f"Silver path is not a directory: {self.silver_base_path}"
            self.logger.error(error_msg)
            return discovered_files
        
        # Step 5: Log successful start of search
        self.logger.debug("Silver directory validation passed, starting file search...")

        # Step 6: Recursive file search by pattern
        try:
            # rglob recursively searches for all files matching the pattern
            found_files = list(self.silver_base_path.rglob(file_pattern))
            self.logger.info(f"Found {len(found_files)} files matching pattern '{file_pattern}'")
            
            # Process each found file
            for file_path in found_files:
                self.logger.debug(f"Processing file: {file_path}")
                
                # Extract metadata from the path structure
                metadata = self._parse_silver_path(file_path)  
                
                # If metadata is successfully extracted and the source is supported
                if metadata:
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

    def _parse_silver_path(self, file_path: Path) -> Optional[Dict[str, str]]: # TODO: rewrite after silver layer refactoring
        """
        Extracts metadata from the Silver layer path structure.
        """
        try:
            # Get the relative path from bronze_base_path
            relative_path = file_path.relative_to(self.silver_base_path)
            parts = relative_path.parts  # Break path into parts
            
            # Expected structure: source/property_type/municipality=xxx/date=xxx/file
            if len(parts) >= 3:
                property_type = parts[0]  # land
                municipality = parts[1].replace('municipality=', '') # lisbon
                date = parts[2].replace('date=', '')  # 2025-11-14
                
                return {
                    'silver_path': str(file_path),
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
    
    def _get_processor(self, property_type: str) -> BaseGoldProcessor:
        """Returns the appropriate processor for property_type"""
        mapping = {
            'apartment_rent': ApartmentRentProcessor,
            # Will add leter:
            # 'land': LandProcessor,
            # 'commercial': CommercialProcessor,
        }
        processor_class = mapping.get(property_type)
        if processor_class:
            return processor_class(
                schema_registry=self.schema_registry,
                property_type=property_type
            )
        return None

    def _group_files_by_date_and_type(self, discovered_files: List[Dict]) -> Dict[Tuple[str, str], List[Dict]]:# rewrite after silver layer refactoring
        """
        Groups files by date and property type.
        
        Args:
            discovered_files: List of metadata of Silver layer files
            
        Returns:
            A dictionary where the key is a tuple (date, property_type), 
            and the value is a list of metadata of files in that group
        """
        grouped_files = {}
        
        for file_metadata in discovered_files:
            key = (file_metadata['date'], file_metadata['property_type'])
            
            if key not in grouped_files:
                grouped_files[key] = []
            
            grouped_files[key].append(file_metadata)
        
        # Log the grouping results
        self.logger.info(f"Grouped {len(discovered_files)} files into {len(grouped_files)} groups:")
        for (date, property_type), files in grouped_files.items():
            self.logger.info(f"  Group ({date}, {property_type}): {len(files)} files")
        
        return grouped_files   

    def _process_combined_file(self, file_group: List[Dict], date: str, property_type: str) -> Dict: # rewrite to process single file after silver layer refactoring
        """
        Combines and processes a group of files in a single call.
        """
        try:
            # 1. Get processor
            processor = self._get_processor(property_type)
            
            if not processor:
                error_msg = f"No processor found for {property_type}"
                self.logger.error(error_msg)
                return {
                    'status': 'error',
                    'error': error_msg,
                    'date': date,
                    'property_type': property_type
                }
            
            # 2. Generate paths
            master_output_path = self._generate_master_path(date)
            details_output_path = self._generate_details_path(property_type, date)
            master_output_path.parent.mkdir(parents=True, exist_ok=True)
            details_output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 3. COMBINE all files in the group right here
            combined_df = None
            for file_meta in file_group:
                file_path = Path(file_meta['silver_path'])
                df = pd.read_parquet(file_path)
                
                if combined_df is None:
                    combined_df = df
                else:
                    combined_df = pd.concat([combined_df, df], ignore_index=True)
            
            if combined_df is None or len(combined_df) == 0:
                return {
                    'status': 'error',
                    'error': "No data after combining files",
                    'date': date,
                    'property_type': property_type
                }
            
            # 4. Process the combined data
            success = processor.process_combined_data(
                combined_df=combined_df,
                master_path=master_output_path,
                details_path=details_output_path
            )
            
            # 5. Return result
            return {
                'status': 'success' if success else 'error',
                'date': date,
                'property_type': property_type,
                'records_processed': len(combined_df),
                'master_output_path': str(master_output_path),
                'details_output_path': str(details_output_path)
            }
            
        except Exception as e:
            error_msg = f"Error processing group ({date}, {property_type}): {e}"
            self.logger.error(error_msg)
            return {
                'status': 'error',
                'error': error_msg,
                'date': date,
                'property_type': property_type
            }

    def process_all_files(self) -> List[Dict]:
            """Main method that launches the entire process with GROUP processing"""
            metrics = PipelineMetrics()
            metrics.start_pipeline()
            
            # tracker initialization – now at the group level
            tracker = FileSystemTracker()
            
            discovered_files = self.discover_silver_files()
            
            # Group files by date and property type
            grouped_files = self._group_files_by_date_and_type(discovered_files)
            
            # Set metrics: number of groups instead of number of files
            metrics.set_total_files(len(grouped_files))
            processing_results = []
            
            # Process each group
            for (date, property_type), file_group in grouped_files.items():
                # Create a unique group key for idempotency tracking
                group_key = f"{date}_{property_type}"
                group_path = Path(group_key)
                group_start = time.time()
                
                # Idempotency check at the GROUP level
                #  TODO implement idempotency later
                """
                if not tracker.should_process(group_path):
                    self.logger.info(f"Group already processed: {group_key}")
                    continue
                
                self.logger.info(f"Processing group: {group_key} ({len(file_group)} files)")
                """
                
                try:
                    # Process the entire group of files
                    result = self._process_combined_file(file_group, date, property_type)
                    processing_results.append(result)
                    
                    # Mark group as successfully processed
                    #tracker.mark_processed(group_path, "")
                    
                except Exception as e:
                    # Mark group as failed
                    #tracker.mark_failed(group_path, "", str(e))
                    processing_results.append({
                        'group_key': group_key,
                        'status': 'error',
                        'message': str(e),
                        'file_count': len(file_group),
                        'date': date,
                        'property_type': property_type
                    })
                    result = {'status': 'error'}  # For metrics
                
                group_time = time.time() - group_start
                # Record result in metrics
                metrics.record_file_result(
                    success=(result.get('status') == 'success'),
                    processing_time=group_time
                )
            
            metrics.end_pipeline()
            summary = metrics.get_summary()
            self.logger.info(f"PIPELINE EXECUTION SUMMARY: {summary}")
            return processing_results
  
    def _generate_master_path(self, date: str) -> Path:
        """Path for the master table (all property types)"""
        return self.gold_base_path / "master" / f"date={date}" / "master_table.parquet"
        
    def _generate_details_path(self, property_type: str, date: str) -> Path:
        """Path for the detailed table (specific property type)"""
        return self.gold_base_path / property_type / f"date={date}" / f"{property_type}_details.parquet"