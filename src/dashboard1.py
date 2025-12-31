import streamlit as st
import pandas as pd
import pydeck as pdk
import numpy as np
import geopandas as gpd
from shapely.geometry import Point

# --- ПУТІ ---
CONTINENTE_GPKG_PATH = r"C:\Users\yunna\OneDrive\Документы\remax_wise_avm\config\geospatial\district_boundaries\Continente_CAOP2024_1.gpkg"
MASTER_GOLD_PATH = r"C:\Users\yunna\OneDrive\Документы\remax_wise_avm\data\gold\master\date=2025-11-29\master_table.parquet"
DETAILS_GOLD_PATH = r"C:\Users\yunna\OneDrive\Документы\remax_wise_avm\data\gold\apartment_rent\date=2025-11-29\apartment_rent_details.parquet"

FREGUESIAS_LAYER_NAME = 'cont_freguesias'
TARGET_MUNICIPALITY = 'Lisboa'

@st.cache_data
def load_and_prepare_data():
    master = pd.read_parquet(MASTER_GOLD_PATH)
    details = pd.read_parquet(DETAILS_GOLD_PATH)
    full_gold = pd.merge(master, details, on='property_id')
    
    full_gold = full_gold[full_gold['municipality'].str.lower().str.contains('lisbo', na=False)]
    full_gold['district'] = full_gold['district'].str.upper().str.strip()
    
    full_gold['energy_efficiency_score'] = pd.to_numeric(full_gold['energy_efficiency_score'], errors='coerce').fillna(0)
    
    geo_data = gpd.read_file(CONTINENTE_GPKG_PATH, layer=FREGUESIAS_LAYER_NAME)
    lisbon_geo = geo_data[geo_data['municipio'] == TARGET_MUNICIPALITY].copy()
    lisbon_geo = lisbon_geo.to_crs(epsg=4326)
    lisbon_geo['freguesia'] = lisbon_geo['freguesia'].str.upper().str.strip()
    
    # Додаємо координати центроїдів для підписів районів
    lisbon_geo['lng'] = lisbon_geo.geometry.centroid.x
    lisbon_geo['lat'] = lisbon_geo.geometry.centroid.y
    
    return full_gold, lisbon_geo

def generate_grid_fill(df_gold, lisbon_geo):
    stats = df_gold.groupby('district').agg({
        'price_per_sqm': 'median',
        'energy_efficiency_score': 'mean'
    }).reset_index()
    
    stats['price_per_sqm'] = stats['price_per_sqm'].round(0)
    stats['energy_efficiency_score'] = stats['energy_efficiency_score'].round(1)
    
    plot_data = []
    step = 0.001 

    for _, district_row in lisbon_geo.iterrows():
        name = district_row['freguesia']
        geom = district_row.geometry
        d_stats = stats[stats['district'] == name]
        
        if d_stats.empty: continue
            
        p_val = float(d_stats.iloc[0]['price_per_sqm'])
        e_val = float(d_stats.iloc[0]['energy_efficiency_score'])

        minx, miny, maxx, maxy = geom.bounds
        for x in np.arange(minx, maxx, step):
            for y in np.arange(miny, maxy, step):
                if geom.contains(Point(x, y)):
                    plot_data.append({
                        'lng': float(x),
                        'lat': float(y),
                        'price_per_sqm': p_val,
                        'energy_efficiency_score': e_val,
                        'district': str(name)
                    })
    
    return pd.DataFrame(plot_data)

def main():
    st.set_page_config(layout="wide", page_title="Lisbon ESG 3D Map")
    st.title("🌱 3D Аналіз: Енергоефективність та Ціни Лісабона")

    # 1. Завантаження та підготовка даних
    df_gold, lisbon_geo = load_and_prepare_data()
    plot_df = generate_grid_fill(df_gold, lisbon_geo)

    if not plot_df.empty:
        # 2. Розрахунок метрик для легенди та кольору
        min_e = plot_df['energy_efficiency_score'].min()
        max_e = plot_df['energy_efficiency_score'].max()
        min_p = plot_df['price_per_sqm'].min()
        max_p = plot_df['price_per_sqm'].max()
        
        def get_energy_color(score):
            norm = (score - min_e) / (max_e - min_e) if max_e > min_e else 0
            contrast_norm = norm ** 2 
            r = int(173 * contrast_norm)
            g = int(40 + (215 * contrast_norm))
            b = int(47 * contrast_norm)
            return [r, g, b, 210]

        plot_df['color'] = plot_df['energy_efficiency_score'].apply(get_energy_color)

        # 3. Створення шарів карти
        
        # Шар меж районів
        boundary_layer = pdk.Layer(
            "GeoJsonLayer",
            lisbon_geo,
            get_fill_color=[0, 0, 0, 0],
            get_line_color=[0, 80, 0, 150],
            get_line_width=2,
        )

        # Шар 3D стовпчиків
        column_layer = pdk.Layer(
            "ColumnLayer",
            plot_df,
            get_position=["lng", "lat"],
            get_elevation="price_per_sqm", 
            elevation_scale=50,
            radius=100,
            get_fill_color="color",
            pickable=True,
            extruded=True,
        )

        # Шар тексту (назви районів прямо на карті)
        text_layer = pdk.Layer(
            "TextLayer",
            lisbon_geo,
            get_position=["lng", "lat"],
            get_text="freguesia",
            get_color=[0, 0, 0, 255], # Чорний колір
            get_size=20,
            get_alignment_baseline="'center'",
            font_weight="bold",
        )

        # 4. Візуалізація карти
        view_state = pdk.ViewState(
            latitude=38.73, longitude=-9.14,
            zoom=11.5, pitch=55
        )

        st.pydeck_chart(pdk.Deck(
            layers=[boundary_layer, column_layer, text_layer],
            initial_view_state=view_state,
            map_style=pdk.map_styles.LIGHT,
            tooltip={
                "html": "<b>Район:</b> {district} <br/>"
                        "<b>Енерго-рейтинг:</b> {energy_efficiency_score} <br/>"
                        "<b>Ціна:</b> {price_per_sqm} €/м²",
                "style": {"backgroundColor": "#002200", "color": "white"}
            }
        ))

        # 5. ПІДПИСИ ТА ЛЕГЕНДА ПІД КАРТОЮ
        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 💰 Вартість (Висота)")
            # Квадратик, що символізує висоту
            st.markdown(f"**Діапазон:** від **{min_p:.0f} €** до **{max_p:.0f} €** за м²")
            st.write("📊 *Чим вищий стовпчик, тим дорожча оренда нерухомості.*")

        with col2:
            st.markdown("### 🌱 Енергоефективність (Колір)")
            # Кольорові квадрати для шкали
            st.markdown(f"**🟥 {min_e:.1f}** (Темно-зелений) — низька ефективність")
            st.markdown(f"**🟩 {max_e:.1f}** (Яскраво-салатовий) — висока ефективність")
            st.write("🎨 *Колір автоматично змінюється залежно від середнього бала енергосертифіката.*")

        st.success(f"✅ Аналіз завершено для муніципалітету Лісабон. Дані базуються на Gold Layer.")
    else:
        st.error("Дані для відображення не знайдені.")
        
        

if __name__ == "__main__":
    main()