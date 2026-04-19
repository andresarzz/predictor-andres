import streamlit as st
import numpy as np
import requests
from scipy.stats import poisson
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Predictor Automático PRO", layout="wide")

# --- FUNCIONES MATEMÁTICAS ---
def calcular_poisson_ou(esperado, linea):
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
            if i == 0 and j == 0: ajuste = 1 - (lambda_l * lambda_v * rho)
            elif i == 1 and j == 0: ajuste = 1 + (lambda_v * rho)
            elif i == 0 and j == 1: ajuste = 1 + (lambda_l * rho)
            elif i == 1 and j == 1: ajuste = 1 - rho
            else: ajuste = 1.0
            matriz[i][j] = max(0, prob_base * ajuste)
    return matriz / matriz.sum()

def calcular_kelly(prob_real, cuota_bookie):
    """Calcula el % de stake óptimo. Usa Kelly Fraccionado (1/4) para proteger la banca."""
    if cuota_bookie <= 1.0: return 0.0
    p = prob_real / 100
    q = 1 - p
    b = cuota_bookie - 1
    kelly_pct = ((p * b) - q) / b
    return max(0, round((kelly_pct * 100) / 4, 2))

# --- FUNCIONES DE API ---
def call_api(endpoint, api_key, params=None):
    url = f"https://v3.football.api-sports.io/{endpoint}"
    headers = {
        'x-apisports-key': api_key, 
        'x-rapidapi-key': api_key,
        'x-rapidapi-host': "v3.football.api-sports.io"
    }
    try:
        response = requests.get(url, headers=headers, params=params)
        return response.json()
    except Exception as e:
        return {"errors": f"Error de red: {e}"}

def get_fixtures_by_date(api_key, date_str):
    data = call_api("fixtures", api_key, {"date": date_str})
    if data and 'response' in data:
        if len(data['response']) == 0: return {}
        matches = {}
        for item in data['response']:
            league = item['league']['name']
            home = item['teams']['home']['name']
            away = item['teams']['away']['name']
            match_name = f"[{league}] {home} vs {away}"
            matches[match_name] = item
        return matches
    return {}

def get_team_stats(api_key, league_id, season, team_id):
    params = {"league": league_id, "season": season, "team": team_id}
    data = call_api("teams/statistics", api_key, params)
    
    if 'errors' in data and data['errors']: return None, f"{data['errors']}"
    s = data.get('response')
    if not s or (isinstance(s, list) and len(s) == 0): return None, "Sin datos en la API."
        
    try:
        avg_tot = s.get('goals', {}).get('for', {}).get('average', {}).get('total', 1.0)
        if avg_tot is None: avg_tot = 1.0 
        
        return {
            "goles": float(avg_tot),
            "corners": 5.5, 
            "remates_totales": 12.0,
            "remates_puerta": 4.5
        }, "OK"
    except Exception as e:
        return None, f"Error: {e}"

# --- BARRA LATERAL ---
st.sidebar.header("🔑 Conexión al Servidor")
api_key = st.sidebar.text_input("Ingresa tu API Key", type="password")

if api_key:
    st.sidebar.divider()
    st.sidebar.header("📅 1. Selecciona la Fecha")
    fecha_seleccionada = st.sidebar.date_input("Fecha", datetime.today())
    fecha_str = fecha_seleccionada.strftime("%Y-%m-%d")
    
    with st.spinner(f"Buscando partidos..."):
        fixtures_dict = get_fixtures_by_date(api_key, fecha_str)
        
    if fixtures_dict:
        st.sidebar.success(f"Se encontraron {len(fixtures_dict)} partidos.")
        st.sidebar.header("⚽ 2. Selecciona el Partido")
        
        sel_match = st.sidebar.selectbox("Escribe el equipo...", list(fixtures_dict.keys()))
        match_data = fixtures_dict[sel_match]
        
        temporada_override = st.sidebar.number_input("Temporada a Escanear", min_value=2020, max_value=2026, value=2024, step=1, help="Usa 2024 para saltar el bloqueo de la API gratuita.")
        
        if st.sidebar.button("⚡ Analizar Partido", use_container_width=True):
            with st.spinner(f"Extrayendo datos de la temporada {temporada_override}..."):
                id_home = match_data['teams']['home']['id']
                id_away = match_data['teams']['away']['id']
                league_id = match_data['league']['id']
                
                stats_h, msg_h = get_team_stats(api_key, league_id, temporada_override, id_home)
                stats_v, msg_v = get_team_stats(api_key, league_id, temporada_override, id_away)
                
                if stats_h and stats_v:
                    st.session_state['datos_partido'] = {
                        'match_name': f"{sel_match}",
                        'stats_h': stats_h,
                        'stats_v': stats_v,
                        'api_status': 'success'
                    }
                else:
                    st.session_state['datos_partido'] = {
                        'match_name': f"{sel_match} (MODO MANUAL)",
                        'stats_h': {"goles": 1.5, "corners": 5.0, "remates_totales": 10.0, "remates_puerta": 4.0},
                        'stats_v': {"goles": 1.5, "corners": 5.0, "remates_totales": 10.0, "remates_puerta": 4.0},
                        'api_status': 'failed',
                        'debug_msg': f"No se pudo extraer la temporada {temporada_override}."
                    }
    else:
        st.sidebar.warning("No hay partidos programados.")

