# simple_map.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
from pathlib import Path
import unicodedata
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import plotly.graph_objects as go

# ==================== НАСТРОЙКА ====================
st.set_page_config(
    page_title="10 Муниципалитетов Лиссабона - Кластерный анализ",
    page_icon="🏠",
    layout="wide"
)

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
def normalize_name(name):
    """Улучшенная нормализация с учетом маппинга"""
    if not isinstance(name, str):
        name = str(name)
    
    # Приводим к нижнему регистру и удаляем пробелы/подчеркивания
    name = name.lower().strip()
    
    # Заменяем подчеркивания на пробелы
    name = name.replace('_', ' ')
    
    # Удаляем лишние пробелы
    name = ' '.join(name.split())
    
    return name

def get_geojson_name(gold_name):
    """Получает название для GeoJSON из названия Gold слоя"""
    gold_normalized = normalize_name(gold_name)
    
    # Если есть прямое соответствие в маппинге
    for gold_key, geojson_value in MUNICIPALITY_MAPPING.items():
        if normalize_name(gold_key) == gold_normalized:
            return geojson_value
    
    # Если нет - пытаемся угадать
    return gold_normalized.upper()

# ==================== ДАННЫЕ ====================

# МАППИНГ между форматами записи


MUNICIPALITY_MAPPING = {
    # Gold -> GeoJSON
    "almada": "ALMADA",
    "aveiro": "AVEIRO", 
    "cascais": "CASCAIS",
    "coimbra": "COIMBRA",
    "leiria": "LEIRIA",
    "lisbon": "LISBOA",  # <-- ОСНОВНАЯ ПРОБЛЕМА ЗДЕСЬ!
    "oeiras": "OEIRAS",
    "porto": "PORTO",
    "sintra": "SINTRA",
    "vila_nova_de_gaia": "VILA NOVA DE GAIA"
}

# СОЗДАЕМ ОБРАТНЫЙ МАППИНГ (GeoJSON -> Gold)
GEOJSON_TO_GOLD_MAPPING = {v: k for k, v in MUNICIPALITY_MAPPING.items()}

# И МАППИНГ ДЛЯ ПЛОТЛИ (данные -> GeoJSON)
PLOTLY_MAPPING = MUNICIPALITY_MAPPING.copy()

YOUR_MUNICIPALITIES = list(MUNICIPALITY_MAPPING.keys())


