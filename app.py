import streamlit as st
import numpy as np
import requests
import pandas as pd
from scipy.stats import poisson

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Predictor Automático PRO", layout="wide")

# --- FUNCIONES DE API (FOOTBALL-API) ---
def call_api(endpoint, api_key, params=None):
    url = f"https://v3.football.api-sports.io/{endpoint}"
    headers = {'x-rapidapi-host': "v3.football.api-sports.io", 'x-rapidapi-key': api_key}
    try:
        response = requests.get(url, headers=headers, params=params)
        return response.json()
    except:
        return None

def get_leagues(api_key):
    data = call_api("leagues", api_key, {"current": "true"})
    if data and 'response' in data:
        return {item['league']['name']: item['league']['id'] for item in data['response']}
    return {}

def get_fixtures(api_key, league_id, season=2025):
    # Trae partidos próximos (próximos 10)
    data = call_api("fixtures", api_key, {"league": league_id, "season": season, "next": 10})
    if data and 'response' in data:
        return {f"{item['teams']['home']['name']} vs {item['teams']['away']['name']}": item for item in data['response']}
    return {}

def get_team_stats(api_key, league_id, season, team_id):
    data = call_api("teams/statistics", api_key, {"league": league_id, "season": season, "team": team_id})
    if data and 'response' in data:
        s = data['response']
        pj = s['fixtures']['played']['total']
        if pj == 0: return None
        return {
            "goles": s['goals']['for']['average']['total'],
            "corners": 5.0, # Valor por defecto si la API free no lo detalla en este endpoint
            "remates": 12.0
        }
    return None

# --- LÓGICA DE CÁLCULO ---
def matriz_dixon_coles(l_l, l_v, rho=-0.15):
    matriz = np.zeros((7, 7))
    for i in range(7):
        for j in range(7):
            prob = poisson.pmf(i, float(l_l)) * poisson.pmf(j, float(l_v))
            # Ajuste simplificado de Dixon-Coles
            if i == 0 and j == 0: prob *= (1 - (l_l * l_v * rho))
            elif i == 1 and j == 1: prob *= (1 - rho)
            matriz[i][j] = max(0, prob)
    return matriz / matriz.sum()

# --- INTERFAZ ---
st.title("🚀 Predictor Automático SaaS v5.0")
st.sidebar.header("🔑 Configuración de Datos")
api_key = st.sidebar.text_input("Ingresa tu API Key de API-Football", type="password")

if api_key:
    # 1. Seleccionar Liga
    leagues_dict = get_leagues(api_key)
    if leagues_dict:
        sel_league_name = st.sidebar.selectbox("1. Elige una Liga", list(leagues_dict.keys()))
        league_id = leagues_dict[sel_league_name]
        
        # 2. Seleccionar Partido
        fixtures_dict = get_fixtures(api_key, league_id)
        if fixtures_dict:
            sel_match = st.sidebar.selectbox("2. Selecciona un Partido Próximo", list(fixtures_dict.keys()))
            match_data = fixtures_dict[sel_match]
            
            if st.sidebar.button("⚡ Analizar Partido"):
                with st.spinner("Extrayendo estadísticas y calculando valor..."):
                    id_home = match_data['teams']['home']['id']
                    id_away = match_data['teams']['away']['id']
                    season = match_data['league']['season']
                    
                    stats_h = get_team_stats(api_key, league_id, season, id_home)
                    stats_v = get_team_stats(api_key, league_id, season, id_away)
                    
                    if stats_h and stats_v:
                        # --- CÁLCULOS ---
                        matriz = matriz_dixon_coles(stats_h['goles'], stats_v['goles'])
                        
                        # Resultados
                        st.header(f"Análisis: {sel_match}")
                        col1, col2, col3 = st.columns(3)
                        
                        # Probabilidades
                        p_over = (1 - sum(matriz[i][j] for i in range(7) for j in range(7) if i+j < 2.5)) * 100
                        p_btts = (1 - (matriz[0,:].sum() + matriz[:,0].sum() - matriz[0,0])) * 100
                        p_home = np.tril(matriz, -1).sum() * 100
                        
                        col1.metric("Prob. Over 2.5", f"{round(p_over, 1)}%")
                        col2.metric("Ambos Anotan", f"{round(p_btts, 1)}%")
                        col3.metric(f"Victoria {match_data['teams']['home']['name']}", f"{round(p_home, 1)}%")
                        
                        # Datos extraídos automáticamente
                        st.subheader("📊 Datos Extraídos Automáticamente")
                        st.write(f"Promedio Goles {match_data['teams']['home']['name']}: **{stats_h['goles']}**")
                        st.write(f"Promedio Goles {match_data['teams']['away']['name']}: **{stats_v['goles']}**")
                    else:
                        st.error("No hay suficientes estadísticas para este partido en la API.")
        else:
            st.sidebar.warning("No hay partidos próximos para esta liga.")
    else:
        st.sidebar.error("No se pudieron cargar las ligas. Revisa tu API Key.")
else:
    st.info("Por favor, ingresa tu API Key en la barra lateral para comenzar.")

st.markdown("---")
st.markdown("<p style='text-align: center;'>Creado por <strong>Andres Araya</strong> | Edición Comercial Automatizada</p>", unsafe_allow_html=True)
