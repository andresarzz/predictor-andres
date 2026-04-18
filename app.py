import streamlit as st
import numpy as np
import pandas as pd
from scipy.stats import poisson, norm
import plotly.graph_objects as go
import plotly.express as px

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Predictor Elite", page_icon="⚡", layout="wide")

# --- FUNCIONES MATEMÁTICAS ---
def calcular_poisson_ou(esperado, linea):
    """Calcula Over/Under respetando secuencias de 0.5 y enteros."""
    if linea % 1 == 0:
        prob_under = sum(poisson.pmf(i, esperado) for i in range(int(linea)))
    else:
        prob_under = sum(poisson.pmf(i, esperado) for i in range(int(linea + 0.5)))
    return round(prob_under * 100, 2), round((1 - prob_under) * 100, 2)

def matriz_dixon_coles(lambda_l, lambda_v, rho=-0.15, max_goles=6):
    matriz = np.zeros((max_goles+1, max_goles+1))
    for i in range(max_goles+1):
        for j in range(max_goles+1):
            prob_base = poisson.pmf(i, lambda_l) * poisson.pmf(j, lambda_v)
            if i == 0 and j == 0: ajuste = 1 - (lambda_l * lambda_v * rho)
            elif i == 1 and j == 0: ajuste = 1 + (lambda_v * rho)
            elif i == 0 and j == 1: ajuste = 1 + (lambda_l * rho)
            elif i == 1 and j == 1: ajuste = 1 - rho
            else: ajuste = 1.0
            matriz[i][j] = max(0, prob_base * ajuste)
    return matriz / matriz.sum()

def prop_baloncesto_norm(promedio, desviacion, linea):
    prob_under = norm.cdf(linea, loc=promedio, scale=desviacion)
    return round(prob_under * 100, 2), round((1 - prob_under) * 100, 2)

def calcular_kelly(prob_real, cuota_bookie):
    """Calcula el porcentaje de banca a apostar según el Criterio de Kelly (fraccionado 1/4)."""
    if cuota_bookie <= 1.0: return 0.0
    p = prob_real / 100
    q = 1 - p
    b = cuota_bookie - 1
    kelly_pct = ((p * b) - q) / b
    # Recomendamos un cuarto de Kelly para proteger la banca
    return max(0, round((kelly_pct * 100) / 4, 2))

# --- INTERFAZ PRINCIPAL ---
st.title("⚡ Motor Cuantitativo de Análisis Deportivo")
st.markdown("Evaluación estadística avanzada para mercados de fútbol y baloncesto.")

# --- TABS PRINCIPALES ---
tab_futbol, tab_graficos, tab_baloncesto, tab_escaner = st.tabs([
    "⚽ Fútbol (Mercados)", 
    "📊 Gráficos de Distribución",
    "🏀 Baloncesto (Props)", 
    "🎯 Escáner de Valor (+EV & Kelly)"
])

# ==========================================
# BARRA LATERAL (DATOS GLOBALES DE FÚTBOL)
# ==========================================
st.sidebar.header("⚙️ Entrada de Datos (Fútbol)")
col_sf1, col_sf2 = st.sidebar.columns(2)
with col_sf1:
    st.subheader("Local")
    xg_l = st.number_input("xG Local", value=1.6, step=0.1)
    cl = st.number_input("Córners L", value=5.5, step=0.1)
    dl = st.number_input("Remates Tot. L", value=12.0, step=0.5)
    dpl = st.number_input("A Puerta L", value=4.5, step=0.1)
with col_sf2:
    st.subheader("Visita")
    xg_v = st.number_input("xG Visita", value=1.2, step=0.1)
    cv = st.number_input("Córners V", value=4.2, step=0.1)
    dv = st.number_input("Remates Tot. V", value=10.0, step=0.5)
    dpv = st.number_input("A Puerta V", value=3.2, step=0.1)

# ==========================================
# TAB 1: FÚTBOL (GOLES, CÓRNERS, REMATES)
# ==========================================
with tab_futbol:
    sub_goles, sub_corners, sub_remates = st.tabs(["🥅 Goles", "🚩 Córners", "👟 Remates y Puerta"])
    
    with sub_goles:
        st.subheader("Mercado de Goles (Dixon-Coles)")
        linea_g = st.select_slider("Línea de Goles", options=[i/2 for i in range(1, 13)], value=2.5)
        matriz = matriz_dixon_coles(xg_l, xg_v)
        
        prob_under_g = 0
        for i in range(len(matriz)):
            for j in range(len(matriz)):
                if i + j < linea_g: prob_under_g += matriz[i][j]
                
        cg1, cg2, cg3 = st.columns(3)
        cg1.metric(f"Over {linea_g}", f"{round((1-prob_under_g)*100, 2)}%")
        cg2.metric(f"Under {linea_g}", f"{round(prob_under_g*100, 2)}%")
        
        p_cero_l = matriz[0, :].sum()
        p_cero_v = matriz[:, 0].sum()
        btts_si = (1 - (p_cero_l + p_cero_v - matriz[0,0])) * 100
        cg3.metric("Ambos Anotan (Sí)", f"{round(btts_si, 2)}%")

    with sub_corners:
        st.subheader("Tiros de Esquina")
        linea_c = st.select_slider("Línea Córners Totales", options=[i/2 for i in range(10, 31)], value=9.5)
        u_c, o_c = calcular_poisson_ou(cl + cv, linea_c)
        cc1, cc2 = st.columns(2)
        cc1.metric(f"Over {linea_c}", f"{o_c}%")
        cc2.metric(f"Under {linea_c}", f"{u_c}%")

    with sub_remates:
        st.subheader("Remates Totales en el Partido")
        linea_d = st.select_slider("Línea Remates Totales", options=[i/2 for i in range(30, 71)], value=24.5)
        u_d, o_d = calcular_poisson_ou(dl + dv, linea_d)
        cd1, cd2 = st.columns(2)
        cd1.metric(f"Over {linea_d}", f"{o_d}%")
        cd2.metric(f"Under {linea_d}", f"{u_d}%")
        
        st.divider()
        st.subheader("Remates a Puerta (Por Equipo)")
        c_puerta1, c_puerta2 = st.columns(2)
        with c_puerta1:
            l_dpl = st.select_slider("Línea Puerta Local", options=[i/2 for i in range(2, 17)], value=4.5)
            u_dpl, o_dpl = calcular_poisson_ou(dpl, l_dpl)
            st.metric(f"Local Over {l_dpl}", f"{o_dpl}%")
        with c_puerta2:
            l_dpv = st.select_slider("Línea Puerta Visita", options=[i/2 for i in range(2, 17)], value=3.5)
            u_dpv, o_dpv = calcular_poisson_ou(dpv, l_dpv)
            st.metric(f"Visita Over {l_dpv}", f"{o_dpv}%")

