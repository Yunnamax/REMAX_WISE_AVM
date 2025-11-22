import sys
from pathlib import Path
import json

# Set up paths
project_root = Path(__file__).parent.parent  # project root (remax_wise_avm/)
sys.path.insert(0, str(project_root))

from src.data_pipeline.coordinator import BronzeToSilverCoordinator

def main():
    # Используем тот же project_root что и выше
    coordinator = BronzeToSilverCoordinator(project_root=project_root)
    
    # Запускаем обработку
    results = coordinator.process_all_files()
    
    # Выводим результаты
    print("Обработка завершена!")
    print(f"Обработано файлов: {len(results)}")

if __name__ == "__main__": 
    main()