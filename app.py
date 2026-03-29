import streamlit as st
import pandas as pd
import pgeocode
import math
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Calculadora de CPs", layout="wide")
st.title("📍 Calculadora de Distancia y Orientación")

def obtener_orientacion(lat1, lon1, lat2, lon2):
    if pd.isna(lat1) or pd.isna(lon1) or pd.isna(lat2) or pd.isna(lon2):
        return "N/A"
    dLon = lon2 - lon1
    y = math.sin(math.radians(dLon)) * math.cos(math.radians(lat2))
    x = math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - \
        math.sin(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.cos(math.radians(dLon))
    brng = math.atan2(y, x)
    brng = (math.degrees(brng) + 360) % 360
    sectores = ["N", "NNE", "NE", "NEE", "E", "SEE", "SE", "SSE", 
                "S", "SSO", "SO", "SOO", "O", "NOO", "NO", "NNO"]
    idx = int((brng + 11.25) / 22.5) % 16
    return sectores[idx]

# --- AQUÍ CREAMOS LA MEMORIA PARA QUE NO SE BORRE ---
if 'resultados' not in st.session_state:
    st.session_state.resultados = None
if 'mapa' not in st.session_state:
    st.session_state.mapa = None

archivo_subido = st.file_uploader("Sube tu archivo Excel o CSV con los CPs", type=["xlsx", "csv"])

if archivo_subido:
    # Si subes un archivo nuevo, limpiamos la memoria anterior
    if 'ultimo_archivo' not in st.session_state or st.session_state.ultimo_archivo != archivo_subido.name:
        st.session_state.resultados = None
        st.session_state.mapa = None
        st.session_state.ultimo_archivo = archivo_subido.name

    if archivo_subido.name.endswith('.csv'):
        df = pd.read_csv(archivo_subido)
    else:
        df = pd.read_excel(archivo_subido)
    
    st.write("### Vista previa de tus datos:")
    st.dataframe(df.head())

    col_origen = df.columns[0]
    col_destino = df.columns[1]

    if st.button("Calcular Distancias y Orientación"):
        with st.spinner('Calculando más de 7,000 datos... (Esto tomará unos segundos)'):
            df['CP_Origen_str'] = df[col_origen].astype(str).str.zfill(5)
            df['CP_Destino_str'] = df[col_destino].astype(str).str.zfill(5)
            
            nomi = pgeocode.Nominatim('mx')
            dist = pgeocode.GeoDistance('mx')
            
            cps_unicos = pd.concat([df['CP_Origen_str'], df['CP_Destino_str']]).unique()
            df_coords = nomi.query_postal_code(cps_unicos)
            coords_dict = df_coords.set_index('postal_code')[['latitude', 'longitude']].to_dict('index')
            
            distancias = []
            orientaciones = []
            
            for index, row in df.iterrows():
                cp_orig = row['CP_Origen_str']
                cp_dest = row['CP_Destino_str']
                
                d = dist.query_postal_code(cp_orig, cp_dest)
                distancias.append(round(d, 2))
                
                lat1, lon1 = coords_dict.get(cp_orig, {}).get('latitude'), coords_dict.get(cp_orig, {}).get('longitude')
                lat2, lon2 = coords_dict.get(cp_dest, {}).get('latitude'), coords_dict.get(cp_dest, {}).get('longitude')
                
                orientaciones.append(obtener_orientacion(lat1, lon1, lat2, lon2))
                
            if len(df.columns) >= 4:
                df[df.columns[2]] = distancias
                df[df.columns[3]] = orientaciones
            else:
                df['Distancia (Kms)'] = distancias
                df['Orientacion'] = orientaciones
            
            df_final = df.drop(columns=['CP_Origen_str', 'CP_Destino_str'])
            
            # GUARDAMOS EN MEMORIA
            st.session_state.resultados = df_final
            
            # PREPARAMOS EL MAPA Y LO GUARDAMOS EN MEMORIA
            m = folium.Map(location=[23.6345, -102.5528], zoom_start=5)
            for i in range(min(50, len(df_final))):
                cp_orig = str(df_final.iloc[i, 0]).zfill(5)
                cp_dest = str(df_final.iloc[i, 1]).zfill(5)
                lat1, lon1 = coords_dict.get(cp_orig, {}).get('latitude'), coords_dict.get(cp_orig, {}).get('longitude')
                lat2, lon2 = coords_dict.get(cp_dest, {}).get('latitude'), coords_dict.get(cp_dest, {}).get('longitude')
                if pd.notna(lat1) and pd.notna(lon1) and pd.notna(lat2) and pd.notna(lon2):
                    folium.Marker([lat1, lon1], popup=f"Origen: {cp_orig}", icon=folium.Icon(color="blue")).add_to(m)
                    folium.Marker([lat2, lon2], popup=f"Destino: {cp_dest}", icon=folium.Icon(color="red")).add_to(m)
                    folium.PolyLine([(lat1, lon1), (lat2, lon2)], color="green", weight=2, opacity=0.8).add_to(m)
            st.session_state.mapa = m

    # --- FUERA DEL BOTÓN: MOSTRAMOS LO QUE HAY EN MEMORIA ---
    if st.session_state.resultados is not None:
        st.success("¡Cálculo terminado y guardado!")
        st.write("### Resultados")
        st.dataframe(st.session_state.resultados)
        
        csv = st.session_state.resultados.to_csv(index=False).encode('utf-8')
        st.download_button("Descargar Resultados en CSV", csv, "Resultados_CPs.csv", "text/csv")
        
        if st.session_state.mapa is not None:
            st.write("### Visualización en Mapa (Primeros 50 resultados)")
            # returned_objects=[] evita que el mapa refresque la página al darle clic
            st_folium(st.session_state.mapa, width=1000, height=500, returned_objects=[])
