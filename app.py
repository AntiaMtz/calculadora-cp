import streamlit as st
import pandas as pd
import pgeocode
import math
import requests
import time
import io

st.set_page_config(page_title="Calculadora de CPs y Rutas", layout="wide")
st.title("Sin Limits - Calculadora de Rutas")

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

    total_registros = len(df)
    st.write(f"Tu archivo tiene **{total_registros}** combinaciones.")
    
    # --- CONFIGURACIÓN DE LOTES ---
    st.write("### ⚙️ Procesamiento por Lotes")
    st.info("Para evitar que el servidor se desconecte, procesa bloques de 1,000 en 1,000.")
    
    col1, col2 = st.columns(2)
    with col1:
        inicio = st.number_input("Fila inicial", min_value=1, max_value=total_registros, value=1)
    with col2:
        fin = st.number_input("Fila final", min_value=1, max_value=total_registros, value=min(1000, total_registros))

    col_origen = df.columns[0]
    col_destino = df.columns[1]

    if st.button("🚀 Iniciar Cálculo de este Lote"):
        df_lote = df.iloc[inicio-1:fin].copy()
        
        df_lote['CP_Origen_str'] = df_lote[col_origen].astype(str).str.zfill(5)
        df_lote['CP_Destino_str'] = df_lote[col_destino].astype(str).str.zfill(5)
        nomi = pgeocode.Nominatim('mx')
        cps_unicos = pd.concat([df_lote['CP_Origen_str'], df_lote['CP_Destino_str']]).unique()
        df_coords = nomi.query_postal_code(cps_unicos)
        coords_dict = df_coords.set_index('postal_code')[['latitude', 'longitude']].to_dict('index')
        
        distancias_reales = []
        tiempos_manejo = []
        orientaciones = []
        enlaces_maps = []
        
        barra_progreso = st.progress(0)
        texto_progreso = st.empty()
        filas_lote = len(df_lote)
        
        for i, (index, row) in enumerate(df_lote.iterrows()):
            cp_orig = row['CP_Origen_str']
            cp_dest = row['CP_Destino_str']
            
            lat1 = coords_dict.get(cp_orig, {}).get('latitude')
            lon1 = coords_dict.get(cp_orig, {}).get('longitude')
            lat2 = coords_dict.get(cp_dest, {}).get('latitude')
            lon2 = coords_dict.get(cp_dest, {}).get('longitude')
            
            dist_km, tiempo_m = obtener_ruta_vehicular(lon1, lat1, lon2, lat2)
            distancias_reales.append(dist_km)
            tiempos_manejo.append(tiempo_m)
            orientaciones.append(obtener_orientacion(lat1, lon1, lat2, lon2))
            
            # URL de Google Maps corregida para que funcione como enlace
            url = "https://" + "www.google.com" + "/maps/dir/?api=1&origin=" + cp_orig + ",+Mexico&destination=" + cp_dest + ",+Mexico"
            enlaces_maps.append(url)
            
            time.sleep(0.3)
            
            porcentaje = int(((i + 1) / filas_lote) * 100)
            barra_progreso.progress(porcentaje)
            texto_progreso.text(f"Procesando fila {i + 1} de {filas_lote} del lote actual...")
        
        # --- CREACIÓN DE LA TABLA LIMPIA Y PERFECTA ---
        # Se genera un dataframe 100% nuevo para evitar choques con columnas ocultas del Excel original
        df_limpio = pd.DataFrame({
            'CP Origen': df_lote.iloc[:, 0],
            'CP Destino': df_lote.iloc[:, 1],
            'Distancia Carretera (Kms)': distancias_reales,
            'Orientación': orientaciones,
            'Tiempo Manejo (Minutos)': tiempos_manejo,
            'URL Maps': enlaces_maps
        })
        
        st.session_state.resultados = df_limpio
        texto_progreso.empty()
        barra_progreso.empty()

    if st.session_state.resultados is not None:
        st.success(f"¡Lote de la fila {inicio} a la {fin} procesado con éxito!")
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            st.session_state.resultados.to_excel(writer, index=False, sheet_name='Rutas')
        
        st.download_button(
            label=f"📥 DESCARGAR LOTE (Filas {inicio} a {fin}) EN EXCEL",
            data=buffer.getvalue(),
            file_name=f"Resultados_Rutas_{inicio}_a_{fin}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        st.dataframe(st.session_state.resultados)
