import streamlit as st
import numpy as np
import pandas as pd
from scipy.stats import poisson, norm
import plotly.express as px

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Predictor Elite", page_icon="📈", layout="wide")

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

# --- INTERFAZ PRINCIPAL ---
st.title("🏦 Sistema Predictivo y Gestión de Capital")

# --- TABS PRINCIPALES ---
tab_futbol, tab_baloncesto, tab_escaner, tab_finanzas = st.tabs([
    "⚽ Fútbol (Análisis Total)", 
    "🏀 Baloncesto (Props)", 
    "🎯 Escáner de Valor", 
    "📈 Plan Financiero 30 Días"
])

# ==========================================
# TAB 1: FÚTBOL (GOLES, CÓRNERS, REMATES)
# ==========================================
with tab_futbol:
    st.sidebar.header("📊 Promedios Fútbol")
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

    # Sub-tabs para organizar los mercados de fútbol
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
# TAB 2: BALONCESTO & PLAYER PROPS
# ==========================================
with tab_baloncesto:
    st.header("Análisis de Player Props (Baloncesto)")
    col_b1, col_b2, col_b3 = st.columns(3)
    with col_b1:
        promedio_jugador = st.number_input("Promedio del Jugador", value=22.5, step=0.5)
    with col_b2:
        desviacion_std = st.number_input("Desviación Estándar", value=4.5, step=0.1)
    with col_b3:
        linea_prop = st.select_slider("Línea de la Casa", options=[i/2 for i in range(10, 81)], value=23.5)
        
    u_prop, o_prop = prop_baloncesto_norm(promedio_jugador, desviacion_std, linea_prop)
    cb1, cb2 = st.columns(2)
    cb1.metric(f"Over {linea_prop}", f"{o_prop}%")
    cb2.metric(f"Under {linea_prop}", f"{u_prop}%")

# ==========================================
# TAB 3: ESCÁNER DE VALOR
# ==========================================
with tab_escaner:
    st.header("Evaluador de Cuotas de Bajo Riesgo")
    cuota_ofrecida = st.number_input("Cuota a evaluar (ej: DoradoBet)", min_value=1.01, value=1.30, step=0.01)
    prob_requerida = (1 / cuota_ofrecida) * 100
    st.info(f"Para que la cuota de **{cuota_ofrecida}** sea rentable, el modelo en la pestaña de análisis debe mostrar una probabilidad mayor al **{round(prob_requerida, 2)}%**.")

# ==========================================
# TAB 4: PLAN FINANCIERO CORREGIDO
# ==========================================
with tab_finanzas:
    st.header("Proyección de Bankroll y Retiros Lógicos")
    
    col_fin1, col_fin2, col_fin3 = st.columns(3)
    with col_fin1:
        capital_inicial = st.number_input("Capital Inicial (Colones)", min_value=100, value=2000, step=500)
    with col_fin2:
        crecimiento_diario = st.number_input("Crecimiento Diario (%)", min_value=0.1, value=2.5, step=0.1)
    with col_fin3:
        porcentaje_retiro = st.number_input("Retiro Semanal (% de Utilidad)", min_value=0.0, value=50.0, step=5.0)

    # LÓGICA CORREGIDA
    dias = []
    bankroll_actual = capital_inicial
    base_semana = capital_inicial
    retiros_totales = 0
    
    for dia in range(1, 31):
        ganancia_del_dia = bankroll_actual * (crecimiento_diario / 100)
        bankroll_actual += ganancia_del_dia
        retiro_hoy = 0
        
        # Evaluar el día 7 de cada ciclo
        if dia % 7 == 0:
            utilidad_semana = bankroll_actual - base_semana
            if utilidad_semana > 0:
                retiro_hoy = utilidad_semana * (porcentaje_retiro / 100)
                bankroll_actual -= retiro_hoy
                retiros_totales += retiro_hoy
            # Resetear la base para medir el rendimiento de la nueva semana
            base_semana = bankroll_actual 
                
        dias.append({
            "Día": dia,
            "Bankroll (₡)": round(bankroll_actual, 2),
            "Utilidad del Día (₡)": round(ganancia_del_dia, 2),
            "Retiro a Banco (₡)": round(retiro_hoy, 2)
        })
        
    df_finanzas = pd.DataFrame(dias)
    
    st.success(f"**Beneficio Extraído (Retiros Totales en 30 días):** ₡ {round(retiros_totales, 2)}")
    st.dataframe(df_finanzas, use_container_width=True, hide_index=True)

# --- FOOTER ---
st.markdown("---")
st.markdown("""
    <div style='text-align: center; color: #888; padding: 20px;'>
        <p style='font-size: 16px;'>Creado por <strong>Andres Araya</strong> | 🏦 Sistema Predictivo Institucional</p>
    </div>
""", unsafe_allow_html=True)
