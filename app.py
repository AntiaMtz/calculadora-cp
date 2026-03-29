import streamlit as st
import pandas as pd
import pgeocode
import math

st.set_page_config(page_title="Calculadora de CPs", layout="wide")
st.title("Sin Limits")

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

    if st.button("🚀 Calcular Distancias y Orientación"):
        with st.spinner('Procesando las 7,644 combinaciones...'):
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
                
                lat1 = coords_dict.get(cp_orig, {}).get('latitude')
                lon1 = coords_dict.get(cp_orig, {}).get('longitude')
                lat2 = coords_dict.get(cp_dest, {}).get('latitude')
                lon2 = coords_dict.get(cp_dest, {}).get('longitude')
                
                orientaciones.append(obtener_orientacion(lat1, lon1, lat2, lon2))
                
            if len(df.columns) >= 4:
                df[df.columns[2]] = distancias
                df[df.columns[3]] = orientaciones
            else:
                df['Distancia (Kms)'] = distancias
                df['Orientacion'] = orientaciones
            
            df_final = df.drop(columns=['CP_Origen_str', 'CP_Destino_str'])
            st.session_state.resultados = df_final

    # --- AQUÍ ESTÁ EL CAMBIO CLAVE ---
    if st.session_state.resultados is not None:
        st.success("¡Cálculo terminado con éxito!")
        
        # EL BOTÓN APARECE HASTA ARRIBA PARA QUE NO TENGAS QUE BAJAR
        csv = st.session_state.resultados.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 HAZ CLIC AQUÍ PARA DESCARGAR TU ARCHIVO",
            data=csv,
            file_name="Resultados_CPs_Calculados.csv",
            mime="text/csv"
        )
        
        st.write("### Vista previa de la tabla completa:")
        st.dataframe(st.session_state.resultados)
