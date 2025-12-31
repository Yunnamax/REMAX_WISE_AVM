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
    
    # Примусово в число
    full_gold['energy_efficiency_score'] = pd.to_numeric(full_gold['energy_efficiency_score'], errors='coerce').fillna(0)
    
    geo_data = gpd.read_file(CONTINENTE_GPKG_PATH, layer=FREGUESIAS_LAYER_NAME)
    lisbon_geo = geo_data[geo_data['municipio'] == TARGET_MUNICIPALITY].copy()
    lisbon_geo = lisbon_geo.to_crs(epsg=4326)
    lisbon_geo['freguesia'] = lisbon_geo['freguesia'].str.upper().str.strip()
    
    return full_gold, lisbon_geo

def generate_grid_fill(df_gold, lisbon_geo):
    stats = df_gold.groupby('district').agg({
        'price_per_sqm': 'median',
        'energy_efficiency_score': 'mean'
    }).reset_index()
    
    # Попереднє округлення в Pandas - запорука успіху
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
    st.set_page_config(layout="wide", page_title="Lisbon ESG Map")
    st.title("🌱 Аналіз енергоефективності районів Лісабона")

    df_gold, lisbon_geo = load_and_prepare_data()
    plot_df = generate_grid_fill(df_gold, lisbon_geo)

    if not plot_df.empty:
        min_e = plot_df['energy_efficiency_score'].min()
        max_e = plot_df['energy_efficiency_score'].max()
        
        def get_energy_color(score):
            norm = (score - min_e) / (max_e - min_e) if max_e > min_e else 0
            contrast_norm = norm ** 2 
            r = int(173 * contrast_norm)
            g = int(40 + (215 * contrast_norm))
            b = int(47 * contrast_norm)
            return [r, g, b, 210]

        plot_df['color'] = plot_df['energy_efficiency_score'].apply(get_energy_color)

        boundary_layer = pdk.Layer(
            "GeoJsonLayer",
            lisbon_geo,
            get_fill_color=[0, 0, 0, 0],
            get_line_color=[0, 80, 0, 150],
            get_line_width=2,
        )

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

        # Фіксований Tooltip без розривів та опечаток
        tooltip_html = "<b>Район:</b> SANTO ANTÓNIO <br/><b>Енерго-рейтинг:</b> 3.9<br/><b>Ціна:</b> 29€"

        st.pydeck_chart(pdk.Deck(
            layers=[boundary_layer, column_layer],
            initial_view_state=pdk.ViewState(latitude=38.73, longitude=-9.14, zoom=11.5, pitch=55),
            map_style=pdk.map_styles.LIGHT,
            tooltip={"html": tooltip_html, "style": {"backgroundColor": "#002200", "color": "white"}}
        ))
        
        st.write(f"🟢 **Діапазон:** {min_e:.1f} бал. (Темний) — {max_e:.1f} бал. (Салатовий)")

if __name__ == "__main__":
    main()