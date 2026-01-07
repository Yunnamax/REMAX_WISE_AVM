import sys
from pathlib import Path
import json

# Set up paths
project_root = Path(__file__).parent.parent  # project root (remax_wise_avm/)
sys.path.insert(0, str(project_root))

from src.data_pipeline.bronze_to_silver_coordinator import BronzeToSilverCoordinator
from src.data_pipeline.silver_to_gold_coordinator import SilverToGoldCoordinator

def main():
    
    coordinator1 = BronzeToSilverCoordinator(project_root=project_root)
    #coordinator2 = SilverToGoldCoordinator(project_root=project_root)
    

    results1 = coordinator1.process_all_files()
    #results2 = coordinator2.process_all_files()
    
    print("Processing is over")
    print(f"Files rocessed: {len(results1)}")
    #print(f"Files rocessed: {len(results2)}")

if __name__ == "__main__": 
    main()