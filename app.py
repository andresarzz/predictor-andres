import streamlit as st
import numpy as np
from scipy.stats import poisson

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Predictor Pro v2 - Andres Araya", page_icon="📈", layout="wide")

# --- FUNCIONES MATEMÁTICAS ---
def calcular_poisson_ou(esperado, linea):
    # Para líneas como 1.0, "Under" significa estrictamente menos que 1 (solo 0).
    # Para líneas como 1.5, "Under" significa 0 o 1.
    prob_under = sum(poisson.pmf(i, esperado) for i in range(int(np.ceil(linea))))
    # Si la línea es un entero (ej: 1.0), sumamos hasta 0. 
    # Si es decimal (ej: 1.5), sumamos hasta 1.
    if linea % 1 == 0:
        prob_under = sum(poisson.pmf(i, esperado) for i in range(int(linea)))
    else:
        prob_under = sum(poisson.pmf(i, esperado) for i in range(int(linea + 0.5)))
        
    return round(prob_under * 100, 2), round((1 - prob_under) * 100, 2)

def matriz_dixon_coles(lambda_l, lambda_v, rho=-0.15, max_goles=7):
    matriz = np.zeros((max_goles+1, max_goles+1))
    for i in range(max_goles+1):
        for j in range(max_goles+1):
            prob_base = poisson.pmf(i, lambda_l) * poisson.pmf(j, lambda_v)
            if i == 0 and j == 0:
                ajuste = 1 - (lambda_l * lambda_v * rho)
            elif i == 1 and j == 0:
                ajuste = 1 + (lambda_v * rho)
            elif i == 0 and j == 1:
                ajuste = 1 + (lambda_l * rho)
            elif i == 1 and j == 1:
                ajuste = 1 - rho
            else:
                ajuste = 1.0
            matriz[i][j] = max(0, prob_base * ajuste)
    return matriz / matriz.sum()

# --- INTERFAZ ---
st.title("⚽ Sistema Predictivo: Motor Dixon-Coles")
st.markdown("Análisis estadístico profesional para mercados de goles, córners y disparos.")

# --- SIDEBAR: ENTRADA DE DATOS ---
st.sidebar.header("📊 Datos de Entrada (xG)")
col1, col2 = st.sidebar.columns(2)
with col1:
    st.subheader("Local")
    xg_l = st.number_input("xG a favor", min_value=0.0, value=1.6, step=0.1)
    cl = st.number_input("Córners Prom.", min_value=0.0, value=5.5, step=0.1)
    dl = st.number_input("Tiros Prom.", min_value=0.0, value=12.0, step=0.5)
    dpl = st.number_input("A Puerta Prom.", min_value=0.0, value=4.5, step=0.1)
with col2:
    st.subheader("Visitante")
    xg_v = st.number_input("xG en contra", min_value=0.0, value=1.2, step=0.1)
    cv = st.number_input("Córners Prom.", min_value=0.0, value=4.2, step=0.1)
    dv = st.number_input("Tiros Prom.", min_value=0.0, value=10.0, step=0.5)
    dpv = st.number_input("A Puerta Prom.", min_value=0.0, value=3.2, step=0.1)

# --- TABS DE MERCADOS ---
tab_goles, tab_corners, tab_disparos = st.tabs(["🥅 Goles", "🚩 Córners", "👟 Disparos"])

with tab_goles:
    st.header("Mercado de Goles (Secuencia 0.5, 1, 1.5...)")
    # Línea dinámica con pasos de 0.5
    linea_g = st.select_slider("Selecciona línea de Goles", options=[i/2 for i in range(1, 13)], value=2.5)
    
    matriz = matriz_dixon_coles(xg_l, xg_v)
    prob_under_g = 0
    for i in range(len(matriz)):
        for j in range(len(matriz)):
            if i + j < linea_g: prob_under_g += matriz[i][j]
    
    col_g1, col_g2, col_g3 = st.columns(3)
    col_g1.metric(f"Over {linea_g}", f"{round((1-prob_under_g)*100, 2)}%")
    col_g2.metric(f"Under {linea_g}", f"{round(prob_under_g*100, 2)}%")
    
    # Ambos Anotan
    p_cero_l = matriz[0, :].sum()
    p_cero_v = matriz[:, 0].sum()
    btts_si = (1 - (p_cero_l + p_cero_v - matriz[0,0])) * 100
    col_g3.metric("Ambos Anotan (Sí)", f"{round(btts_si, 2)}%")

with tab_corners:
    st.header("Análisis de Córners")
    linea_c = st.select_slider("Selecciona línea de Córners", options=[i/2 for i in range(10, 31)], value=9.5)
    u_c, o_c = calcular_poisson_ou(cl + cv, linea_c)
    c1, c2 = st.columns(2)
    c1.metric(f"Over {linea_c}", f"{o_c}%")
    c2.metric(f"Under {linea_c}", f"{u_c}%")

with tab_disparos:
    st.header("Análisis de Disparos")
    linea_d = st.select_slider("Línea Disparos Totales", options=[float(i) for i in range(15, 36)], value=24.0)
    u_d, o_d = calcular_poisson_ou(dl + dv, linea_d)
    st.metric(f"Total Disparos Over {linea_d}", f"{o_d}%")
    
    st.divider()
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        l_dpl = st.select_slider("Línea Puerta Local", options=[i/2 for i in range(2, 16)], value=4.5)
        _, o_dpl = calcular_poisson_ou(dpl, l_dpl)
        st.metric(f"Local Puerta Over {l_dpl}", f"{o_dpl}%")
    with col_d2:
        l_dpv = st.select_slider("Línea Puerta Visita", options=[i/2 for i in range(2, 16)], value=3.5)
        _, o_dpv = calcular_poisson_ou(dpv, l_dpv)
        st.metric(f"Visita Puerta Over {l_dpv}", f"{o_dpv}%")

# --- FOOTER PERSONALIZADO ---
st.markdown("---")
st.markdown("""
    <div style='text-align: center; color: #888; padding: 20px;'>
        <p style='font-size: 16px;'>Creado por <strong>Andres Araya</strong> | ⚽ Predictor Estadístico PRO</p>
    </div>
""", unsafe_allow_html=True)