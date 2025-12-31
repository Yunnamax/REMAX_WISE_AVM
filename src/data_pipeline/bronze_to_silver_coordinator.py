from pathlib import Path
from typing import List, Dict, Optional
import logging
from datetime import datetime
import time
import sys
import re
import yaml
import importlib
import pandas as pd
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT))
from .processors.base_processor import BaseProcessor
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
    
    def parse_bronze_path(file_path, bronze_root, config_dir):
        try:
            # 1. Relative path
            relative = file_path.relative_to(bronze_root)
            parts = relative.parts
            
            # 2. Loading common.yaml
            common_path = config_dir / "bronze" / "common.yaml"
            with open(common_path) as f:
                common = yaml.safe_load(f)
            
            # 3. Extract source  (first part of the path)
            source_pos = common["source_detection"]["position"]
            source = parts[source_pos]
            
            # 4. Determine source type
            source_type = common["source_type_mapping"][source]
            
            # 5. Loading config file for the type
            type_path = config_dir / "bronze" / f"{source_type}.yaml"
            with open(type_path) as f:
                type_config = yaml.safe_load(f)
            
            # 6. Extricting metadata by components
            metadata = {}
            for comp in type_config["components"]:
                pos = comp["position"]
                name = comp["name"]
                value = parts[pos]
                
                if "prefix" in comp and value.startswith(comp["prefix"]):
                    value = value[len(comp["prefix"]):]
                
                metadata[name] = value
            
            # 7. Adding service fields
            metadata["bronze_path"] = str(file_path)
            metadata["source"] = source
            
            return metadata
            
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None
        
    def _is_supported_source(self, source: str) -> bool:
        """Checks if the data source is supported"""
        return source in self.supported_sources   
    
    #TODO refactor method (create data class and change returnung value type):
    def _group_metadata_by_source_config(
        self,
        metadata_list: List[Dict],
        config_dir: Path = None
    ) -> Dict[tuple, tuple[List[Dict], List[str]]]:
        """
        Groups metadata by keys defined in the source type configuration.
        
        Args:
            metadata_list: List of file metadata dictionaries
            config_dir: Path to the configuration directory
            
        Returns:
            Dictionary where:
            - Key: tuple of grouping parameters (group_key)
            - Value: tuple containing two lists:
                [0]: List of original metadata dictionaries (not modified)
                [1]: List of processor key NAMES (e.g., ['source', 'property_type'])
                    These are the field names to use when building processor keys later
        """
        if config_dir is None:
            config_dir = self.project_root / "configs"

        # Load common.yaml to map source -> source_type
        common_path = config_dir / "bronze" / "common.yaml"
        with open(common_path, 'r') as f:
            common_config = yaml.safe_load(f)

        source_type_mapping = common_config.get('source_type_mapping', {})
        grouped_data = {}
        
        # Cache for source type configurations to avoid reading files multiple times
        source_type_config_cache = {}

        for metadata in metadata_list:
            # Extract source from metadata
            source = metadata.get('source')
            if not source:
                self.logger.warning(f"Metadata does not contain source: {metadata}")
                continue

            # Determine source type
            source_type = source_type_mapping.get(source)
            if not source_type:
                self.logger.warning(f"Unknown source {source}, skipping")
                continue

            # Load configuration for this source type ( with cacheing)
            if source_type not in source_type_config_cache:
                source_type_config_path = config_dir / "bronze" / f"{source_type}.yaml"
                if not source_type_config_path.exists():
                    self.logger.warning(f"Config for {source_type} not found, skipping")
                    continue
                
                with open(source_type_config_path, 'r') as f:
                    source_type_config_cache[source_type] = yaml.safe_load(f)
            
            source_type_config = source_type_config_cache[source_type]

            # Get grouping keys (for combining files in Silver)
            grouping_keys = source_type_config.get('grouping_keys', [])
            if not grouping_keys:
                # By default, group only by date
                grouping_keys = ['date']

            # Get processor selection key NAMES (not values!)
            processor_key_names = source_type_config.get('processor_keys', [])
            if not processor_key_names:
                # Default processor keys for backward compatibility
                processor_key_names = ['source', 'property_type']

            # Build grouping key (for combining files into one DataFrame)
            group_key_parts = [source_type]
            for key in grouping_keys:
                value = metadata.get(key)
                if value is not None:
                    group_key_parts.append(value)
                else:
                    # If the key is missing, use 'unknown' and log a warning
                    self.logger.warning(
                        f"Grouping key {key} is missing in metadata for source {source}"
                    )
                    group_key_parts.append('unknown')

            group_key = tuple(group_key_parts)
            
            # Initialize group entry if it doesn't exist
            if group_key not in grouped_data:
                # СОХРАНЯЕМ ТОЛЬКО НАЗВАНИЯ КЛЮЧЕЙ, не готовые ключи!
                grouped_data[group_key] = ([], processor_key_names)  # Изменено здесь!
            
            # Add the original metadata to the group
            # Metadata is NOT modified (no '_processor_key' added)
            grouped_data[group_key][0].append(metadata)  # Add to metadata list

        # Log summary of grouping results
        self.logger.info(
            f"Grouping completed. Created {len(grouped_data)} groups "
            f"from {len(metadata_list)} files."
        )
        
        return grouped_data

    def _get_processor(self, metadata: Dict, processor_key_names: List[str]) -> BaseProcessor:
        """
        Returns the appropriate processor by dynamically loading it from configuration.
        
        This method dynamically builds a processor key using values from metadata
        according to the specified processor_key_names, then loads the corresponding
        processor class from the processor_mapping.yaml configuration.
        
        Args:
            metadata: File metadata dictionary containing all extracted fields
            processor_key_names: List of key names to use for building the processor key
                            (e.g., ['source', 'property_type'])
        
        Returns:
            Processor instance initialized with required parameters, or None if not found
        
        Example:
            metadata = {'source': 'idealista', 'property_type': 'apartment_rent', ...}
            processor_key_names = ['source', 'property_type']
            
            Processor key will be: 'idealista.apartment_rent'
            Configuration lookup in processor_mapping.yaml under 'processors' section
        
        Raises:
            Logs warnings for missing keys in metadata
            Logs errors for import failures
        """
        # 1. Determine the path to the config (same as in parse_bronze_path)
        config_dir = self.project_root / "configs"
        mapping_path = config_dir / "processor_mapping.yaml"
        
        # 2. Load the config (same as in parse_bronze_path)
        with open(mapping_path) as f:
            processor_config = yaml.safe_load(f)
        
        # 3. Dynamically build processor key from metadata using processor_key_names
        key_parts = []
        
        for key_name in processor_key_names:
            value = metadata.get(key_name)
            
            if value is not None:
                key_parts.append(str(value))
            else:
                # If the key is missing, use 'unknown' and log a warning
                self.logger.warning(
                    f"Processor key '{key_name}' is missing in metadata for file: "
                    f"{metadata.get('bronze_path', 'unknown')}. Using 'unknown' as fallback."
                )
                key_parts.append('unknown')
        
        processor_key = '.'.join(key_parts)
        
        # 4. Look up the processor in config
        if processor_key not in processor_config.get("processors", {}):
            self.logger.warning(f"No processor mapping found for key: {processor_key}")
            return None
        
        # 5. Dynamically import the class
        module_path = processor_config["processors"][processor_key]["module"]
        class_name = processor_config["processors"][processor_key]["class"]
        
        try:
            module = importlib.import_module(module_path)
            processor_class = getattr(module, class_name)
            
            # 6. Extract required parameters for processor initialization
            # We preserve the same interface for backward compatibility
            source = metadata.get('source', 'unknown')
            property_type = metadata.get('property_type', 'unknown')
            
            # 7. Create an instance with required parameters
            return processor_class(
                schema_registry=self.schema_registry,
                source=source,
                property_type=property_type
            )
            
        except (ImportError, AttributeError) as e:
            self.logger.error(f"Failed to load processor for key {processor_key}: {e}")
            return None


    def _process_group_of_files(self, metadata_list: List[Dict], processor_key_names: List[str], group_key: tuple) -> Dict:
        """
        Processes a group of files by combining them into a single DataFrame.
        
        Args:
            metadata_list: List of file metadata to be combined
            group_key: Group key (e.g., ('real_estate_portal', 'apartment_rent', '2025-01-15'))
        
        Returns:
            Dictionary with the results of group processing
        """
        if not metadata_list:
            return {
                'status': 'empty_group',
                'group_key': str(group_key),
                'message': 'Group is empty'
            }
        
        all_dataframes = []
        processed_files = 0
        failed_files = 0
        
        # 1. Process each file in the group
        for metadata in metadata_list:
            try:
                # Get the processor for this file
                processor = self._get_processor(
                    metadata=metadata,
                   processor_key_names=processor_key_names,
                   group_key=group_key
                )
                
                if processor is None:
                    self.logger.warning(f"No processor for {metadata['source']}/{metadata['property_type']}")
                    failed_files += 1
                    continue
                
                # The processor should return a DataFrame (new method)
                input_path = Path(metadata['bronze_path'])
                df = processor.process_file(input_path)
                
                # Add source as a column to track the data origin
                df['source'] = metadata['source']
                
                all_dataframes.append(df)
                processed_files += 1
                
            except Exception as e:
                self.logger.error(f"Error processing {metadata['bronze_path']}: {e}")
                failed_files += 1
        
        # 2. Check if there are any successfully processed files
        if not all_dataframes:
            return {
                'status': 'error',
                'group_key': str(group_key),
                'error': f'All files in the group failed to process. Successful: 0, Failed: {failed_files}'
            }
        
        # 3. Combine all DataFrames
        try:
            combined_df = pd.concat(all_dataframes, ignore_index=True)
            
            # Optional: deduplication at the group level
            # combined_df = combined_df.drop_duplicates(subset=['id', 'source']) if an ID exists
            
        except Exception as e:
            return {
                'status': 'error',
                'group_key': str(group_key),
                'error': f'Error while combining data: {e}'
            }
        
        # 4. Generate output path and save
        try:
            output_path = self._generate_silver_path_for_group(group_key, metadata_list)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save the combined DataFrame
            combined_df.to_parquet(output_path)
            
        except Exception as e:
            return {
                'status': 'error',
                'group_key': str(group_key),
                'error': f'Error while saving: {e}'
            }
        
        # 5. Return the result
        return {
            'status': 'success',
            'group_key': str(group_key),
            'files_processed': processed_files,
            'files_failed': failed_files,
            'total_rows': len(combined_df),
            'output_path': str(output_path),
            'sources': list(set(m['source'] for m in metadata_list))
        }
    
    def process_all_files(self) -> List[Dict]:
        """Main method that launches the entire process"""
        metrics = PipelineMetrics()
        metrics.start_pipeline()
        
        # Initialize filesystem tracker
        tracker = FileSystemTracker()
        
        # 1. Retrieve a flat list of metadata
        metadata_list = self.discover_bronze_files()
        
        # 2. Group metadata according to source configuration
        grouped_files = self._group_metadata_by_source_config(metadata_list)
        
        # 3. Count the total number of files across all groups
        total_files = sum(len(group) for group in grouped_files.values())
        metrics.set_total_files(total_files)
        
        processing_results = []
        
        # 4. Process each group
        for group_key, (metadata_list_in_group, processor_key_names) in grouped_files.items():
            self.logger.info(
                f"Processing group {group_key} with {len(metadata_list_in_group)} files"
                f"Processor keys: {processor_key_names}"
                )
            
            # 5. Check idempotency for ALL files in the group
            should_process_group = True
            for metadata in metadata_list_in_group:
                bronze_path = Path(metadata['bronze_path'])
                if not tracker.should_process(bronze_path):
                    self.logger.info(f"Skipping group {group_key}: file {bronze_path} already processed")
                    should_process_group = False
                    break
            
            if not should_process_group:
                continue
            
            # 6. Start processing the group
            group_start = time.time()
            
            try:
                # 7. Process the ENTIRE GROUP in a single call
                result = self._process_group_of_files(metadata_list_in_group, processor_key_names, group_key)
                processing_results.append(result)
                
                # 8. Mark ALL files in the group as processed
                for metadata in metadata_list_in_group:
                    bronze_path = Path(metadata['bronze_path'])
                    tracker.mark_processed(bronze_path, "")
                
                group_status = 'success'
                
            except Exception as e:
                self.logger.error(f"Error processing group {group_key}: {e}")
                
                # 9. In case of error, mark ALL files in the group as failed
                for metadata in metadata_list_in_group:
                    bronze_path = Path(metadata['bronze_path'])
                    tracker.mark_failed(bronze_path, "", str(e))
                
                result = {
                    'group_key': str(group_key),
                    'status': 'error',
                    'error': str(e),
                    'file_count': len(metadata_list_in_group)
                }
                processing_results.append(result)
                group_status = 'error'
            
            # 10. Record metrics for the group
            group_time = time.time() - group_start
            metrics.record_file_result(
                success=(group_status == 'success'),
                processing_time=group_time
            )
            # If group-level metrics are required:
            # metrics.record_group_result(group_key, len(metadata_list_in_group), group_status == 'success', group_time)
        
        metrics.end_pipeline()
        summary = metrics.get_summary()
        self.logger.info(f"PIPELINE EXECUTION SUMMARY: {summary}")
        return processing_results
    
    def _generate_silver_path(self, metadata: Dict) -> Path:
        """Generates peth to Silver layer"""
        return (
            self.silver_base_path / 
            metadata['property_type'] / 
            f"municipality={metadata['municipality']}" / 
            f"date={metadata['date']}" / 
            "processed_data.parquet"
        )
    
