import pandas as pd

# Загружаем оба файла
main_file = "architecture_firms_with_logos_normalized_new.csv"
reference_file = "combined_google_maps_logo_enhanced_unique.csv"

print(" Загрузка файлов...")
df_main = pd.read_csv(main_file, sep=';', encoding='utf-8')
df_reference = pd.read_csv(reference_file, sep=',', encoding='utf-8')

print(f"Основной файл: {len(df_main)} строк, {df_main['website'].nunique()} уникальных website")
print(f"Справочный файл: {len(df_reference)} строк, {df_reference['website'].nunique()} уникальных website")

# Удаляем дубликаты в основном файле (оставляем первую запись для каждого website)
df_main_unique = df_main.drop_duplicates(subset=['website'], keep='first')
print(f"\nПосле удаления дубликатов в основном файле: {len(df_main_unique)} строк")

# Удаляем дубликаты в справочном файле
df_reference_unique = df_reference.drop_duplicates(subset=['website'], keep='first')
print(f"После удаления дубликатов в справочном файле: {len(df_reference_unique)} строк")

# Получаем множества уникальных website
main_websites = set(df_main_unique['website'].dropna().str.strip().str.lower())
ref_websites = set(df_reference_unique['website'].dropna().str.strip().str.lower())

print(f"\n📊 СТАТИСТИКА УНИКАЛЬНЫХ WEBSITE:")
print(f"Уникальных website в основном файле: {len(main_websites)}")
print(f"Уникальных website в справочном файле: {len(ref_websites)}")

# Находим пересечения и уникальные значения
common_websites = main_websites.intersection(ref_websites)
only_in_main = main_websites - ref_websites
only_in_ref = ref_websites - main_websites

print(f"\n АНАЛИЗ ПЕРЕСЕЧЕНИЙ:")
print(f"Общие website: {len(common_websites)}")
print(f"Website только в основном файле: {len(only_in_main)}")
print(f"Website только в справочном файле: {len(only_in_ref)}")

# СОЗДАЕМ РЕЗУЛЬТИРУЮЩИЙ ФАЙЛ:
# 1. Берем все записи из основного файла, которые ЕСТЬ в справочном
df_common = df_main_unique[df_main_unique['website'].apply(
    lambda x: str(x).strip().lower() in common_websites if pd.notna(x) else False
)]

# 2. Берем записи только из основного файла
df_only_main = df_main_unique[df_main_unique['website'].apply(
    lambda x: str(x).strip().lower() in only_in_main if pd.notna(x) else False
)]

# 3. Берем записи только из справочного файла
df_only_ref = df_reference_unique[df_reference_unique['website'].apply(
    lambda x: str(x).strip().lower() in only_in_ref if pd.notna(x) else False
)]

print(f"\n ФОРМИРУЕМ РЕЗУЛЬТАТ:")
print(f"Общие записи (из основного файла): {len(df_common)}")
print(f"Только из основного файла: {len(df_only_main)}")
print(f"Только из справочного файла: {len(df_only_ref)}")

# Объединяем все три части
df_result = pd.concat([df_common, df_only_main, df_only_ref], ignore_index=True)

print(f"\n ИТОГОВЫЙ РЕЗУЛЬТАТ:")
print(f"Всего уникальных записей: {len(df_result)}")
print(f"Уникальных website в результате: {df_result['website'].nunique()}")

# Проверяем, что дубликатов нет
duplicates = df_result.duplicated(subset=['website']).sum()
print(f"Дубликатов в результате: {duplicates}")

# Покажем примеры из каждой категории
print(f"\n ПРИМЕРЫ ОБЩИХ ЗАПИСЕЙ:")
for i, row in df_common.head(3).iterrows():
    print(f"  {i+1}. {row.get('company_name', 'N/A')} - {row.get('website', 'N/A')}")

print(f"\n ПРИМЕРЫ ТОЛЬКО ИЗ ОСНОВНОГО ФАЙЛА:")
for i, row in df_only_main.head(3).iterrows():
    print(f"  {i+1}. {row.get('company_name', 'N/A')} - {row.get('website', 'N/A')}")

print(f"\n ПРИМЕРЫ ТОЛЬКО ИЗ СПРАВОЧНОГО ФАЙЛА:")
for i, row in df_only_ref.head(3).iterrows():
    print(f"  {i+1}. {row.get('company_name', 'N/A')} - {row.get('website', 'N/A')}")

# Сохраняем результат
output_file = "architecture_firms_final_cleaned.csv"
df_result.to_csv(output_file, sep=';', encoding='utf-8', index=False)
print(f"\n Результат сохранен в: {output_file}")