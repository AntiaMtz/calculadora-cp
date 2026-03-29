import streamlit as st
import pandas as pd
import pgeocode
import math
import requests
import time

st.set_page_config(page_title="Calculadora de CPs y Rutas", layout="wide")
st.title("📍 Calculadora de Distancia, Tiempo de Manejo y Orientación")
st.markdown("**Nota:** El cálculo de rutas vehiculares usa OSRM (Open Source). Procesar miles de datos tomará tiempo para evitar bloqueos del servidor gratuito.")

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

def obtener_ruta_vehicular(lon1, lat1, lon2, lat2):
    # Usamos el servidor público de OSRM
    if pd.isna(lat1) or pd.isna(lon1) or pd.isna(lat2) or pd.isna(lon2):
        return "Error coord", "Error coord"
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
        respuesta = requests.get(url, timeout=5)
        datos = respuesta.json()
        if datos.get("code") == "Ok":
            distancia_km = datos["routes"][0]["distance"] / 1000.0
            tiempo_min = datos["routes"][0]["duration"] / 60.0
            return round(distancia_km, 2), round(tiempo_min, 0)
    except Exception:
        pass
    return "Falla Servidor", "Falla Servidor"

if 'resultados' not in st.session_state:
    st.session_state.resultados = None

archivo_subido = st.file_uploader("Sube tu archivo Excel o CSV con los CPs", type=["xlsx", "csv"])

if archivo_subido:
    if 'ultimo_archivo' not in st.session_state or st.session_state.ultimo_archivo != archivo_subido.name:
        st.session_state.resultados = None
        st.session_state.ultimo_archivo = archivo_subido.name

    if archivo_subido.name.endswith('.csv'):
        df = pd.read_csv(archivo_subido)
    else:
        df = pd.read_excel(archivo_subido)

    col_origen = df.columns[0]
    col_destino = df.columns[1]

    if st.button("🚀 Iniciar Cálculo Masivo (Gratis)"):
        df['CP_Origen_str'] = df[col_origen].astype(str).str.zfill(5)
        df['CP_Destino_str'] = df[col_destino].astype(str).str.zfill(5)
        
        nomi = pgeocode.Nominatim('mx')
        cps_unicos = pd.concat([df['CP_Origen_str'], df['CP_Destino_str']]).unique()
        df_coords = nomi.query_postal_code(cps_unicos)
        coords_dict = df_coords.set_index('postal_code')[['latitude', 'longitude']].to_dict('index')
        
        distancias_reales = []
        tiempos_manejo = []
        orientaciones = []
        enlaces_maps = []
        
        barra_progreso = st.progress(0)
        texto_progreso = st.empty()
        total_filas = len(df)
        
        for index, row in df.iterrows():
            cp_orig = row['CP_Origen_str']
            cp_dest = row['CP_Destino_str']
            
            lat1 = coords_dict.get(cp_orig, {}).get('latitude')
            lon1 = coords_dict.get(cp_orig, {}).get('longitude')
            lat2 = coords_dict.get(cp_dest, {}).get('latitude')
            lon2 = coords_dict.get(cp_dest, {}).get('longitude')
            
            # Cálculo de Ruta y Tiempo (OSRM)
            dist_km, tiempo_m = obtener_ruta_vehicular(lon1, lat1, lon2, lat2)
            distancias_reales.append(dist_km)
            tiempos_manejo.append(tiempo_m)
            
            # Orientación Matemática
            orientaciones.append(obtener_orientacion(lat1, lon1, lat2, lon2))
            
            # URL de Google Maps para validación manual
            url = f"https://www.google.com/maps/dir/?api=1&origin={cp_orig},+Mexico&destination={cp_dest},+Mexico"
            enlaces_maps.append(url)
            
            # Micropausa para no saturar la API gratuita
            time.sleep(0.3) 
            
            # Actualizar progreso
            porcentaje = int(((index + 1) / total_filas) * 100)
            barra_progreso.progress(porcentaje)
            texto_progreso.text(f"Procesando fila {index + 1} de {total_filas}...")
            
        # Asignar a nuevas columnas
        df['Distancia Carretera (Kms)'] = distancias_reales
        df['Tiempo Manejo (Minutos)'] = tiempos_manejo
        df['Orientacion'] = orientaciones
        df['URL Validación Maps'] = enlaces_maps
        
        df_final = df.drop(columns=['CP_Origen_str', 'CP_Destino_str'])
        st.session_state.resultados = df_final
        texto_progreso.empty()
        barra_progreso.empty()

    if st.session_state.resultados is not None:
        st.success("¡Cálculo terminado con éxito!")
        
        csv = st.session_state.resultados.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 DESCARGAR TABLA CON TIEMPOS DE MANEJO",
            data=csv,
            file_name="Resultados_Rutas_Gratis.csv",
            mime="text/csv"
        )
        st.dataframe(st.session_state.resultados)
