import streamlit as st
import numpy as np
from scipy.stats import poisson, norm
import plotly.graph_objects as go

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Predictor Elite PRO", page_icon="🔒", layout="wide")

# --- SISTEMA DE SESIÓN (LOGIN FALSO PARA DEMO) ---
if 'logueado' not in st.session_state:
    st.session_state.logueado = False

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

def prop_baloncesto_norm(promedio, desviacion, linea):
    prob_under = norm.cdf(linea, loc=promedio, scale=desviacion)
    return round(prob_under * 100, 2), round((1 - prob_under) * 100, 2)

# ==========================================
# PANTALLA DE LOGIN (PAYWALL)
# ==========================================
if not st.session_state.logueado:
    st.markdown("<h1 style='text-align: center;'>⚡ Predictor Elite Analytics</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Plataforma institucional de apuestas cuantitativas.</p>", unsafe_allow_html=True)
    
    col_login1, col_login2, col_login3 = st.columns([1, 1, 1])
    with col_login2:
        st.info("🔐 Acceso exclusivo para suscriptores VIP")
        usuario = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        
        # Para tu demo, cualquier contraseña entrará. En el futuro aquí va Stripe/Firebase.
        if st.button("Iniciar Sesión", use_container_width=True):
            st.session_state.logueado = True
            st.rerun()
            
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #888;'>
        <p style='font-size: 14px;'>Desarrollado con motor Dixon-Coles y Monte Carlo</p>
        <p style='font-size: 14px;'>Creado por <strong>Andres Araya</strong> | © 2026</p>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# INTERFAZ PRINCIPAL (SOLO PARA USUARIOS VIP)
# ==========================================
else:
    st.sidebar.success("✅ Sesión Iniciada (Suscripción Activa)")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.logueado = False
        st.rerun()

    st.sidebar.header("⚙️ Automatización (Próximamente)")
    st.sidebar.selectbox("Seleccionar Partido en Vivo", ["Ingresar datos manualmente...", "Real Madrid vs Barcelona (API Lock)", "Arsenal vs Chelsea (API Lock)"], disabled=True, help="Esta función requiere integración de API.")
    
    st.sidebar.divider()
    st.sidebar.header("📊 Ingreso Manual de xG")
    col_sf1, col_sf2 = st.sidebar.columns(2)
    with col_sf1:
        st.subheader("Local")
        xg_l = st.number_input("xG L", value=1.6, step=0.1)
        cl = st.number_input("Córners L", value=5.5, step=0.1)
        dl = st.number_input("Remates L", value=12.0, step=0.5)
        dpl = st.number_input("A Puerta L", value=4.5, step=0.1)
    with col_sf2:
        st.subheader("Visita")
        xg_v = st.number_input("xG V", value=1.2, step=0.1)
        cv = st.number_input("Córners V", value=4.2, step=0.1)
        dv = st.number_input("Remates V", value=10.0, step=0.5)
        dpv = st.number_input("A Puerta V", value=3.2, step=0.1)

    st.title("⚡ Dashboard de Análisis Cuantitativo")
    
    tab_futbol, tab_baloncesto, tab_backtest = st.tabs(["⚽ Fútbol", "🏀 Baloncesto", "📈 Backtesting (Próximamente)"])
    
    with tab_futbol:
        sub_goles, sub_corners, sub_remates = st.tabs(["🥅 Goles", "🚩 Córners", "👟 Remates y Puerta"])
        
        with sub_goles:
            linea_g = st.select_slider("Línea de Goles", options=[i/2 for i in range(1, 13)], value=2.5)
            matriz = matriz_dixon_coles(xg_l, xg_v)
            prob_under_g = sum(matriz[i][j] for i in range(len(matriz)) for j in range(len(matriz)) if i + j < linea_g)
            
            cg1, cg2, cg3 = st.columns(3)
            cg1.metric(f"Over {linea_g}", f"{round((1-prob_under_g)*100, 2)}%")
            cg2.metric(f"Under {linea_g}", f"{round(prob_under_g*100, 2)}%")
            btts_si = (1 - (matriz[0, :].sum() + matriz[:, 0].sum() - matriz[0,0])) * 100
            cg3.metric("Ambos Anotan (Sí)", f"{round(btts_si, 2)}%")

        with sub_corners:
            linea_c = st.select_slider("Línea Córners Totales", options=[i/2 for i in range(10, 31)], value=9.5)
            u_c, o_c = calcular_poisson_ou(cl + cv, linea_c)
            cc1, cc2 = st.columns(2)
            cc1.metric(f"Over {linea_c}", f"{o_c}%")
            cc2.metric(f"Under {linea_c}", f"{u_c}%")

        with sub_remates:
            linea_d = st.select_slider("Línea Remates Totales", options=[i/2 for i in range(30, 71)], value=24.5)
            u_d, o_d = calcular_poisson_ou(dl + dv, linea_d)
            st.metric(f"Total Over {linea_d}", f"{o_d}%")
            
            st.divider()
            c_puerta1, c_puerta2 = st.columns(2)
            with c_puerta1:
                l_dpl = st.select_slider("Línea Puerta Local", options=[i/2 for i in range(2, 17)], value=4.5)
                u_dpl, o_dpl = calcular_poisson_ou(dpl, l_dpl)
                st.metric(f"Local Over {l_dpl}", f"{o_dpl}%")
            with c_puerta2:
                l_dpv = st.select_slider("Línea Puerta Visita", options=[i/2 for i in range(2, 17)], value=3.5)
                u_dpv, o_dpv = calcular_poisson_ou(dpv, l_dpv)
                st.metric(f"Visita Over {l_dpv}", f"{o_dpv}%")

    with tab_baloncesto:
        st.header("Player Props")
        col_b1, col_b2, col_b3 = st.columns(3)
        promedio_jugador = col_b1.number_input("Promedio Pts", value=22.5)
        desviacion_std = col_b2.number_input("Desv. Estándar", value=4.5)
        linea_prop = col_b3.select_slider("Línea Casa", options=[i/2 for i in range(10, 81)], value=23.5)
            
        u_prop, o_prop = prop_baloncesto_norm(promedio_jugador, desviacion_std, linea_prop)
        cb1, cb2 = st.columns(2)
        cb1.metric(f"Over {linea_prop}", f"{o_prop}%")
        cb2.metric(f"Under {linea_prop}", f"{u_prop}%")
        
    with tab_backtest:
        st.info("📊 Módulo de Backtesting Histórico en desarrollo. Próximamente los usuarios podrán evaluar la rentabilidad del sistema contra 50,000 partidos históricos.")

    # --- FOOTER ---
    st.markdown("---")
    st.markdown("""
        <div style='text-align: center; color: #888; padding: 20px;'>
            <p style='font-size: 16px;'>Creado por <strong>Andres Araya</strong> | ⚡ Predictor Estadístico PRO</p>
        </div>
    """, unsafe_allow_html=True)