# ==========================================
# TAB 2: GRÁFICOS VISUALES (POISSON)
# ==========================================
with tab_graficos:
    st.header("Distribución de Probabilidad Exacta")
    st.markdown("Visualiza la probabilidad de que un equipo anote exactamente X cantidad de goles.")
    
    goles_posibles = list(range(6))
    prob_l = [poisson.pmf(i, xg_l) * 100 for i in goles_posibles]
    prob_v = [poisson.pmf(i, xg_v) * 100 for i in goles_posibles]
    
    fig = go.Figure(data=[
        go.Bar(name='Local', x=goles_posibles, y=prob_l, marker_color='#1f77b4', text=[f"{p:.1f}%" for p in prob_l], textposition='auto'),
        go.Bar(name='Visitante', x=goles_posibles, y=prob_v, marker_color='#ff7f0e', text=[f"{p:.1f}%" for p in prob_v], textposition='auto')
    ])
    fig.update_layout(barmode='group', xaxis_title='Goles Exactos', yaxis_title='Probabilidad (%)',
                      title="Comparativa de Fuerza Ofensiva (xG)")
    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# TAB 3: BALONCESTO & PLAYER PROPS
# ==========================================
with tab_baloncesto:
    st.header("Análisis de Player Props (Baloncesto)")
    col_b1, col_b2, col_b3 = st.columns(3)
    with col_b1:
        promedio_jugador = st.number_input("Promedio del Jugador", value=22.5, step=0.5)
    with col_b2:
        desviacion_std = st.number_input("Desviación Estándar", value=4.5, step=0.1)
    with col_b3:
        linea_prop = st.select_slider("Línea de la Casa (Baloncesto)", options=[i/2 for i in range(10, 81)], value=23.5)
        
    u_prop, o_prop = prop_baloncesto_norm(promedio_jugador, desviacion_std, linea_prop)
    cb1, cb2 = st.columns(2)
    cb1.metric(f"Over {linea_prop}", f"{o_prop}%")
    cb2.metric(f"Under {linea_prop}", f"{u_prop}%")

# ==========================================
# TAB 4: ESCÁNER DE VALOR Y GESTIÓN DE RIESGO
# ==========================================
with tab_escaner:
    st.header("Escáner de Valor Esperado (+EV) y Stake")
    st.markdown("Ideal para evaluar rápidamente cuotas de bajo riesgo (ej. 1.30) en slates de múltiples partidos.")
    
    col_esc1, col_esc2 = st.columns(2)
    with col_esc1:
        prob_modelo = st.number_input("Probabilidad Real calculada por el modelo (%)", min_value=1.0, max_value=99.9, value=80.0, step=0.5)
    with col_esc2:
        cuota_bookie = st.number_input("Cuota ofrecida en la casa de apuestas", min_value=1.01, value=1.30, step=0.01)
        
    prob_implicita = (1 / cuota_bookie) * 100
    ev = ( (prob_modelo / 100) * cuota_bookie ) - 1
    kelly_recomendado = calcular_kelly(prob_modelo, cuota_bookie)
    
    st.divider()
    
    if ev > 0:
        st.success(f"✅ **VENTAJA MATEMÁTICA DETECTADA**")
        res1, res2, res3 = st.columns(3)
        res1.metric("Valor Esperado (+EV)", f"+{round(ev * 100, 2)}%")
        res2.metric("Probabilidad Implícita", f"{round(prob_implicita, 2)}%", "La casa asume esta probabilidad", delta_color="off")
        res3.metric("Stake Sugerido (Kelly %)", f"{kelly_recomendado}%", "Porcentaje de tu bankroll a invertir")
    else:
        st.error(f"❌ **SIN VALOR (EV NEGATIVO)**")
        st.write(f"La cuota de {cuota_bookie} exige una probabilidad mínima de {round(prob_implicita, 2)}%, pero el modelo solo otorga {prob_modelo}%. A largo plazo, apostar aquí genera pérdidas.")

# --- FOOTER ---
st.markdown("---")
st.markdown("""
    <div style='text-align: center; color: #888; padding: 20px;'>
        <p style='font-size: 16px;'>Creado por <strong>Andres Araya</strong> | ⚡ Predictor Estadístico PRO</p>
    </div>
""", unsafe_allow_html=True)
