from pathlib import Path
import json
from datetime import datetime

class FileSystemTracker:
    def __init__(self, state_file_path: Path = None):
        if state_file_path is None:
            project_root = Path(__file__).parent.parent.parent
            self.state_file = project_root / "metadata" / "processing_state.json"
            self.project_root = project_root
        else:
            self.state_file = Path(state_file_path)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

    def _load_state(self) -> dict:
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {
                    "version": "1.0",
                    "created_at": datetime.now().isoformat(),
                    "files": {}
                }
        except Exception as e:
            print(f"Error loading state: {e}")
            return {"version": "1.0", "created_at": datetime.now().isoformat(), "files": {}}
        
    def _save_state(self, state: dict):
        """Saves the state to a JSON file"""
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)


    def should_process(self, file_path: Path) -> bool:
        """Checks whether the file should be processed"""
        
        # Convert path to string for comparison
        file_path_str = str(file_path.absolute())
        
        # Load current state
        state = self._load_state()
        
        # Look for the file in the state
        if file_path_str in state["files"]:
            file_info = state["files"][file_path_str]
            
            # If status is "processed" - skip it
            if file_info["status"] == "processed":
                return False
                
            # If status is "failed" - process again
            elif file_info["status"] == "failed":
                return True
                
        # If file is not present in the state - process it
        return True

    
    def mark_processed(self, file_path: Path, processor_type: str):
        """Mark file as successfully processed"""
        # 1. Load the current state
        state = self._load_state()
        
        # 2. Create/update the record for this file
        file_path_str = str(file_path.absolute())
        state["files"][file_path_str] = {
            "status": "processed",
            "processor_type": processor_type,
            "updated": datetime.now().isoformat(),
            "error": None  # Successful processing - no errors
        }
        
        # 3. Update the last modified time
        state["updated_at"] = datetime.now().isoformat()
        
        # 4. Save the updated state
        self._save_state(state)

    
    def mark_failed(self, file_path, processor_type, error):
        """mark file as failed"""
                # 1. Load the current state
        state = self._load_state()
        
        # 2. Create/update the record for this file
        file_path_str = str(file_path.absolute())
        state["files"][file_path_str] = {
            "status": "failed",
            "processor_type": processor_type,
            "updated": datetime.now().isoformat(),
            "error": error  
        }
        
        # 3. Update the last modified time
        state["updated_at"] = datetime.now().isoformat()
        
        # 4. Save the updated state
        self._save_state(state)