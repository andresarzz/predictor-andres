import streamlit as st
import numpy as np
from scipy.stats import poisson
import plotly.express as px

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Predictor Pro +EV - Andres Araya", page_icon="💰", layout="wide")

# --- FUNCIONES MATEMÁTICAS ---
def calcular_poisson_ou(esperado, linea):
    if linea % 1 == 0:
        prob_under = sum(poisson.pmf(i, esperado) for i in range(int(linea)))
    else:
        prob_under = sum(poisson.pmf(i, esperado) for i in range(int(linea + 0.5)))
    return round(prob_under * 100, 2), round((1 - prob_under) * 100, 2)

def matriz_dixon_coles(lambda_l, lambda_v, rho=-0.15, max_goles=5):
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

def calcular_kelly(prob_decimal, cuota, bankroll, fraccion=0.25):
    # Kelly = (p*b - q) / b  donde b = cuota - 1
    if cuota <= 1: return 0, 0
    p = prob_decimal
    q = 1 - p
    b = cuota - 1
    f_kelly = (p * b - q) / b
    recomendacion = max(0, f_kelly * bankroll * fraccion) # Kelly fraccionado para seguridad
    return round(f_kelly * 100 * fraccion, 2), round(recomendacion, 2)

# --- INTERFAZ ---
st.title("⚽ Predictor Elite: Análisis +EV y Gestión de Banca")

# --- SIDEBAR: DATOS Y BANKROLL ---
st.sidebar.header("🏦 Tu Gestión de Banca")
bankroll = st.sidebar.number_input("Tu Capital Total ($)", min_value=0.0, value=1000.0, step=100.0)
riesgo = st.sidebar.select_slider("Perfil de Riesgo", options=["Conservador", "Moderado", "Agresivo"], value="Moderado")
frac_dict = {"Conservador": 0.1, "Moderado": 0.25, "Agresivo": 0.5}

st.sidebar.divider()
st.sidebar.header("📊 Datos del Partido (xG)")
col_s1, col_s2 = st.sidebar.columns(2)
with col_s1:
    xg_l = st.number_input("xG Local", value=1.6)
    cl = st.number_input("Córners L", value=5.5)
with col_s2:
    xg_v = st.number_input("xG Visita", value=1.2)
    cv = st.number_input("Córners V", value=4.2)

# --- CÁLCULO DE MATRIZ ---
matriz = matriz_dixon_coles(xg_l, xg_v)

# --- TABS ---
tab_goles, tab_heatmap, tab_otros = st.tabs(["🥅 Análisis de Valor", "🔥 Mapa de Calor", "🚩 Otros Mercados"])

with tab_goles:
    st.header("Calculadora de Valor Esperado (+EV)")
    st.info("Ingresa la cuota de tu casa de apuestas para ver si tiene valor.")
    
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        linea_g = st.select_slider("Línea de Goles", options=[i/2 for i in range(1, 11)], value=2.5)
        cuota_bookie = st.number_input("Cuota de la Casa (ej: 1.95)", min_value=1.01, value=1.90, step=0.05)
    
    # Cálculo Over/Under
    prob_under_g = 0
    for i in range(len(matriz)):
        for j in range(len(matriz)):
            if i + j < linea_g: prob_under_g += matriz[i][j]
    prob_over_g = 1 - prob_under_g
    
    # Análisis de Valor
    ev = (prob_over_g * cuota_bookie) - 1
    pct_kelly, monto_recom = calcular_kelly(prob_over_g, cuota_bookie, bankroll, frac_dict[riesgo])
    
    with col_g2:
        st.subheader("Resultado del Análisis")
        if ev > 0:
            st.success(f"✅ ¡VALOR DETECTADO! EV: +{round(ev*100, 2)}%")
            st.metric("Sugerencia de Apuesta", f"${monto_recom}", f"{pct_kelly}% del bank")
        else:
            st.error(f"❌ SIN VALOR. EV: {round(ev*100, 2)}%")
            st.write("La cuota es muy baja para la probabilidad real.")

    st.divider()
    # Métricas rápidas
    m1, m2, m3 = st.columns(3)
    m1.metric("Prob. Over", f"{round(prob_over_g*100, 2)}%")
    m2.metric("Prob. Under", f"{round(prob_under_g*100, 2)}%")
    p_cero_l = matriz[0, :].sum()
    p_cero_v = matriz[:, 0].sum()
    btts_si = (1 - (p_cero_l + p_cero_v - matriz[0,0])) * 100
    m3.metric("Ambos Anotan (Sí)", f"{round(btts_si, 2)}%")

with tab_heatmap:
    st.header("Probabilidad de Marcadores Exactos")
    # Crear Heatmap con Plotly
    fig = px.imshow(matriz * 100,
                    labels=dict(x="Goles Visitante", y="Goles Local", color="Prob %"),
                    x=[str(i) for i in range(6)],
                    y=[str(i) for i in range(6)],
                    text_auto=".1f",
                    color_continuous_scale="Viridis")
    fig.update_layout(title_text="Mapa de Calor: Resultados Probables")
    st.plotly_chart(fig, use_container_width=True)

with tab_otros:
    st.header("Córners y Disparos")
    linea_c = st.select_slider("Línea Córners", options=[i/2 for i in range(14, 26)], value=9.5)
    u_c, o_c = calcular_poisson_ou(cl + cv, linea_c)
    c1, c2 = st.columns(2)
    c1.metric("Over Córners", f"{o_c}%")
    c2.metric("Under Córners", f"{u_c}%")

# --- FOOTER ---
st.markdown("---")
st.markdown(f"""
    <div style='text-align: center; color: #888; padding: 20px;'>
        <p style='font-size: 16px;'>Creado por <strong>Andres Araya</strong> | ⚽ Predictor Elite v3.0</p>
        <p style='font-size: 12px;'>Gestión de Banca actual: ${bankroll} ({riesgo})</p>
    </div>
""", unsafe_allow_html=True)
