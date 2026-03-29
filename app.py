import streamlit as st
import pandas as pd
import pgeocode
import math
import folium
from streamlit_folium import st_folium

# Configuración de página
st.set_page_config(page_title="Calculadora de CPs", layout="wide")
st.title("📍 Calculadora de Distancia y Orientación entre Códigos Postales")

# Función para calcular el ángulo y la orientación
def obtener_orientacion(lat1, lon1, lat2, lon2):
    if pd.isna(lat1) or pd.isna(lon1) or pd.isna(lat2) or pd.isna(lon2):
        return "N/A"
    
    # Diferencia de coordenadas
    dLon = lon2 - lon1
    y = math.sin(math.radians(dLon)) * math.cos(math.radians(lat2))
    x = math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - \
        math.sin(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.cos(math.radians(dLon))
    
    brng = math.atan2(y, x)
    brng = math.degrees(brng)
    brng = (brng + 360) % 360
    
    # 16 Direcciones según lo solicitado
    sectores = ["N", "NNE", "NE", "NEE", "E", "SEE", "SE", "SSE", 
                "S", "SSO", "SO", "SOO", "O", "NOO", "NO", "NNO"]
    
    idx = int((brng + 11.25) / 22.5) % 16
    return sectores[idx]

# Subir archivo
archivo_subido = st.file_uploader("Sube tu archivo Excel o CSV con los CPs", type=["xlsx", "csv"])

if archivo_subido:
    # Leer el archivo dependiendo de su extensión
    if archivo_subido.name.endswith('.csv'):
        df = pd.read_csv(archivo_subido)
    else:
        df = pd.read_excel(archivo_subido)
    
    st.write("### Vista previa de tus datos:")
    st.dataframe(df.head())

    # Asegurarnos de tener las columnas indicadas en la posición correcta o por nombre
    col_origen = df.columns[0]
    col_destino = df.columns[1]

    if st.button("Calcular Distancias y Orientación"):
        with st.spinner('Calculando datos... (Esto puede tardar unos segundos)'):
            # Formatear CPs asegurando que sean texto y tengan 5 dígitos (para México)
            df['CP_Origen_str'] = df[col_origen].astype(str).str.zfill(5)
            df['CP_Destino_str'] = df[col_destino].astype(str).str.zfill(5)
            
            # Inicializar el motor de códigos postales para México
            nomi = pgeocode.Nominatim('mx')
            dist = pgeocode.GeoDistance('mx')
            
            # Obtener Latitud y Longitud para todos los CPs únicos (para no hacer consultas repetidas)
            cps_unicos = pd.concat([df['CP_Origen_str'], df['CP_Destino_str']]).unique()
            df_coords = nomi.query_postal_code(cps_unicos)
            coords_dict = df_coords.set_index('postal_code')[['latitude', 'longitude']].to_dict('index')
            
            distancias = []
            orientaciones = []
            
            for index, row in df.iterrows():
                cp_orig = row['CP_Origen_str']
                cp_dest = row['CP_Destino_str']
                
                # Calcular Distancia en Kms
                d = dist.query_postal_code(cp_orig, cp_dest)
                distancias.append(round(d, 2))
                
                # Obtener coordenadas para la orientación
                lat1, lon1 = coords_dict.get(cp_orig, {}).get('latitude'), coords_dict.get(cp_orig, {}).get('longitude')
                lat2, lon2 = coords_dict.get(cp_dest, {}).get('latitude'), coords_dict.get(cp_dest, {}).get('longitude')
                
                orientacion = obtener_orientacion(lat1, lon1, lat2, lon2)
                orientaciones.append(orientacion)
                
            # Asignar a columnas originales (C y D)
            if len(df.columns) >= 4:
                df[df.columns[2]] = distancias
                df[df.columns[3]] = orientaciones
            else:
                df['Distancia (Kms)'] = distancias
                df['Orientacion'] = orientaciones
            
            # Limpiar columnas temporales
            df = df.drop(columns=['CP_Origen_str', 'CP_Destino_str'])
            
            st.success("¡Cálculo terminado!")
            st.write("### Resultados")
            st.dataframe(df)
            
            # Descargar archivo
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("Descargar Resultados en CSV", csv, "Resultados_CPs.csv", "text/csv")
            
            # Mostrar Mapa Interactivo con una muestra (ej. primeros 50 para no trabar el navegador)
            st.write("### Visualización en Mapa (Mostrando los primeros 50 resultados)")
            mapa = folium.Map(location=[23.6345, -102.5528], zoom_start=5) # Centro de México
            
            for i in range(min(50, len(df))):
                cp_orig = str(df.iloc[i, 0]).zfill(5)
                cp_dest = str(df.iloc[i, 1]).zfill(5)
                
                lat1 = coords_dict.get(cp_orig, {}).get('latitude')
                lon1 = coords_dict.get(cp_orig, {}).get('longitude')
                lat2 = coords_dict.get(cp_dest, {}).get('latitude')
                lon2 = coords_dict.get(cp_dest, {}).get('longitude')
                
                if pd.notna(lat1) and pd.notna(lon1) and pd.notna(lat2) and pd.notna(lon2):
                    folium.Marker([lat1, lon1], popup=f"Origen: {cp_orig}", icon=folium.Icon(color="blue")).add_to(mapa)
                    folium.Marker([lat2, lon2], popup=f"Destino: {cp_dest}", icon=folium.Icon(color="red")).add_to(mapa)
                    folium.PolyLine([(lat1, lon1), (lat2, lon2)], color="green", weight=2, opacity=0.8).add_to(mapa)

            st_folium(mapa, width=1000, height=500)