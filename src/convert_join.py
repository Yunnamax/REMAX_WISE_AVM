
import csv
import json
import glob
import os

# Настройки
input_files_pattern = 'idealista_apartments_almada_page*.csv'
output_csv = 'idealista_apartments_almada.csv'
output_json = 'idealista_apartments_almada.json'

def merge_csv_files():
    all_data = []
    headers = set()
    
    # Находим все файлы по шаблону
    csv_files = glob.glob(input_files_pattern)
    
    if not csv_files:
        print(f"❌ Файлы по шаблону '{input_files_pattern}' не найдены!")
        return
    
    print(f"📁 Найдено файлов: {len(csv_files)}")
    
    # Читаем все файлы
    for i, csv_file in enumerate(sorted(csv_files)):
        print(f"📖 Читаю файл: {csv_file}")
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                csv_reader = csv.DictReader(f, delimiter=';')
                
                # Сохраняем заголовки из первого файла
                if i == 0:
                    fieldnames = csv_reader.fieldnames
                    print(f"📋 Заголовки: {fieldnames}")
                
                # Читаем данные
                file_data = list(csv_reader)
                all_data.extend(file_data)
                print(f"✅ Добавлено записей: {len(file_data)}")
                
        except Exception as e:
            print(f"❌ Ошибка при чтении {csv_file}: {e}")
            continue
    
    # Сохраняем объединенный CSV
    print(f"\n💾 Сохраняю объединенный CSV...")
    try:
        with open(output_csv, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
            writer.writeheader()
            writer.writerows(all_data)
        print(f"✅ CSV сохранен: {output_csv}")
    except Exception as e:
        print(f"❌ Ошибка при сохранении CSV: {e}")
    
    # Конвертируем в JSON
    print(f"🔄 Конвертирую в JSON...")
    try:
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, indent=4, ensure_ascii=False)
        print(f"✅ JSON сохранен: {output_json}")
    except Exception as e:
        print(f"❌ Ошибка при сохранении JSON: {e}")
    
    # Итоговая статистика
    print(f"\n🎉 Готово!")
    print(f"📊 Всего записей: {len(all_data)}")
    print(f"📁 Исходных файлов: {len(csv_files)}")
    print(f"💾 Результирующие файлы:")
    print(f"   - {output_csv}")
    print(f"   - {output_json}")

# Запуск
if __name__ == "__main__":
    merge_csv_files()