# ==================== ЗАГРУЗКА И ФИЛЬТРАЦИЯ ДАННЫХ ====================
@st.cache_data
def load_and_filter_geojson():
    """Загружает GeoJSON и данные Gold-шара, фильтрует нужные муниципалитеты"""
    try:
        # Определяем путь к файлу
        project_root = Path(__file__).resolve().parent.parent
        geojson_path = project_root / "data" / "Portugal_Municipalities.geojson"
        
        # Пути к данным Gold-шара
        master_table_path = project_root / "data" / "gold" / "master" / "date=2025-11-29" / "master_table.parquet"
        details_table_path = project_root / "data" / "gold" / "apartment_rent" / "date=2025-11-29" / "apartment_rent_details.parquet"
        
        # Проверка существования файлов
        if not geojson_path.exists():
            st.error(f"❌ GeoJSON файл не найден: {geojson_path}")
            return None, None, None
        
        if not master_table_path.exists():
            st.error(f"❌ Master таблица не найдена: {master_table_path}")
            return None, None, None
            
        if not details_table_path.exists():
            st.error(f"❌ Details таблица не найдена: {details_table_path}")
            return None, None, None
        
        # 1. Загружаем GeoJSON
        with open(geojson_path, 'r', encoding='utf-8') as f:
            geojson_data = json.load(f)
            geojson_data = fix_geojson_names(geojson_data)
        
        st.sidebar.success(f"✅ Загружено: {len(geojson_data['features'])} муниципалитетов")
        
        # 2. Загружаем данные Gold-шара
        st.sidebar.info("📊 Загрузка данных Gold-шара...")
        
        # Master таблица - только нужные колонки для экономии памяти
        master_cols = [
            'property_id', 'municipality', 'transaction_type', 
            'price_value', 'area_m2', 'price_per_sqm', 'district',
            'title_length', 'description_length', 'agent_type'
        ]
        
        master_df = pd.read_parquet(master_table_path, columns=master_cols)
        
        # Фильтруем только аренду
        master_df = master_df[master_df['transaction_type'] == 'rent'].copy()
        
        # Details таблица
        details_df = pd.read_parquet(details_table_path)
        
        st.sidebar.success(f"✅ Master: {len(master_df):,} записей аренды")
        st.sidebar.success(f"✅ Details: {len(details_df):,} записей деталей")
        
        # 3. Объединяем таблицы
        df = pd.merge(
            master_df, 
            details_df, 
            on='property_id', 
            how='inner',
            suffixes=('_master', '_details')
        )
        
        st.sidebar.success(f"✅ Объединенный датафрейм: {len(df):,} записей")
        
        # 4. Фильтруем по 10 ключевым муниципалитетам
        normalized_your_municipalities = [normalize_name(m) for m in YOUR_MUNICIPALITIES]
        df['municipality_normalized'] = df['municipality'].apply(normalize_name)
        df_filtered = df[df['municipality_normalized'].isin(normalized_your_municipalities)].copy()
        
        # Восстанавливаем оригинальные названия муниципалитетов из нашего списка
        name_mapping = {normalize_name(name): name for name in YOUR_MUNICIPALITIES}
        df_filtered['municipality_original'] = df_filtered['municipality_normalized'].map(name_mapping)
        
        st.sidebar.success(f"✅ После фильтрации: {len(df_filtered):,} записей из {df_filtered['municipality_original'].nunique()} муниципалитетов")
        
        # 5. Фильтруем GeoJSON по тем же муниципалитетам
        # Сначала создаем маппинг нормализованных имен из GeoJSON
        geojson_municipalities = []
        for feature in geojson_data['features']:
            # Проверяем разные возможные поля с названиями
            name = feature['properties'].get('NAME_2') or feature['properties'].get('concelho') or feature['properties'].get('municipality')
            if name:
                normalized = normalize_name(name)
                geojson_municipalities.append((normalized, feature))
        
        # Фильтруем только те, что есть в нашем списке
        filtered_features = []
        for normalized_name, feature in geojson_municipalities:
            if normalized_name in normalized_your_municipalities:
                # Добавляем оригинальное название из нашего списка
                feature['properties']['original_name'] = name_mapping[normalized_name]
                #feature['properties']['FINAL_JOIN_KEY'] = name_mapping[normalized_name]
                filtered_features.append(feature)
        
        filtered_geojson = {
            'type': 'FeatureCollection',
            'features': filtered_features
        }
        
        st.sidebar.success(f"✅ Отфильтровано: {len(filtered_features)} муниципалитетов в GeoJSON")
        
        # Статистика по муниципалитетам для отладки
        st.sidebar.info("📈 Статистика по муниципалитетам:")
        stats = df_filtered.groupby('municipality_original').agg({
            'property_id': 'count',
            'price_per_sqm': 'mean',
            'price_value': 'mean',
            'area_m2': 'mean'
        }).round(2)
        
        stats.columns = ['Количество', 'Цена за м²', 'Средняя цена', 'Средняя площадь']
        st.sidebar.dataframe(stats)
        
        return filtered_geojson, df_filtered, stats
        
    except Exception as e:
        st.error(f"❌ Ошибка при загрузке данных: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return None, None, None

def fix_geojson_names(geojson_data):
    """Исправляет названия в GeoJSON для соответствия данным"""
    
    # Ключи, которые могут содержать названия в GeoJSON
    possible_keys = ['NAME_2', 'concelho', 'municipality', 'original_name']
    
    for feature in geojson_data['features']:
        props = feature['properties']
        
        # Находим название
        original_name = None
        for key in possible_keys:
            if key in props:
                original_name = props[key]
                break
        
        if original_name:
            # Приводим к верхнему регистру для сравнения
            name_upper = original_name.upper()
            
            # Пробуем найти соответствие в маппинге
            for gold_name, geojson_name in MUNICIPALITY_MAPPING.items():
                if geojson_name.upper() == name_upper:
                    # Заменяем название в GeoJSON на то, что у нас в данных
                    props['original_name'] = gold_name  # Используем gold-название
                    break
            else:
                # Если не нашли, оставляем как есть
                props['original_name'] = original_name.lower()
    
    return geojson_data

def perform_clustering_analysis(df_filtered):
    """
    Выполняет кластеризацию муниципалитетов методом K-means
    Возвращает DataFrame с кластерами и статистикой
    """
    try:
        # 1. Агрегация по муниципалитетам
        municipality_stats = df_filtered.groupby('municipality_original').agg({
            'property_id': 'count',
            'price_per_sqm': 'mean',
            'area_m2': 'mean',
            'num_bedrooms': 'mean',
            'has_balcony': 'mean'
        }).round(2)
        
        # ПЕРЕИМЕНОВАНИЕ КОЛОНОК
        municipality_stats.columns = [
            'num_listings',
            'avg_price_per_sqm',
            'avg_area_m2',
            'avg_bedrooms',
            'balcony_ratio'
        ]
        
        # ВАЖНО: Сохраняем индекс как отдельную колонку для карты!
        municipality_stats['municipality_original'] = municipality_stats.index
        
        # 2. Нормализация данных (Z-score) - ВАЖНО: убираем колонку municipality_original!
        scaler = StandardScaler()
        features_for_clustering = municipality_stats[['avg_price_per_sqm', 'num_listings', 'avg_area_m2', 'avg_bedrooms']]
        
        # Заполняем NaN если есть
        features_for_clustering = features_for_clustering.fillna(features_for_clustering.mean())
        
        scaled_features = scaler.fit_transform(features_for_clustering)
        
        # 3. Кластеризация K-means (3 кластера)
        kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
        municipality_stats['cluster'] = kmeans.fit_predict(scaled_features)
        
        # 4. Описание кластеров на основе центроидов
        cluster_centers = kmeans.cluster_centers_
        cluster_centers_original = scaler.inverse_transform(cluster_centers)
        
        # Создаем DataFrame центроидов
        centroids_df = pd.DataFrame(
            cluster_centers_original,
            columns=['avg_price_per_sqm', 'num_listings', 'avg_area_m2', 'avg_bedrooms']
        )
        
        # Назначаем названия кластерам по цене
        price_order = centroids_df['avg_price_per_sqm'].argsort()[::-1]
        
        cluster_names = {
            price_order[0]: '🏆 Премиум-сегмент',
            price_order[1]: '💰 Средний сегмент',
            price_order[2]: '📊 Бюджетный сегмент'
        }
        
        municipality_stats['cluster_name'] = municipality_stats['cluster'].map(cluster_names)
        
        # 5. Добавляем характеристики кластеров
        cluster_summary = municipality_stats.groupby('cluster_name').agg({
            'avg_price_per_sqm': ['mean', 'std'],
            'num_listings': ['mean', 'sum'],
            'avg_area_m2': 'mean',
            'avg_bedrooms': 'mean',
            'balcony_ratio': 'mean'
        }).round(2)
        
        return municipality_stats, cluster_summary, centroids_df
        
    except Exception as e:
        st.error(f"Ошибка в кластеризации: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def create_simple_cluster_map(geojson_data, municipality_stats):
    """Простая версия карты для тестирования"""
    
    # Просто покажем данные без карты, если что-то не так
    st.write("### Вместо карты покажем таблицу кластеров:")
    
    # Создаем красивую таблицу
    display_data = municipality_stats[['municipality_original', 'cluster_name', 
                                     'avg_price_per_sqm', 'num_listings']].copy()
    display_data['avg_price_per_sqm'] = '€' + display_data['avg_price_per_sqm'].astype(str)
    display_data.columns = ['Муниципалитет', 'Сегмент', 'Средняя цена за м²', 'Количество объявлений']
    
    st.dataframe(display_data, use_container_width=True)
    
    # Также покажем кластеры на простой гистограмме
    st.write("### Распределение по сегментам:")
    
    cluster_counts = municipality_stats['cluster_name'].value_counts()
    fig = px.bar(
        x=cluster_counts.index,
        y=cluster_counts.values,
        color=cluster_counts.index,
        color_discrete_map={
            '🏆 Премиум-сегмент': '#FF6B6B',
            '💰 Средний сегмент': '#4ECDC4',
            '📊 Бюджетный сегмент': '#45B7D1'
        },
        labels={'x': 'Сегмент', 'y': 'Количество муниципалитетов'},
        title='Распределение муниципалитетов по сегментам'
    )
    
    return fig

def create_cluster_map(geojson_data, municipality_stats):
    """
    Создает интерактивную карту муниципалитетов, раскрашенную по кластерам
    """
    try:
        # Проверка входных данных
        if municipality_stats is None or municipality_stats.empty:
            st.error("Нет данных для построения карты")
            return None
        
        # Проверка GeoJSON
        if 'features' not in geojson_data or not geojson_data['features']:
            st.error("❌ GeoJSON не содержит features")
            return None
        
        # ДИАГНОСТИКА: покажем все свойства первого feature
        first_feature = geojson_data['features'][0]
        st.write("**Все свойства первого feature:**", first_feature['properties'].keys())
        
        # Подготовка данных для карты
        map_data = municipality_stats.copy()
        
        # ПРЕОБРАЗУЕМ НАЗВАНИЯ: Gold -> GeoJSON формат (верхний регистр)
        map_data['geojson_name'] = map_data['municipality_original'].str.upper()
        
        # Специальная обработка для особых случаев
        map_data['geojson_name'] = map_data['geojson_name'].replace({
            'LISBON': 'LISBOA',
            'VILA_NOVA_DE_GAIA': 'VILA NOVA DE GAIA'
        })
        
        # Диагностика: что получилось
        st.write("**Преобразованные названия для карты:**")
        for gold_name, geojson_name in zip(map_data['municipality_original'], map_data['geojson_name']):
            st.write(f"  {gold_name} -> {geojson_name}")
        
        # Получаем имена из GeoJSON
        geo_names = []
        for feature in geojson_data['features']:
            props = feature['properties']
            
            # Пробуем разные варианты ключей
            name = props.get('Concelho') or props.get('CONCELHO') or props.get('concelho') or props.get('NAME_2')
            if name:
                geo_names.append(name.upper().strip())
        
        st.write("**Имена в GeoJSON (первые 10):**", geo_names[:10])
        st.write("**Имена после преобразования:**", map_data['geojson_name'].tolist())
        
        # Находим совпадающие имена
        common = set(geo_names) & set(map_data['geojson_name'])
        st.write("**Совпадающие имена:**", common)
        
        if not common:
            st.error("❌ Нет совпадающих имен!")
            
            # Поищем частичные совпадения
            st.write("**Поиск частичных совпадений:**")
            for geo_name in geo_names:
                for our_name in map_data['geojson_name']:
                    if geo_name.replace(' ', '') == our_name.replace(' ', ''):
                        st.write(f"  Возможное совпадение: {geo_name} ~ {our_name}")
                        break
        
        # Фильтруем данные только для совпадающих муниципалитетов
        filtered_data = map_data[map_data['geojson_name'].isin(common)]
        
        if filtered_data.empty:
            st.error("❌ После фильтрации данных не осталось")
            return None
        
        # Цветовая схема для кластеров
        color_map = {
            '🏆 Премиум-сегмент': '#FF6B6B',
            '💰 Средний сегмент': '#4ECDC4',
            '📊 Бюджетный сегмент': '#45B7D1'
        }
        
        # Создание карты
        fig = px.choropleth(
            filtered_data,
            geojson=geojson_data,
            locations='geojson_name',
            color='cluster_name',
            color_discrete_map=color_map,
            featureidkey="properties.Concelho",  # Теперь точно правильный ключ!
            hover_data={
                'Средняя цена за м²': '€' + filtered_data['avg_price_per_sqm'].astype(str),
                'Объявлений': filtered_data['num_listings'],
                'Средняя площадь': filtered_data['avg_area_m2'].astype(str) + ' м²'
            },
            title='<b>Кластерный анализ муниципалитетов</b>',
            labels={'cluster_name': 'Сегмент рынка'}
        )
        
        # Настройка внешнего вида
        fig.update_geos(
            fitbounds="locations",
            visible=False
        )
        
        fig.update_layout(
            margin={"r":0,"t":100,"l":0,"b":0},
            title_font_size=20,
            title_x=0.5
        )
        
        return fig
        
    except Exception as e:
        st.error(f"❌ Ошибка при создании карты: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return None
        
    except Exception as e:
        st.error(f"❌ Ошибка при создании карты: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return None

def create_radar_chart(cluster_summary):
    """
    Создает радарную диаграмму для сравнения профилей кластеров
    """
    try:
        # Проверяем входные данные
        if cluster_summary is None or cluster_summary.empty:
            return go.Figure()
        
        # 1. Извлекаем только средние значения (убираем MultiIndex)
        if isinstance(cluster_summary.columns, pd.MultiIndex):
            # Если MultiIndex, берем только 'mean' значения
            df_means = cluster_summary.xs('mean', axis=1, level=1)
        else:
            df_means = cluster_summary
        
        # 2. Определяем нужные признаки
        features_map = {
            'avg_price_per_sqm': 'Цена за м²',
            'num_listings': 'Объем рынка',
            'avg_area_m2': 'Средняя площадь',
            'avg_bedrooms': 'Ср. кол-во спален',
            'balcony_ratio': 'Доля с балконом'
        }
        
        # Оставляем только те признаки, которые есть в данных
        available_features = [f for f in features_map.keys() if f in df_means.columns]
        if not available_features:
            return go.Figure()
        
        # 3. Нормализуем значения (0-1)
        df_normalized = pd.DataFrame(index=df_means.index)
        
        for feature in available_features:
            values = df_means[feature]
            min_val = values.min()
            max_val = values.max()
            
            if max_val > min_val:
                df_normalized[feature] = (values - min_val) / (max_val - min_val)
            else:
                df_normalized[feature] = 0.5
        
        # 4. Создаем радарную диаграмму
        fig = go.Figure()
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1']
        
        for i, (cluster_name, row) in enumerate(df_normalized.iterrows()):
            values = row[available_features].tolist()
            
            # Замыкаем круг (добавляем первое значение в конец)
            values = values + [values[0]]
            categories = [features_map[f] for f in available_features]
            categories = categories + [categories[0]]
            
            fig.add_trace(go.Scatterpolar(
                r=values,
                theta=categories,
                name=cluster_name,
                fill='toself',
                line_color=colors[i % len(colors)],
                opacity=0.7
            ))
        
        # 5. Настройки графика
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 1],
                    tickfont=dict(size=10)
                ),
                angularaxis=dict(
                    tickfont=dict(size=12),
                    rotation=90
                )
            ),
            title='<b>Сравнение профилей рыночных сегментов</b><br><span style="font-size:14px">Нормализованные характеристики кластеров</span>',
            title_font_size=18,
            title_x=0.5,
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=1.05
            ),
            height=500
        )
        
        return fig
        
    except Exception as e:
        import traceback
        st.error(f"Ошибка в create_radar_chart: {str(e)}")
        st.code(traceback.format_exc())
        return go.Figure()