# --- INTERFAZ PRINCIPAL ---
st.title("🚀 Predictor Automático SaaS")

if 'datos_partido' in st.session_state:
    datos = st.session_state['datos_partido']
    st.header(f"📊 {datos['match_name']}")
    
    if datos['api_status'] == 'failed':
        st.warning(f"⚠️ {datos['debug_msg']} Ingresa los datos manualmente.")
    
    # --- PANEL DE CONTROL DE PROMEDIOS ---
    st.markdown("### ⚙️ Ajuste de Promedios del Partido")
    st.caption("Los goles (xG) se descargaron de la API. Ajusta los córners y remates según tu análisis previo.")
    
    col_l, col_v = st.columns(2)
    with col_l:
        st.subheader("Equipo Local")
        xg_l = st.number_input("xG Local", value=float(datos['stats_h']['goles']), step=0.1)
        cl = st.number_input("Córners Local", value=float(datos['stats_h']['corners']), step=0.5)
        dl = st.number_input("Remates Totales Local", value=float(datos['stats_h']['remates_totales']), step=0.5)
        dpl = st.number_input("A Puerta Local", value=float(datos['stats_h']['remates_puerta']), step=0.5)
    with col_v:
        st.subheader("Equipo Visita")
        xg_v = st.number_input("xG Visita", value=float(datos['stats_v']['goles']), step=0.1)
        cv = st.number_input("Córners Visita", value=float(datos['stats_v']['corners']), step=0.5)
        dv = st.number_input("Remates Totales Visita", value=float(datos['stats_v']['remates_totales']), step=0.5)
        dpv = st.number_input("A Puerta Visita", value=float(datos['stats_v']['remates_puerta']), step=0.5)

    st.divider()

    # --- TABS DE MERCADOS ---
    tab_goles, tab_corners, tab_remates_tot, tab_remates_p, tab_ev = st.tabs([
        "🥅 Goles", "🚩 Córners", "👟 Remates Totales", "🎯 A Puerta", "⚖️ Calculadora +EV"
    ])
    
    # 1. MERCADO DE GOLES
    with tab_goles:
        st.subheader("Goles del Partido (Dixon-Coles)")
        linea_g = st.select_slider("Línea de Goles", options=[i/2 for i in range(1, 15)], value=2.5)
        matriz = matriz_dixon_coles(xg_l, xg_v)
        
        prob_under_g = 0
        for i in range(len(matriz)):
            for j in range(len(matriz)):
                if i + j < linea_g: prob_under_g += matriz[i][j]
                
        cg1, cg2, cg3 = st.columns(3)
        cg1.metric(f"Over {linea_g}", f"{round((1-prob_under_g)*100, 2)}%")
        cg2.metric(f"Under {linea_g}", f"{round(prob_under_g*100, 2)}%")
        btts_si = (1 - (matriz[0, :].sum() + matriz[:, 0].sum() - matriz[0,0])) * 100
        cg3.metric("Ambos Anotan (Sí)", f"{round(btts_si, 2)}%")

    # 2. MERCADO DE CÓRNERS
    with tab_corners:
        st.subheader("Córners Totales del Partido")
        linea_c_tot = st.select_slider("Línea Córners Totales", options=[i/2 for i in range(10, 35)], value=9.5)
        u_c_tot, o_c_tot = calcular_poisson_ou(cl + cv, linea_c_tot)
        cc1, cc2 = st.columns(2)
        cc1.metric(f"Total Over {linea_c_tot}", f"{o_c_tot}%")
        cc2.metric(f"Total Under {linea_c_tot}", f"{u_c_tot}%")

        st.divider()
        st.subheader("Córners por Equipo")
        col_ce1, col_ce2 = st.columns(2)
        with col_ce1:
            linea_cl = st.select_slider("Línea Córners Local", options=[i/2 for i in range(2, 21)], value=4.5)
            u_cl, o_cl = calcular_poisson_ou(cl, linea_cl)
            st.metric(f"Local Over {linea_cl}", f"{o_cl}%")
            st.metric(f"Local Under {linea_cl}", f"{u_cl}%")
        with col_ce2:
            linea_cv = st.select_slider("Línea Córners Visita", options=[i/2 for i in range(2, 21)], value=3.5)
            u_cv, o_cv = calcular_poisson_ou(cv, linea_cv)
            st.metric(f"Visita Over {linea_cv}", f"{o_cv}%")
            st.metric(f"Visita Under {linea_cv}", f"{u_cv}%")

    # 3. MERCADO DE REMATES TOTALES
    with tab_remates_tot:
        st.subheader("Remates Totales del Partido")
        linea_d_tot = st.select_slider("Línea Remates Totales Partido", options=[i/2 for i in range(30, 71)], value=24.5)
        u_d_tot, o_d_tot = calcular_poisson_ou(dl + dv, linea_d_tot)
        cd1, cd2 = st.columns(2)
        cd1.metric(f"Total Over {linea_d_tot}", f"{o_d_tot}%")
        cd2.metric(f"Total Under {linea_d_tot}", f"{u_d_tot}%")

        st.divider()
        st.subheader("Remates Totales por Equipo")
        col_de1, col_de2 = st.columns(2)
        with col_de1:
            linea_dl = st.select_slider("Línea Remates Local", options=[i/2 for i in range(10, 41)], value=12.5)
            u_dl, o_dl = calcular_poisson_ou(dl, linea_dl)
            st.metric(f"Local Over {linea_dl}", f"{o_dl}%")
            st.metric(f"Local Under {linea_dl}", f"{u_dl}%")
        with col_de2:
            linea_dv = st.select_slider("Línea Remates Visita", options=[i/2 for i in range(10, 41)], value=10.5)
            u_dv, o_dv = calcular_poisson_ou(dv, linea_dv)
            st.metric(f"Visita Over {linea_dv}", f"{o_dv}%")
            st.metric(f"Visita Under {linea_dv}", f"{u_dv}%")

    # 4. MERCADO DE REMATES A PUERTA
    with tab_remates_p:
        st.subheader("Remates a Puerta Totales del Partido")
        linea_dp_tot = st.select_slider("Línea A Puerta Totales Partido", options=[i/2 for i in range(10, 31)], value=8.5)
        u_dp_tot, o_dp_tot = calcular_poisson_ou(dpl + dpv, linea_dp_tot)
        cdp1, cdp2 = st.columns(2)
        cdp1.metric(f"Total A Puerta Over {linea_dp_tot}", f"{o_dp_tot}%")
        cdp2.metric(f"Total A Puerta Under {linea_dp_tot}", f"{u_dp_tot}%")

        st.divider()
        st.subheader("Remates a Puerta por Equipo")
        col_dpe1, col_dpe2 = st.columns(2)
        with col_dpe1:
            linea_dpl = st.select_slider("Línea A Puerta Local", options=[i/2 for i in range(2, 21)], value=4.5)
            u_dpl, o_dpl = calcular_poisson_ou(dpl, linea_dpl)
            st.metric(f"Local Over {linea_dpl}", f"{o_dpl}%")
            st.metric(f"Local Under {linea_dpl}", f"{u_dpl}%")
        with col_dpe2:
            linea_dpv = st.select_slider("Línea A Puerta Visita", options=[i/2 for i in range(2, 21)], value=3.5)
            u_dpv, o_dpv = calcular_poisson_ou(dpv, linea_dpv)
            st.metric(f"Visita Over {linea_dpv}", f"{o_dpv}%")
            st.metric(f"Visita Under {linea_dpv}", f"{u_dpv}%")

    # 5. CALCULADORA DE VALOR ESPERADO (+EV)
    with tab_ev:
        st.subheader("Buscador de Rentabilidad (+EV)")
        st.markdown("Verifica si la cuota que te ofrece la casa de apuestas tiene ventaja matemática basándote en los porcentajes calculados por el modelo.")
        
        col_ev1, col_ev2 = st.columns(2)
        with col_ev1:
            prob_modelo = st.number_input("Probabilidad del Modelo (%)", min_value=1.0, max_value=99.9, value=65.0, step=0.5, help="Copia aquí el % que te dio la herramienta en las pestañas anteriores.")
        with col_ev2:
            cuota_bookie = st.number_input("Cuota de la Casa de Apuestas", min_value=1.01, value=1.85, step=0.01)

        # Cálculos de EV
        prob_impl = (1 / cuota_bookie) * 100
        ev = ((prob_modelo / 100) * cuota_bookie) - 1
        kelly = calcular_kelly(prob_modelo, cuota_bookie)

        st.divider()
        if ev > 0:
            st.success(f"✅ **¡VALOR DETECTADO! (EV: +{round(ev*100, 2)}%)**")
            st.markdown("La probabilidad real es mayor a lo que asume la casa. Apostar aquí es rentable a largo plazo.")
            
            c_res1, c_res2, c_res3 = st.columns(3)
            c_res1.metric("Tu Probabilidad Real", f"{prob_modelo}%")
            c_res2.metric("Prob. de la Casa", f"{round(prob_impl, 2)}%")
            c_res3.metric("Stake (Kelly Seguro)", f"{kelly}%", "Del bankroll")
        else:
            st.error(f"❌ **SIN VALOR (EV: {round(ev*100, 2)}%)**")
            st.markdown("La casa te está pagando menos de lo que deberías ganar por este riesgo. Evita esta apuesta.")
            
            c_res1, c_res2 = st.columns(2)
            c_res1.metric("Tu Probabilidad Real", f"{prob_modelo}%")
            c_res2.metric("Prob. de la Casa", f"{round(prob_impl, 2)}%")

# --- FOOTER ---
st.markdown("---")
st.markdown("""
    <div style='text-align: center; color: #888; padding: 20px;'>
        <p style='font-size: 16px;'>Creado por <strong>Andres Araya</strong> | ⚡ Predictor Estadístico PRO</p>
    </div>
""", unsafe_allow_html=True)
