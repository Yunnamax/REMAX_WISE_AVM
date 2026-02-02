from pathlib import Path
import os
from abc import ABC, abstractmethod
from datetime import datetime
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

class BaseScraper(ABC):
    """
    ABSTRACT BASE CLASS for all scrapers.
    Implements the Template Method pattern.
    """
    
    def __init__(self, source_name: str, **context_kwargs):
        """
        Initialize the common state of the scraper.
        """
        # IDENTIFICATION (for the orchestrator)
        self.source_name = source_name      # "idealista", "architizer"
        self.context = context_kwargs   
        self.scraper_id = self._generate_scraper_id()
        
        # State Pattern
        self.status = "READY"  # READY, RUNNING, COMPLETED, FAILED, MANUAL_PENDING
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.records_collected = 0
        
        # Results and errors
        self.last_successful_run: Optional[datetime] = None
        self.error_message: Optional[str] = None
        self.collected_data: List[Dict] = []
        
        # Infrastructure
        self.config = self._load_scraper_config()  # Strategy Pattern
        self.logger = self._setup_logging()        # Observer Pattern

        self.project_root = self._find_project_root()

    @property
    @abstractmethod
    def source_type(self) -> str:
        pass

    def _find_project_root(self) -> Path:
        """Finds the root project directory (where data/ is located)."""
        current_file = Path(__file__).resolve() 

        for parent in current_file.parents:
            if (parent / 'data').exists():
                return parent

        return Path.cwd()

    # PUBLIC INTERFACE (for the orchestrator) ===
    
    def run(self) -> List[Dict]:
        """
        MAIN METHOD – Entry point for the orchestrator.
        
        Theory: Facade Pattern – provides a simple interface
        to a complex subsystem (the entire scraping process).
        """
        # 3.1 PREPARATION
        self.status = "RUNNING"
        self.start_time = datetime.now()
        self.error_message = None
        
        try:
            self.logger.info(f"Starting scraper: {self.scraper_id}")
            
            # 3.2 EXECUTION (abstract method – implemented in subclasses)
            self.collected_data = self._execute_scraping()
            self.records_collected = len(self.collected_data)
            
            # 3.3 SAVE RESULTS
            if self.collected_data:
                output_path = self._generate_output_path()
                self._save_to_bronze(output_path)
                self.last_successful_run = datetime.now()
            
            # 3.4 SUCCESSFUL COMPLETION
            self.status = "COMPLETED"
            self.logger.info(f"Scraper completed: {self.records_collected} records")
            
        except Exception as e:
            # 3.5 ERROR HANDLING
            self.status = "FAILED"
            self.error_message = str(e)
            self.logger.error(f"Scraper failed: {str(e)}")
            raise
        
        finally:
            # 3.6 FINALIZATION (always executed)
            self.end_time = datetime.now()
            
        return self.collected_data

    def get_status(self) -> Dict[str, Any]:
        """
        MONITORING METHOD – returns the current scraper state.
        
        Theory: Memento Pattern – provides a snapshot of the object's
        state without exposing its internal implementation.
        """
        duration = None
        if self.start_time and self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()
        elif self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds()
            
        return {
            "scraper_id": self.scraper_id,
            "status": self.status,
            "records_collected": self.records_collected,
            "duration_seconds": duration,
            "last_successful_run": self.last_successful_run,
            "error_message": self.error_message,
            "timestamp": datetime.now().isoformat()
        }
    
    def is_healthy(self) -> bool:
        """Checks whether the scraper is ready to run."""
        return self.status in ["READY", "COMPLETED"]
    
    def needs_to_run(self) -> bool:
        """Determines whether the scraper should run based on schedule."""
        if not self.last_successful_run:
            return True
            
        update_frequency = self.config.get('update_frequency_hours', 24)
        time_since_last_run = (datetime.now() - self.last_successful_run).total_seconds() / 3600
        return time_since_last_run >= update_frequency

    # ABSTRACT METHODS (contract for subclasses) ===       
    
    @abstractmethod
    def _execute_scraping(self) -> List[Dict]:
        """
        ABSTRACT METHOD – must be implemented in each subclass.
        
        Theory: Strategy Pattern – each scraping strategy
        implements this method in its own way.
        """
        pass
    
    @abstractmethod
    def get_scraping_instructions(self) -> Dict[str, Any]:
        """
        ABSTRACT METHOD – instructions for manual scraping.
        
        Theory: Command Pattern – encapsulates a request as an object,
        allowing clients to parameterize with different requests.
        """
        pass

    # HELPER METHODS (common logic) ===
    def _generate_scraper_id(self):
        """Generates an ID based on source_name and key context parameters"""
        parts = [self.source_name]

        # For backward compatibility, key parameters can be added
        # But now this is optional
        key_params = ['property_type', 'municipality', 'layer_type', 'data_type']
        for key in key_params:
            if key in self.context:
                parts.append(str(self.context[key]))

        return '_'.join(parts)
    
    def _generate_output_path(self) -> Path:
        """
        Generates a path for saving.
        BASE METHOD - can be overridden in child classes.
        """
        date = datetime.now().strftime('%Y-%m-%d')

        # 1. Base path (unchanging for all scrapers)
        path_parts = [
            self.project_root,
            "data",
            "bronze",
            self.source_name,
        ]

        # 2. ADDITIONAL LEVEL - source type (if available)
        # Helps to group logically similar sources
        if hasattr(self, 'source_type') and self.source_type:
            path_parts.append(self.source_type)

        # 3. CONTEXT PARAMETERS (dynamic)
        # Add only if present in context
        # Sort for determinism
        for key, value in sorted(self.context.items()):
            if value is not None:
                path_parts.append(f"{key}={value}")

        # 4. DATE and FILE
        path_parts.extend([
            f"date={date}",
            "raw_data.json"
        ])

        return Path(*path_parts)

    def _save_to_bronze(self, output_path: Path):
        """Save to bronze layer - UNIVERSAL"""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # TODO: fix metadata adding to general info
        # Temporarily saving only data without metadata structure
        # Original structure (commented out for now):
        # result = {
        #     "metadata": {
        #         "scraping_timestamp": datetime.now().isoformat(),
        #         "source": self.source_name,
        #         "source_type": getattr(self, 'source_type', 'unknown'),  # if defined
        #         "context": self.context,  # ENTIRE context
        #         "records_count": len(self.collected_data),
        #         "scraper_status": self.status,
        #         "scraper_id": self.scraper_id
        #     },
        #     "data": self.collected_data
        # }
        
        # TEMPORARY: Save only data for MVP
        # Will restore metadata structure when implementing configuration-based system
        result = self.collected_data

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False, default=str)

        self.logger.info(f"Data saved to: {output_path}")

    def _load_scraper_config(self) -> Dict:
        """Load scraper configuration (Strategy Pattern)."""
        return {
            'update_frequency_hours': 24,
            'max_records_per_run': 1000,
            'timeout_minutes': 60,
            'output_format': 'json'
        }
    
    def _setup_logging(self):
        """Configure logging (Observer Pattern)."""
        logger = logging.getLogger(self.scraper_id)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                f'%(asctime)s - {self.scraper_id} - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    # METHODS FOR MANUAL SCRAPING ===
    
    def _handle_manual_scraping(self) -> List[Dict]:
        """
        Handle manual scraping – ONLY directory creation.
        """
        instructions = self.get_scraping_instructions()
        
        print(f"\nMANUAL SCRAPING PREPARATION: {self.scraper_id}")
        print("=" * 60)
        
        for step, instruction in instructions.items():
            print(f"{step}. {instruction}")
        
        # Create directory
        output_path = self._generate_output_path()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        print(f"\nFolders created: {output_path.parent}")
        print("You can now save files to the specified directory")
        input("Press Enter to finish...")
        
        # Return empty result
        return []
    
    def _load_manual_results(self) -> List[Dict]:
        """Load manual results - UNIVERSAL"""
        # Build the base path (without date)
        base_parts = [
            self.project_root,
            "data",
            "bronze",
            self.source_name,
        ]

        # Add source_type if available
        if hasattr(self, 'source_type') and self.source_type:
            base_parts.append(self.source_type)

        # Add context parameters
        for key, value in sorted(self.context.items()):
            if value is not None:
                base_parts.append(f"{key}={value}")

        output_dir = Path(*base_parts)

        if not output_dir.exists():
            return []

        # Search in all subdirectories (including date=*)
        json_files = list(output_dir.rglob("*.json"))

        if not json_files:
            return []

        # Take the newest file
        latest_file = max(json_files, key=lambda x: x.stat().st_mtime)

        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            return data.get('data', [])
        except Exception as e:
            self.logger.error(f"Error loading {latest_file}: {e}")
            return []