# ==================== ГЛАВНАЯ СТРАНИЦА ====================
# ==================== ОСНОВНОЙ КОД ====================
def main():

    """Основная функция дашборда - только визуализации"""
    
    # Минимальный заголовок
    st.title("🏙️ Анализ рынка аренды Лиссабона")

    # ВЕРСИЯ С БЕЗОПАСНОЙ ПРОВЕРКОЙ
    try:
        result = load_and_filter_geojson()
        
        if result is None:
            st.error("❌ Функция загрузки вернула None")
            st.stop()
        
        if len(result) != 3:
            st.error(f"❌ Ожидалось 3 значения, получили {len(result)}")
            st.stop()
            
        geojson_data, df_filtered, stats = result
        
    except Exception as e:
        st.error(f"❌ Ошибка при распаковке данных: {str(e)}")
        st.stop()
    
    # ТЕПЕРЬ БЕЗОПАСНО ИСПОЛЬЗОВАТЬ df_filtered
    if df_filtered is None or df_filtered.empty:
        st.error("❌ Данные не загружены или пустые")
        st.stop()
    
    # Проверяем, что нужные колонки есть
    required_columns = ['municipality_original', 'price_per_sqm', 'area_m2']
    missing_columns = [col for col in required_columns if col not in df_filtered.columns]
    
    if missing_columns:
        st.error(f"❌ Отсутствуют колонки: {missing_columns}")
        st.write("Доступные колонки:", df_filtered.columns.tolist())
        st.stop()
    
    # ДИАГНОСТИКА: покажем что загрузилось
    st.write("### 📊 Загруженные данные:")
    st.write(f"• Количество записей: {len(df_filtered):,}")
    st.write(f"• Муниципалитеты: {df_filtered['municipality_original'].unique().tolist()}")
    st.write(f"• Количество муниципалитетов: {df_filtered['municipality_original'].nunique()}")

    st.markdown("### Визуализация данных Gold-шара AVM-системы")
    st.markdown("---")
    
    # Блок загрузки
    with st.spinner("📥 Загрузка данных Gold-шара..."):
        geojson_data, df_filtered, stats = load_and_filter_geojson()
    
    if geojson_data is None or df_filtered is None:
        st.error("❌ Не удалось загрузить данные")
        st.stop()
    
    # Основные метрики сверху
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Всего объявлений", f"{len(df_filtered):,}")
    with col2:
        st.metric("Муниципалитетов", df_filtered['municipality_original'].nunique())
    with col3:
        avg_price = df_filtered['price_per_sqm'].mean()
        st.metric("Средняя цена за м²", f"€{avg_price:.2f}")
    with col4:
        avg_area = df_filtered['area_m2'].mean()
        st.metric("Средняя площадь", f"{avg_area:.1f} м²")
    
    # Вкладки ТОЛЬКО с графиками
    tab1, tab2, tab3 = st.tabs(["📊 Распределение цен", "🗺️ Кластерный анализ", "📈 Сравнение муниципалитетов"])
    
    # ==================== ВКЛАДКА 1: РАСПРЕДЕЛЕНИЕ ЦЕН ====================
    with tab1:
        st.subheader("Розподіл цін оренди за квадратний метр")
        
        # Гістограма розподілу цін
        fig_hist = px.histogram(
            df_filtered,
            x='price_per_sqm',
            nbins=50,
            color_discrete_sequence=['#4ECDC4'],
            labels={'price_per_sqm': 'Ціна за м² (€)', 'count': 'Кількість оголошень'}
        )
        
        fig_hist.update_layout(
            # 1. ЗАГОЛОВОК ГРАФІКА
            title={
                'text': "Розподіл цін оренди за квадратний метр",
                'font': {'size': 24, 'family': 'Arial', 'color': "#FFFFFF"}, # Збільшуємо розмір заголовка графіка
                'x': 0.5, # Центруємо заголовок
                'xanchor': 'center',
                'yanchor': 'top'
            },
            
            bargap=0.1,
            height=500,
            showlegend=False,
            
            # 2. ПІДПИСИ ОСЕЙ (Title)
            xaxis_title={
                'text': "Ціна за м² (€)",
                'font': {'size': 18, 'family': 'Arial', 'color': "#FFFFFF"} # Збільшуємо розмір заголовка осі X
            },
            yaxis_title={
                'text': "Кількість оголошень",
                'font': {'size': 18, 'family': 'Arial', 'color': "#FFFFFF"} # Збільшуємо розмір заголовка осі Y
            },
            
            # 3. ТЕКСТ НА ОСЯХ (Tick labels)
            xaxis={
                'tickfont': {'size': 14, 'family': 'Arial'}, # Збільшуємо розмір міток на осі X
                'showgrid': True, 
                'gridcolor': '#E0E0E0'
            },
            yaxis={
                'tickfont': {'size': 14, 'family': 'Arial'}, # Збільшуємо розмір міток на осі Y
                'showgrid': True, 
                'gridcolor': '#E0E0E0'
            }
        )
        
        st.plotly_chart(fig_hist, use_container_width=True)

        # Box-plot по муниципалитетам
    st.subheader("Розподіл цін за муніципалітетами")
        
    fig_box = px.box(
            df_filtered,
            x='municipality_original',
            y='price_per_sqm',
            points=False,
            color='municipality_original',
            # Переклад міток даних для px
            labels={'municipality_original': 'Муніципалітет', 'price_per_sqm': 'Ціна за м² (€)'}
        )
    
    fig_box.update_layout(
        showlegend=False,
        xaxis_tickangle=-45,
        height=600,
        
        # 1. ЗАГОЛОВОК ГРАФІКА
        title={
            'text': "Розподіл цін за муніципалітетами",
            'font': {'size': 24, 'family': 'Arial', 'color': '#FFFFFF'}, # Білий, крупний
            'x': 0.5, 
            'xanchor': 'center',
            'yanchor': 'top'
        },
        
        # 2. ПІДПИСИ ОСЕЙ (Title)
        xaxis_title={
            'text': "Муніципалітет",
            'font': {'size': 18, 'family': 'Arial', 'color': '#FFFFFF'} # Білий, крупний
        },
        yaxis_title={
            'text': "Ціна за м² (€)",
            'font': {'size': 18, 'family': 'Arial', 'color': '#FFFFFF'} # Білий, крупний
        },
        
        # 3. ТЕКСТ НА ОСЯХ (Tick labels)
        xaxis={
            'tickfont': {'size': 14, 'family': 'Arial', 'color': '#FFFFFF'}, # Білі мітки
            'showgrid': True, 
            'gridcolor': '#666666' 
        },
        yaxis={
            'tickfont': {'size': 14, 'family': 'Arial', 'color': '#FFFFFF'}, # Білі мітки
            'showgrid': True, 
            'gridcolor': '#666666'
        }
    )
    
    st.plotly_chart(fig_box, use_container_width=True)
        
    
    # ==================== ВКЛАДКА 2: КЛАСТЕРНЫЙ АНАЛИЗ ====================
    with tab2:
        st.subheader("Сегментація муніципалітетів за ринковими характеристиками")
        
        # Кластеризація (виконання аналізу)
        municipality_stats, cluster_summary, _ = perform_clustering_analysis(df_filtered)

        # 1. Карта кластерів
        st.markdown("#### 1. Географічний розподіл сегментів")
        cluster_map = create_simple_cluster_map(geojson_data, municipality_stats)
        
        # --- СТИЛІЗАЦІЯ КАРТИ ---
        cluster_map.update_layout(
            # Назва графіку (білий та крупний)
            title={
                'text': "Географічний розподіл кластерів нерухомості",
                'font': {'size': 24, 'family': 'Arial', 'color': '#FFFFFF'},
                'x': 0.5,
                'xanchor': 'center',
                'yanchor': 'top'
            },
            
            # Загальне налаштування шрифтів (для легенди, якщо вона є)
            font=dict(
                family="Arial",
                size=14,
                color="#FFFFFF"
            ),
            
            # Налаштування фону (якщо графік відображається на темному тлі)
            plot_bgcolor='rgba(0, 0, 0, 0)', 
            paper_bgcolor='rgba(0, 0, 0, 0)',
            
            # Налаштування легенди (також білий колір)
            legend=dict(
                font=dict(color="#FFFFFF", size=16),
                title=dict(text="Кластер", font=dict(color="#FFFFFF", size=18))
            )
        )
        # --- КІНЕЦЬ СТИЛІЗАЦІЇ ---
        
        st.plotly_chart(cluster_map, use_container_width=True)
        
 
    
    # ==================== ВКЛАДКА 3: СРАВНЕНИЕ МУНИЦИПАЛИТЕТОВ ====================
    with tab3:
        st.subheader("Сравнительный анализ муниципалитетов")
        
 
    

# ==================== ЗАПУСК ====================
if __name__ == "__main__":
    main()