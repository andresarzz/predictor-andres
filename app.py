import streamlit as st
import numpy as np
from scipy.stats import poisson
import plotly.express as px

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Predictor Elite - Andres Araya", page_icon="💰", layout="wide")

# --- FUNCIONES MATEMÁTICAS ---
def calcular_poisson_ou(esperado, linea):
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

def calcular_kelly(prob_decimal, cuota, bankroll, fraccion=0.25):
    if cuota <= 1: return 0, 0
    p = prob_decimal
    q = 1 - p
    b = cuota - 1
    f_kelly = (p * b - q) / b
    recomendacion = max(0, f_kelly * bankroll * fraccion)
    return round(f_kelly * 100 * fraccion, 2), round(recomendacion, 2)

# --- INTERFAZ ---
st.title("⚽ Predictor Elite: Análisis +EV y Gestión de Banca")

# --- SIDEBAR: DATOS Y BANKROLL ---
st.sidebar.header("🏦 Tu Gestión de Banca")
bankroll = st.sidebar.number_input("Tu Capital Total ($)", min_value=0.0, value=1000.0, step=100.0)
riesgo = st.sidebar.select_slider("Perfil de Riesgo", options=["Conservador", "Moderado", "Agresivo"], value="Moderado")
frac_dict = {"Conservador": 0.1, "Moderado": 0.25, "Agresivo": 0.5}

st.sidebar.divider()
st.sidebar.header("📊 Datos del Partido (Promedios/xG)")
col_s1, col_s2 = st.sidebar.columns(2)
with col_s1:
    st.subheader("Local")
    xg_l = st.number_input("xG Local", value=1.6)
    cl = st.number_input("Córners L", value=5.5)
    dl = st.number_input("Tiros L", value=12.0)
    dpl = st.number_input("A Puerta L", value=4.5)
with col_s2:
    st.subheader("Visita")
    xg_v = st.number_input("xG Visita", value=1.2)
    cv = st.number_input("Córners V", value=4.2)
    dv = st.number_input("Tiros V", value=10.0)
    dpv = st.number_input("A Puerta V", value=3.2)

# --- CÁLCULO DE MATRIZ ---
matriz = matriz_dixon_coles(xg_l, xg_v)

# --- TABS ---
tab_goles, tab_heatmap, tab_corners, tab_disparos = st.tabs(["🥅 Valor (Goles)", "🔥 Marcadores", "🚩 Córners", "👟 Disparos"])

with tab_goles:
    st.header("Calculadora de Valor Esperado (+EV)")
    
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        linea_g = st.select_slider("Línea de Goles", options=[i/2 for i in range(1, 13)], value=2.5)
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
        if ev > 0:
            st.success(f"✅ ¡VALOR DETECTADO! EV: +{round(ev*100, 2)}%")
            st.metric("Sugerencia de Apuesta", f"${monto_recom}", f"{pct_kelly}% del bank")
        else:
            st.error(f"❌ SIN VALOR. EV: {round(ev*100, 2)}%")
            st.write("La cuota es muy baja para la probabilidad real.")

    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric(f"Prob. Over {linea_g}", f"{round(prob_over_g*100, 2)}%")
    m2.metric(f"Prob. Under {linea_g}", f"{round(prob_under_g*100, 2)}%")
    p_cero_l = matriz[0, :].sum()
    p_cero_v = matriz[:, 0].sum()
    btts_si = (1 - (p_cero_l + p_cero_v - matriz[0,0])) * 100
    m3.metric("Ambos Anotan (Sí)", f"{round(btts_si, 2)}%")

with tab_heatmap:
    st.header("Probabilidad de Marcadores Exactos")
    fig = px.imshow(matriz * 100,
                    labels=dict(x="Goles Visitante", y="Goles Local", color="Prob %"),
                    x=[str(i) for i in range(7)],
                    y=[str(i) for i in range(7)],
                    text_auto=".1f",
                    color_continuous_scale="Viridis")
    fig.update_layout(title_text="Mapa de Calor: Resultados Probables")
    st.plotly_chart(fig, use_container_width=True)

with tab_corners:
    st.header("Análisis de Tiros de Esquina")
    linea_c = st.select_slider("Línea Córners", options=[i/2 for i in range(10, 31)], value=9.5)
    u_c, o_c = calcular_poisson_ou(cl + cv, linea_c)
    c1, c2 = st.columns(2)
    c1.metric(f"Over {linea_c}", f"{o_c}%")
    c2.metric(f"Under {linea_c}", f"{u_c}%")

with tab_disparos:
    st.header("Análisis de Disparos Totales y a Puerta")
    
    # Disparos Totales
    st.subheader("Disparos en el Partido")
    linea_d = st.select_slider("Línea Disparos Totales", options=[i/2 for i in range(30, 71)], value=24.5) # De 15.0 a 35.0
    u_d, o_d = calcular_poisson_ou(dl + dv, linea_d)
    col_dt1, col_dt2 = st.columns(2)
    col_dt1.metric(f"Over {linea_d} Totales", f"{o_d}%")
    col_dt2.metric(f"Under {linea_d} Totales", f"{u_d}%")
    
    st.divider()
    
    # Disparos a Puerta por Equipo
    st.subheader("Disparos a Puerta por Equipo")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        l_dpl = st.select_slider("Línea Puerta Local", options=[i/2 for i in range(4, 17)], value=4.5)
        u_dpl, o_dpl = calcular_poisson_ou(dpl, l_dpl)
        st.metric(f"Local Over {l_dpl}", f"{o_dpl}%")
        st.metric(f"Local Under {l_dpl}", f"{u_dpl}%")
    with col_d2:
        l_dpv = st.select_slider("Línea Puerta Visita", options=[i/2 for i in range(4, 17)], value=3.5)
        u_dpv, o_dpv = calcular_poisson_ou(dpv, l_dpv)
        st.metric(f"Visita Over {l_dpv}", f"{o_dpv}%")
        st.metric(f"Visita Under {l_dpv}", f"{u_dpv}%")

# --- FOOTER ---
st.markdown("---")
st.markdown(f"""
    <div style='text-align: center; color: #888; padding: 20px;'>
        <p style='font-size: 16px;'>Creado por <strong>Andres Araya</strong> | ⚽ Predictor Elite v3.0</p>
        <p style='font-size: 12px;'>Gestión de Banca actual: ${bankroll} ({riesgo})</p>
    </div>
""", unsafe_allow_html=True)
