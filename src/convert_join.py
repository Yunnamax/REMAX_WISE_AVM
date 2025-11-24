"""
import csv
import json
import glob
import os

# Настройки
input_files_pattern = 'idealista_land_vila_nova_de_gaia_page*.csv'
output_csv = 'master_vila_nova_de_gaia_land.csv'
output_json = 'master_vila_nova_de_gaia_land.json'

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
"""


# save_as: simple_avm_dashboard.py
# Просто запусти: python simple_avm_dashboard.py

from datetime import datetime

def main():
    """
    Простой скрипт для генерации компактного дашборда AVM пайплайна
    """
    
    # Твои метрики
    METRICS = {
        'files_processed': 47,
        'total_records': '7,438',
        'success_rate': 100,
        'avg_processing_time': 0.12,
        'data_quality': 85,
        'records_per_second': 1319,
    }
    
    # Генерируем HTML
    html_content = f'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>AVM Pipeline Metrics</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background: white;
            color: #333;
        }}
        .dashboard {{
            max-width: 900px;
            margin: 0 auto;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 15px;
            border-bottom: 2px solid #eee;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-bottom: 20px;
        }}
        .metric-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 5px;
            border-left: 4px solid #007acc;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: bold;
            margin: 5px 0;
        }}
        .metric-label {{
            color: #666;
            font-size: 14px;
        }}
        .summary {{
            background: #f0f8ff;
            padding: 20px;
            border-radius: 5px;
            margin-top: 20px;
            font-size: 14px;
            line-height: 1.5;
        }}
        .footer {{
            text-align: center;
            margin-top: 20px;
            color: #888;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="header">
            <h1>AVM Pipeline Performance Metrics</h1>
        </div>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">Files Processed</div>
                <div class="metric-value">{METRICS['files_processed']}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Properties Processed</div>
                <div class="metric-value">{METRICS['total_records']}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Success Rate</div>
                <div class="metric-value">{METRICS['success_rate']}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Processing Time</div>
                <div class="metric-value">{METRICS['avg_processing_time']}s</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Data Quality</div>
                <div class="metric-value">{METRICS['data_quality']}/100</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Records/Second</div>
                <div class="metric-value">{METRICS['records_per_second']}</div>
            </div>
        </div>
        
        <div class="summary">
            <strong>Performance Summary:</strong> The AVM pipeline processed {METRICS['files_processed']} files 
            containing {METRICS['total_records']} property records with {METRICS['success_rate']}% success rate. 
            Average processing time: {METRICS['avg_processing_time']}s per file. Data quality score: {METRICS['data_quality']}/100.
        </div>
        
        <div class="footer">
            Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}
        </div>
    </div>
</body>
</html>
    '''
    
    # Сохраняем файл
    with open("AVM_Metrics_Dashboard.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print("✅ Дашборд создан: AVM_Metrics_Dashboard.html")
    print("📸 Открой файл в браузере и сделай скриншот")

if __name__ == "__main__":
    main()