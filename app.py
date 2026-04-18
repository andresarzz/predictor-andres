import streamlit as st
import numpy as np
import pandas as pd
from scipy.stats import poisson, norm
import plotly.express as px

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Predictor Elite - Andres Araya", page_icon="🏦", layout="wide")

# --- FUNCIONES MATEMÁTICAS Y MONTE CARLO ---
def calcular_poisson_ou(esperado, linea):
    if linea % 1 == 0:
        prob_under = sum(poisson.pmf(i, esperado) for i in range(int(linea)))
    else:
        prob_under = sum(poisson.pmf(i, esperado) for i in range(int(linea + 0.5)))
    return round(prob_under * 100, 2), round((1 - prob_under) * 100, 2)

def simulacion_monte_carlo(xg_l, xg_v, sims=10000):
    """Simula el partido 10,000 veces para absorber la varianza del deporte."""
    goles_l = np.random.poisson(xg_l, sims)
    goles_v = np.random.poisson(xg_v, sims)
    return goles_l, goles_v

def prop_baloncesto_norm(promedio, desviacion, linea):
    """Usa distribución normal para calcular Player Props (Ej. Puntos de un jugador)."""
    prob_under = norm.cdf(linea, loc=promedio, scale=desviacion)
    return round(prob_under * 100, 2), round((1 - prob_under) * 100, 2)

# --- INTERFAZ ---
st.title("🏦 Sistema Predictivo Institucional y Gestión")
st.markdown("Plataforma algorítmica para análisis cuantitativo y flujo de caja.")

# --- TABS PRINCIPALES ---
tab_futbol, tab_baloncesto, tab_escaner, tab_finanzas = st.tabs([
    "⚽ Fútbol (Monte Carlo)", 
    "🏀 Baloncesto (Props)", 
    "🎯 Escáner de Valor", 
    "📈 Plan Financiero 30 Días"
])

# ==========================================
# TAB 1: FÚTBOL CON MONTE CARLO
# ==========================================
with tab_futbol:
    st.header("Simulador Monte Carlo (10,000 Iteraciones)")
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        xg_l = st.number_input("xG Local (Fútbol)", value=1.65, step=0.1)
    with col_f2:
        xg_v = st.number_input("xG Visitante (Fútbol)", value=1.20, step=0.1)
    
    # Ejecutar simulación
    sim_l, sim_v = simulacion_monte_carlo(xg_l, xg_v)
    total_goles_sim = sim_l + sim_v
    
    linea_g = st.select_slider("Línea de Goles (Secuencia 0.5)", options=[i/2 for i in range(1, 13)], value=2.5)
    
    # Calcular probabilidades basadas en 10,000 resultados reales simulados
    if linea_g % 1 == 0:
        under_sim = np.mean(total_goles_sim < linea_g) * 100
    else:
        under_sim = np.mean(total_goles_sim <= int(linea_g)) * 100
        
    over_sim = 100 - under_sim
    
    c1, c2, c3 = st.columns(3)
    c1.metric(f"Over {linea_g} (Monte Carlo)", f"{round(over_sim, 2)}%")
    c2.metric(f"Under {linea_g} (Monte Carlo)", f"{round(under_sim, 2)}%")
    
    btts_sim = np.mean((sim_l > 0) & (sim_v > 0)) * 100
    c3.metric("Ambos Anotan (Sí)", f"{round(btts_sim, 2)}%")

