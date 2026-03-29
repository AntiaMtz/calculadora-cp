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
    col