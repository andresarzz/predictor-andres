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

# --- FUNCIONES DE API (BLINDADAS) ---
def call_api(endpoint, api_key, params=None):
    url = f"https://v3.football.api-sports.io/{endpoint}"
    headers = {'x-rapidapi-host': "v3.football.api-sports.io", 'x-rapidapi-key': api_key}
    try:
        response = requests.get(url, headers=headers, params=params)
        return response.json()
    except Exception:
        return None

def get_fixtures_by_date(api_key, date_str):
    data = call_api("fixtures", api_key, {"date": date_str})
    if data and 'response' in data:
        if len(data['response']) == 0:
            return {}
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
    """Extrae métricas con escudo anti-errores (TypeError handling)"""
    data = call_api("teams/statistics", api_key, {"league": league_id, "season": season, "team": team_id})
    
    if not data or 'response' not in data:
        return None
        
    s = data['response']
    
    # SOLUCIÓN AL ERROR: Validar si la API devolvió una lista vacía [] o datos corruptos
    if not s or isinstance(s, list) or 'fixtures' not in s:
        return None
        
    try:
        pj = s['fixtures']['played']['total']
        if not pj or pj == 0: 
            return None
            
        # Extracción segura del promedio de goles
        avg_goles = s['goals']['for']['average']['total']
        goles_float = float(avg_goles) if avg_goles is not None else 1.0
        
        return {
            "goles": goles_float,
            "corners": 5.5, 
            "remates_totales": 12.0,
            "remates_puerta": 4.5
        }
    except (TypeError, ValueError, KeyError):
        # Si cualquier dato interno falta, bloquea la caída y retorna None
        return None

# --- INTERFAZ PRINCIPAL ---
st.title("🚀 Predictor Automático SaaS v5.2.1")
st.markdown("Buscador global de partidos por fecha en tiempo real.")

# --- BARRA LATERAL: FLUJO AUTOMATIZADO ---
st.sidebar.header("🔑 Conexión al Servidor")
api_key = st.sidebar.text_input("Ingresa tu API Key (API-Football)", type="password")

if api_key:
    st.sidebar.divider()
    st.sidebar.header("📅 1. Selecciona la Fecha")
    fecha_seleccionada = st.sidebar.date_input("Fecha de los partidos", datetime.today())
    fecha_str = fecha_seleccionada.strftime("%Y-%m-%d")
    
    with st.spinner(f"Buscando partidos para el {fecha_str}..."):
        fixtures_dict = get_fixtures_by_date(api_key, fecha_str)
        
    if fixtures_dict:
        st.sidebar.success(f"Se encontraron {len(fixtures_dict)} partidos.")
        st.sidebar.header("⚽ 2. Selecciona el Partido")
        
        sel_match = st.sidebar.selectbox("Escribe el equipo para buscar...", list(fixtures_dict.keys()))
        match_data = fixtures_dict[sel_match]
        
        if st.sidebar.button("⚡ Analizar Partido Seleccionado", use_container_width=True):
            with st.spinner("Descargando métricas y calculando Poisson..."):
                id_home = match_data['teams']['home']['id']
                id_away = match_data['teams']['away']['id']
                league_id = match_data['league']['id']
                season = match_data['league']['season'] 
                
                stats_h = get_team_stats(api_key, league_id, season, id_home)
                stats_v = get_team_stats(api_key, league_id, season, id_away)
                
                if stats_h and stats_v:
                    st.session_state['datos_partido'] = {
                        'match_name': sel_match,
                        'stats_h': stats_h,
                        'stats_v': stats_v
                    }
                else:
                    st.sidebar.error("⚠️ La API no tiene estadísticas suficientes para esta temporada o copa específica. Intenta con otro partido.")
    else:
        st.sidebar.warning(f"No hay partidos programados para el {fecha_str}.")
else:
    st.sidebar.info("Ingresa tu API Key para cargar el calendario de partidos.")

# --- MOSTRAR RESULTADOS SI HAY DATOS EN SESIÓN ---
if 'datos_partido' in st.session_state:
    datos = st.session_state['datos_partido']
    st.header(f"📊 {datos['match_name']}")
    
    xg_l = datos['stats_h']['goles']
    xg_v = datos['stats_v']['goles']
    
    st.markdown(f"**xG Promedio Extraído:** Local ({xg_l}) | Visita ({xg_v})")
    st.divider()

    sub_goles, sub_corners, sub_remates = st.tabs(["🥅 Goles", "🚩 Córners", "👟 Remates y Puerta"])
    
    with sub_goles:
        st.subheader("Mercado de Goles (Secuencia 0.5)")
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
        cl = datos['stats_h']['corners']
        cv = datos['stats_v']['corners']
        u_c, o_c = calcular_poisson_ou(cl + cv, linea_c)
        cc1, cc2 = st.columns(2)
        cc1.metric(f"Over {linea_c}", f"{o_c}%")
        cc2.metric(f"Under {linea_c}", f"{u_c}%")

    with sub_remates:
        st.subheader("Remates Totales en el Partido")
        linea_d = st.select_slider("Línea Remates Totales", options=[i/2 for i in range(30, 71)], value=24.5)
        dl = datos['stats_h']['remates_totales']
        dv = datos['stats_v']['remates_totales']
        u_d, o_d = calcular_poisson_ou(dl + dv, linea_d)
        cd1, cd2 = st.columns(2)
        cd1.metric(f"Over {linea_d}", f"{o_d}%")
        cd2.metric(f"Under {linea_d}", f"{u_d}%")
        
        st.divider()
        st.subheader("Remates a Puerta (Por Equipo)")
        dpl = datos['stats_h']['remates_puerta']
        dpv = datos['stats_v']['remates_puerta']
        
        c_puerta1, c_puerta2 = st.columns(2)
        with c_puerta1:
            l_dpl = st.select_slider("Línea Puerta Local", options=[i/2 for i in range(2, 17)], value=4.5)
            u_dpl, o_dpl = calcular_poisson_ou(dpl, l_dpl)
            st.metric(f"Local Over {l_dpl}", f"{o_dpl}%")
        with c_puerta2:
            l_dpv = st.select_slider("Línea Puerta Visita", options=[i/2 for i in range(2, 17)], value=3.5)
            u_dpv, o_dpv = calcular_poisson_ou(dpv, l_dpv)
            st.metric(f"Visita Over {l_dpv}", f"{o_dpv}%")

# --- FOOTER ---
st.markdown("---")
st.markdown("""
    <div style='text-align: center; color: #888; padding: 20px;'>
        <p style='font-size: 16px;'>Creado por <strong>Andres Araya</strong> | ⚡ Predictor Estadístico PRO</p>
    </div>
""", unsafe_allow_html=True)