# ==========================================
# TAB 2: BALONCESTO & PLAYER PROPS
# ==========================================
with tab_baloncesto:
    st.header("Análisis de Player Props (Baloncesto)")
    st.markdown("Calcula el valor en líneas de puntos, rebotes o asistencias de jugadores.")
    
    col_b1, col_b2, col_b3 = st.columns(3)
    with col_b1:
        promedio_jugador = st.number_input("Promedio del Jugador", value=22.5, step=0.5)
    with col_b2:
        desviacion_std = st.number_input("Desviación Estándar", value=4.5, step=0.1, help="Variabilidad en sus puntos (ej. 4.5)")
    with col_b3:
        linea_prop = st.select_slider("Línea de la Casa (Over/Under)", options=[i/2 for i in range(10, 81)], value=23.5)
        
    u_prop, o_prop = prop_baloncesto_norm(promedio_jugador, desviacion_std, linea_prop)
    
    st.divider()
    cb1, cb2 = st.columns(2)
    cb1.metric(f"Probabilidad Over {linea_prop}", f"{o_prop}%")
    cb2.metric(f"Probabilidad Under {linea_prop}", f"{u_prop}%")

# ==========================================
# TAB 3: ESCÁNER DE VALOR (ESTRATEGIA > 1.30)
# ==========================================
with tab_escaner:
    st.header("Escáner de Liquidez (+EV)")
    st.markdown("Ingresa la cuota ofrecida por la plataforma. El sistema filtrará y validará si cumple con el riesgo estructural.")
    
    cuota_ofrecida = st.number_input("Cuota a evaluar", min_value=1.01, value=1.35, step=0.01)
    prob_requerida = (1 / cuota_ofrecida) * 100
    
    st.info(f"Para que la cuota de **{cuota_ofrecida}** sea rentable a largo plazo, tu modelo debe calcular una probabilidad real mayor al **{round(prob_requerida, 2)}%**.")
    
    if cuota_ofrecida >= 1.30:
        st.success("✅ La cuota cumple con el perfil de riesgo base (≥ 1.30).")
    else:
        st.warning("⚠️ Cuota de alto riesgo por baja rentabilidad (menor a 1.30). Se requiere un win-rate extremo para ser rentable.")

# ==========================================
# TAB 4: PLAN FINANCIERO 30 DÍAS (RETIROS SEMANALES)
# ==========================================
with tab_finanzas:
    st.header("Proyección de Bankroll a 30 Días")
    
    col_fin1, col_fin2, col_fin3 = st.columns(3)
    with col_fin1:
        capital_inicial = st.number_input("Capital Inicial (Colones)", min_value=100, value=2000, step=500)
    with col_fin2:
        crecimiento_diario = st.number_input("Crecimiento Diario Esperado (%)", min_value=0.1, value=2.5, step=0.1)
    with col_fin3:
        retiro_semanal = st.number_input("Retiro Semanal (% de Utilidad)", min_value=0.0, value=50.0, step=5.0)

    # Generar tabla de 30 días
    dias = []
    capital_actual = capital_inicial
    retiros_acumulados = 0
    
    for dia in range(1, 31):
        ganancia_dia = capital_actual * (crecimiento_diario / 100)
        capital_actual += ganancia_dia
        retiro_hoy = 0
        
        # Retiro semanal (días 7, 14, 21, 28)
        if dia % 7 == 0:
            utilidad_semana = capital_actual - capital_inicial
            if utilidad_semana > 0:
                retiro_hoy = utilidad_semana * (retiro_semanal / 100)
                capital_actual -= retiro_hoy
                retiros_acumulados += retiro_hoy
                capital_inicial = capital_actual # Reiniciar base para la siguiente semana
                
        dias.append({
            "Día": dia,
            "Bankroll (₡)": round(capital_actual, 2),
            "Ganancia Diaria (₡)": round(ganancia_dia, 2),
            "Retiro (₡)": round(retiro_hoy, 2)
        })
        
    df_finanzas = pd.DataFrame(dias)
    
    st.write(f"**Retiros Totales Proyectados en 30 días:** ₡ {round(retiros_acumulados, 2)}")
    st.dataframe(df_finanzas, use_container_width=True, hide_index=True)

# --- FOOTER ---
st.markdown("---")
st.markdown("""
    <div style='text-align: center; color: #888; padding: 20px;'>
        <p style='font-size: 16px;'>Creado por <strong>Andres Araya</strong> | 🏦 Sistema Predictivo Institucional v4.0</p>
    </div>
""", unsafe_allow_html=True)
