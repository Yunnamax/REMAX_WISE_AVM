import pandas as pd
import os

# Укажи путь к папке с файлами
folder_path = os.getcwd()

# Пройти по всем CSV файлам в папке
for filename in os.listdir(folder_path):
    if filename.endswith(".csv"):
        file_path = os.path.join(folder_path, filename)
        
        try:
            # Читаем файл с разделителем ;
            df = pd.read_csv(file_path, sep=';')
            
            # Проверяем, есть ли столбец website
            if 'website' in df.columns:
                # Удаляем дубликаты по столбцу website, оставляя первое вхождение
                initial_count = len(df)
                df_clean = df.drop_duplicates(subset=['website'], keep='first')
                
                # Сохраняем обратно с тем же разделителем ;
                df_clean.to_csv(file_path, index=False, sep=';')
                
                print(f"Обработан {filename}: было {initial_count} строк, стало {len(df_clean)} строк")
            else:
                print(f"Пропущен {filename}: нет столбца 'website'")
                
        except Exception as e:
            print(f"Ошибка при обработке {filename}: {e}")

print("Все файлы обработаны!")