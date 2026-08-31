import sys
import requests
import pandas as pd
import numpy as np
from datetime import datetime
from jinja2 import Template

# Habilitar caché local para consultas de béisbol
import pybaseball
from pybaseball import cache, pitching_stats_bref
cache.enable()

# ==========================================
# 1. EXTRACCIÓN ROBUSTA DE BIG DATA
# ==========================================
print("Descargando Big Data Sabermétrica desde Statcast / Baseball Reference...")
año_actual = datetime.now().year

def cargar_metricas_globales():
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Referer': 'https://www.fangraphs.com/leaders/major-league',
            'Origin': 'https://www.fangraphs.com'
        }
        url_fg = f"https://www.fangraphs.com/api/leaders/major-league/data?age=&pos=all&stats=pit&lg=all&qual=0&type=8&season={año_actual}&month=0&season1={año_actual}&ind=0&team=0&rost=0&age=0&filter=&players=0&startdate=&enddate=&pageitems=5000"
        
        res = requests.get(url_fg, headers=headers, timeout=10)
        if res.status_code == 200:
            json_data = res.json()
            data_list = json_data.get('data', json_data) if isinstance(json_data, dict) else json_data
            
            if isinstance(data_list, list) and len(data_list) > 0:
                df = pd.DataFrame(data_list)
                df['Name_Clean'] = df['PlayerName'].str.lower().str.strip()
                df['xFIP'] = pd.to_numeric(df.get('xFIP', df.get('ERA', 4.10)), errors='coerce').fillna(4.10)
                df['K%'] = pd.to_numeric(df.get('K%', 0.22), errors='coerce').fillna(0.22) * 100
                df['BB%'] = pd.to_numeric(df.get('BB%', 0.08), errors='coerce').fillna(0.08) * 100
                df['IP'] = pd.to_numeric(df.get('IP', 5.1), errors='coerce').fillna(5.1)
                print("✓ Conexión exitosa a FanGraphs API (xFIP, K%, BB%, IP cargados).")
                return df
    except Exception as e:
        pass

    print("⚠️ Conectando a Baseball Reference / Statcast Engine...")
    try:
        df = pitching_stats_bref(año_actual)
        if not df.empty:
            df['Name_Clean'] = df['Name'].str.lower().str.strip()
            bf = df['BF'] if 'BF' in df else (df['IP'] * 4.2)
            df['K%'] = np.where(bf > 0, (df['SO'] / bf) * 100, 22.0)
            df['BB%'] = np.where(bf > 0, (df['BB'] / bf) * 100, 8.0)
            df['xFIP'] = pd.to_numeric(df.get('ERA', 4.10), errors='coerce').fillna(4.10)
            df['IP'] = pd.to_numeric(df.get('IP', 5.1), errors='coerce').fillna(5.1)
            print("✓ Conexión exitosa a Baseball Reference.")
            return df
    except Exception as e:
        print(f"Aviso BRef Engine: {e}")

    return pd.DataFrame()

df_pitchers = cargar_metricas_globales()

MLB_TEAM_K_FACTORS = {
    "Colorado Rockies": 1.12, "Oakland Athletics": 1.10, "Seattle Mariners": 1.09,
    "Detroit Tigers": 1.06, "Pittsburgh Pirates": 1.05, "Chicago White Sox": 1.04,
    "Minnesota Twins": 1.02, "Tampa Bay Rays": 1.01, "Los Angeles Angels": 1.00,
    "San Francisco Giants": 0.99, "Milwaukee Brewers": 0.98, "Chicago Cubs": 0.97,
    "New York Yankees": 0.96, "Boston Red Sox": 0.96, "Toronto Blue Jays": 0.95,
    "Philadelphia Phillies": 0.95, "Baltimore Orioles": 0.94, "Texas Rangers": 0.94,
    "Atlanta Braves": 0.93, "Los Angeles Dodgers": 0.92, "Houston Astros": 0.90,
    "San Diego Padres": 0.89, "Arizona Diamondbacks": 0.88, "Cleveland Guardians": 0.87
}

def obtener_metricas_profundas_pitcher(nombre):
    if df_pitchers.empty or not nombre or nombre in ["Desconocido", "Por Anunciar"]:
        return {"xFIP": 4.10, "K_pct": 22.0, "BB_pct": 8.0, "ERA": 4.20, "IP_per_game": 5.1}
    
    nombre_clean = nombre.lower().strip()
    match = df_pitchers[df_pitchers['Name_Clean'].str.contains(nombre_clean, regex=False)]
    
    if not match.empty:
        row = match.iloc[0]
        xfip_val = row.get('xFIP', row.get('ERA', 4.10))
        k_val = row.get('K%', 22.0)
        bb_val = row.get('BB%', 8.0)
        ip_val = row.get('IP', 5.1)
        
        if isinstance(k_val, (int, float)) and k_val < 1: k_val *= 100
        if isinstance(bb_val, (int, float)) and bb_val < 1: bb_val *= 100

        return {
            "xFIP": float(xfip_val) if pd.notnull(xfip_val) else 4.10,
            "K_pct": float(k_val) if pd.notnull(k_val) else 22.0,
            "BB_pct": float(bb_val) if pd.notnull(bb_val) else 8.0,
            "ERA": float(row.get('ERA', 4.20)),
            "IP_per_game": min(6.2, max(4.0, float(ip_val) / 25.0)) if float(ip_val) > 20 else 5.1
        }
    return {"xFIP": 4.10, "K_pct": 22.0, "BB_pct": 8.0, "ERA": 4.20, "IP_per_game": 5.1}

# ==========================================
# 2. PROYECTOR DE PONCHES (K-PROPS)
# ==========================================
def proyectar_ponches_abridor(pitcher_name, opponent_team):
    m = obtener_metricas_profundas_pitcher(pitcher_name)
    opp_factor = MLB_TEAM_K_FACTORS.get(opponent_team, 1.00)
    
    bf_estimados = m["IP_per_game"] * 4.1
    k_proyectados = round((bf_estimados * (m["K_pct"] / 100.0)) * opp_factor, 1)
    
    linea = np.floor(k_proyectados) + 0.5 if k_proyectados >= np.floor(k_proyectados) + 0.3 else np.floor(k_proyectados) - 0.5
    if linea < 3.5: linea = 3.5

    tipo_pick = "OVER" if k_proyectados > linea else "UNDER"
    probabilidad = min(78, max(52, int(50 + abs(k_proyectados - linea) * 15)))

    return {
        "pitcher": pitcher_name,
        "rival": opponent_team,
        "k_proj": k_proyectados,
        "linea": linea,
        "pick_str": f"{pitcher_name}: {tipo_pick} {linea} Ks (Proj: {k_proyectados})",
        "probabilidad": probabilidad,
        "tipo": tipo_pick
    }

# ==========================================
# 3. CONSULTAR CARTELERA Y MARCADORES MLB API
# ==========================================
def obtener_partidos_mlb(fecha_str):
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={fecha_str}&hydrate=team,probablePitcher"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
    except Exception as e:
        print(f"Error al conectar con la API de MLB: {e}")
        return []
    
    partidos = []
    if "dates" in data and len(data["dates"]) > 0:
        for g in data["dates"][0]["games"]:
            partidos.append({
                "game_id": g["gamePk"],
                "home_team": g["teams"]["home"]["team"]["name"],
                "away_team": g["teams"]["away"]["team"]["name"],
                "venue": g.get("venue", {}).get("name", "Sede Desconocida"),
                "status": g["status"]["detailedState"],
                "home_score": g["teams"]["home"].get("score", 0),
                "away_score": g["teams"]["away"].get("score", 0),
                "away_pitcher": g["teams"]["away"].get("probablePitcher", {}).get("fullName", "Por Anunciar"),
                "home_pitcher": g["teams"]["home"].get("probablePitcher", {}).get("fullName", "Por Anunciar")
            })
    return partidos

# ==========================================
# 4. MOTOR MONTE CARLO Y EVALUADOR MULTI-MERCADO
# ==========================================
def analizar_partido_deep(partido):
    m_away = obtener_metricas_profundas_pitcher(partido["away_pitcher"])
    m_home = obtener_metricas_profundas_pitcher(partido["home_pitcher"])
    
    k_prop_away = proyectar_ponches_abridor(partido["away_pitcher"], partido["home_team"])
    k_prop_home = proyectar_ponches_abridor(partido["home_pitcher"], partido["away_team"])
    best_k_prop = k_prop_away if k_prop_away["probabilidad"] >= k_prop_home["probabilidad"] else k_prop_home

    adj_away_p = m_away["xFIP"] - (m_away["K_pct"] - m_away["BB_pct"]) * 0.03
    adj_home_p = m_home["xFIP"] - (m_home["K_pct"] - m_home["BB_pct"]) * 0.03
    
    away_xg = round(max(2.1, adj_home_p * 0.92), 2)
    home_xg = round(max(2.1, (adj_away_p * 0.92) + 0.28), 2)
    
    np.random.seed(partido["game_id"] % 100000)
    n_sims = 10000
    away_runs = np.random.poisson(away_xg, n_sims)
    home_runs = np.random.poisson(home_xg, n_sims)
    
    home_wins = np.sum(home_runs > away_runs)
    away_wins = np.sum(away_runs > home_runs)
    
    home_win_pct = int(np.clip(round((home_wins / n_sims) * 100), 22, 78))
    away_win_pct = int(np.clip(round((away_wins / n_sims) * 100), 22, 78))
    
    if home_win_pct >= away_win_pct:
        equipo_fav, equipo_und = partido["home_team"], partido["away_team"]
        prob_ml = home_win_pct
        diff_runs = home_runs - away_runs
    else:
        equipo_fav, equipo_und = partido["away_team"], partido["home_team"]
        prob_ml = away_win_pct
        diff_runs = away_runs - home_runs

    cover_rl_fav = np.sum(diff_runs >= 2)
    prob_rl_fav = int(round((cover_rl_fav / n_sims) * 100))
    prob_rl_und = 100 - prob_rl_fav

    if prob_rl_fav >= 52:
        handicap_str = f"{equipo_fav} -1.5 ({prob_rl_fav}%)"
        handicap_equipo = equipo_fav
        handicap_linea = -1.5
    else:
        handicap_str = f"{equipo_und} +1.5 ({prob_rl_und}%)"
        handicap_equipo = equipo_und
        handicap_linea = 1.5

    total_esperado = round(away_xg + home_xg, 1)
    tipo_total = "OVER" if total_esperado >= 8.5 else "UNDER"
    total_str = f"Altas (Over {total_esperado})" if tipo_total == "OVER" else f"Bajas (Under {total_esperado})"

    # ----------------------------------------------------
    # EXPLICACIÓN DETALLADA DE LA CATEGORIZACIÓN
    # ----------------------------------------------------
    if prob_ml >= 67:
        categoria, color_tag = "ALTAMENTE RECOMENDADO", "#28a745"
        razon_cat = f"<b>Ventaja Superior (ML {prob_ml}%):</b> El modelo Monte Carlo proyecta una probabilidad de victoria enorme a favor de {equipo_fav}, impulsada por una clara brecha sabermétrica entre pitchers e indicadores ofensivos."
    elif prob_ml >= 57:
        categoria, color_tag = "RECOMENDACIÓN MODERADA", "#d97706"
        razon_cat = f"<b>Ventaja Moderada (ML {prob_ml}%):</b> {equipo_fav} posee ventaja en las simulaciones, pero con un margen de variabilidad que requiere precaución con la cuota ofertada."
    else:
        categoria, color_tag = "PRECAUCIÓN", "#dc3545"
        razon_cat = f"<b>Encuentro Parejo / Volátil (ML {prob_ml}%):</b> Las probabilidades de ambos equipos están muy niveladas. No hay suficiente ventaja sabermétrica para Moneyline directo."

    pronostico_str = f"ML: {equipo_fav} ({prob_ml}%) | RL: {handicap_str} | Total: {total_str}"

    analisis_txt = (
        f"<b>Abridores:</b> {partido['away_pitcher']} (xFIP: {m_away['xFIP']:.2f} | K%: {m_away['K_pct']:.1f}%) vs "
        f"{partido['home_pitcher']} (xFIP: {m_home['xFIP']:.2f} | K%: {m_home['K_pct']:.1f}%).<br>"
        f"<b>Proyección xG:</b> {partido['away_team']} {away_xg} - {home_xg} {partido['home_team']}.<br>"
        f"<b>K-Props Destacado:</b> {best_k_prop['pick_str']} (Confianza: {best_k_prop['probabilidad']}%).<br>"
        f"<span style='color:{color_tag};'><b>Justificación Criterio:</b> {razon_cat}</span>"
    )

    # ----------------------------------------------------
    # EVALUACIÓN DETALLADA MULTI-MERCADO
    # ----------------------------------------------------
    estatus, estatus_color = "PENDIENTE", "#6c757d"
    detalle_evaluacion = "Esperando inicio del encuentro"
    estado_str = str(partido["status"]).lower()
    marcador_resumen = f"Finalizado ({partido['away_score']} - {partido['home_score']})" if any(k in estado_str for k in ["final", "completed", "game over"]) else "Por Jugar"

    if any(k in estado_str for k in ["final", "completed", "game over"]) or "Finalizado" in marcador_resumen:
        h_score, a_score = partido["home_score"], partido["away_score"]
        total_real = h_score + a_score
        ganador_real = partido["home_team"] if h_score > a_score else partido["away_team"]

        # 1. Evaluar Moneyline
        ml_ok = (equipo_fav == ganador_real)

        # 2. Evaluar Hándicap (Run Line)
        diff_target = (h_score - a_score) if handicap_equipo == partido["home_team"] else (a_score - h_score)
        rl_ok = ((diff_target + handicap_linea) > 0)

        # 3. Evaluar Totales (Carreras Over/Under)
        total_ok = (total_real > total_esperado) if tipo_total == "OVER" else (total_real < total_esperado)

        aciertos_list, fallos_list = [], []

        if ml_ok: aciertos_list.append("ML")
        else: fallos_list.append("ML")

        if rl_ok: aciertos_list.append(f"Handicap ({handicap_equipo})")
        else: fallos_list.append("Handicap")

        if total_ok: aciertos_list.append(f"{tipo_total} {total_esperado}")
        else: fallos_list.append(f"{tipo_total} {total_esperado}")

        num_aciertos = len(aciertos_list)

        if num_aciertos == 3:
            estatus = "✓ ACERTADO COMPLETO"
            estatus_color = "#28a745"
            detalle_evaluacion = "Ganaron los 3 mercados (ML, Hándicap y Totales)."
        elif num_aciertos > 0:
            estatus = f"½ ACIERTO PARCIAL ({num_aciertos}/3)"
            estatus_color = "#d97706"
            detalle_evaluacion = f"Acertó: {', '.join(aciertos_list)} | Falló: {', '.join(fallos_list)}"
        else:
            estatus = "X FALLADO COMPLETO"
            estatus_color = "#dc3545"
            detalle_evaluacion = f"Perdidos todos los mercados (Marcador real: {a_score}-{h_score})."

    marcador_detalle = f"{partido['away_team']} {partido['away_score']} - {partido['home_score']} {partido['home_team']}" if any(k in estado_str for k in ["final", "completed", "game over"]) else "Pendiente de inicio"

    return {
        "partido": f"{partido['away_team']} vs {partido['home_team']}",
        "sede": partido["venue"],
        "marcador_resumen": marcador_resumen,
        "marcador_detalle": marcador_detalle,
        "categoria": categoria,
        "color_tag": color_tag,
        "tipo_apuesta": "[Monte Carlo Multi-Mercado]",
        "pronostico": pronostico_str,
        "handicap": handicap_str,
        "k_prop_away_str": k_prop_away["pick_str"],
        "k_prop_home_str": k_prop_home["pick_str"],
        "analisis": analisis_txt,
        "estatus": estatus,
        "estatus_color": estatus_color,
        "detalle_evaluacion": detalle_evaluacion
    }

# ==========================================
# 5. PLANTILLA HTML DISEÑO PROFESIONAL
# ==========================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Reporte Deep Analytics MLB + K-Props</title>
    <style>
        body { font-family: 'Helvetica', 'Arial', sans-serif; background-color: #f8f9fa; padding: 20px; color: #333; }
        .header { margin-bottom: 15px; border-bottom: 2px solid #002b49; padding-bottom: 10px; }
        .header h1 { margin: 0; color: #002b49; font-size: 22px; text-transform: uppercase; }
        .header .meta { margin-top: 5px; font-size: 13px; color: #666; }
        .legend-box { background: #ffffff; border: 1px solid #d9d9d9; border-left: 4px solid #002b49; padding: 10px; margin-bottom: 20px; font-size: 11px; border-radius: 4px; }
        .legend-box h3 { margin: 0 0 6px 0; font-size: 12px; color: #002b49; text-transform: uppercase; }
        .legend-grid { display: flex; gap: 15px; }
        .legend-item { flex: 1; }
        table { width: 100%; border-collapse: collapse; background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        th { background-color: #0d1b2a; color: white; text-align: left; padding: 10px; font-size: 11px; text-transform: uppercase; }
        td { padding: 10px; border-bottom: 1px solid #e9ecef; font-size: 11px; vertical-align: top; }
        .partido-title { font-weight: bold; color: #111; font-size: 12px; }
        .sede-sub { color: #777; font-size: 10px; margin-top: 2px; }
        .cat-tag { font-weight: bold; font-size: 11px; }
        .pronostico-val { font-weight: bold; color: #222; margin-top: 2px; line-height: 1.3; }
        .k-box { background: #eef6ff; border-left: 3px solid #1890ff; padding: 4px 6px; margin-top: 4px; font-size: 10px; }
        .analisis-box { font-size: 10px; color: #444; line-height: 1.4; background: #fafafa; padding: 6px; border-left: 3px solid #002b49; margin-top: 2px; }
        .estatus-cell { font-weight: bold; font-size: 11px; }
    </style>
</head>
<body>
<div class="header">
    <h1>Reporte Oficial MLB: ML, Run Lines & Props de Ponches (K)</h1>
    <div class="meta">
        <strong>Fecha:</strong> {{ fecha }} | 
        <strong>Partidos Evaluados:</strong> {{ total }} | 
        <span style="color:#28a745;"><strong>Plenos (3/3):</strong> {{ plenos }}</span> | 
        <span style="color:#d97706;"><strong>Parciales:</strong> {{ parciales }}</span> | 
        <span style="color:#dc3545;"><strong>Fallados:</strong> {{ fallados }}</span>
    </div>
</div>

<div class="legend-box">
    <h3>Criterios de Clasificación Sabermétrica (Simulaciones Monte Carlo)</h3>
    <div class="legend-grid">
        <div class="legend-item">
            <span style="color:#28a745; font-weight:bold;">● ALTAMENTE RECOMENDADO (ML ≥ 67%)</span>
            <p style="margin: 3px 0 0 0; color:#555;">Dominio estadístico claro. Brecha significativa en xFIP de abridores, métricas de ponches (K%) y factor de campo favorable.</p>
        </div>
        <div class="legend-item">
            <span style="color:#d97706; font-weight:bold;">● RECOMENDACIÓN MODERADA (57% ≤ ML < 67%)</span>
            <p style="margin: 3px 0 0 0; color:#555;">Ventaja inclinada a favor del equipo con mejor proyección sabermétrica, pero sujeto a volatilidad de bullpens o paridad competitiva.</p>
        </div>
        <div class="legend-item">
            <span style="color:#dc3545; font-weight:bold;">● PRECAUCIÓN (ML < 57%)</span>
            <p style="margin: 3px 0 0 0; color:#555;">Encuentro muy disputado o volátil. No se sugiere apuesta a Moneyline directa; conviene buscar valor en Run Lines (+1.5) o K-Props.</p>
        </div>
    </div>
</div>

<table>
    <thead>
        <tr>
            <th width="18%">PARTIDO / SEDE</th>
            <th width="13%">MARCADOR</th>
            <th width="24%">PRONÓSTICO MULTI-MERCADO</th>
            <th width="23%">PROPS PONCHES ABRIDORES (K)</th>
            <th width="22%">ANÁLISIS Y RESULTADOS</th>
        </tr>
    </thead>
    <tbody>
        {% for r in resultados %}
        <tr>
            <td>
                <div class="partido-title">{{ r.partido }}</div>
                <div class="sede-sub">{{ r.sede }}</div>
            </td>
            <td>
                <div><b>{{ r.marcador_resumen }}</b></div>
                <div style="color:#555; font-size:10px;">{{ r.marcador_detalle }}</div>
            </td>
            <td>
                <div class="cat-tag" style="color: {{ r.color_tag }};">● {{ r.categoria }}</div>
                <div class="pronostico-val">{{ r.pronostico }}</div>
            </td>
            <td>
                <div class="k-box"><b>Visitante:</b> {{ r.k_prop_away_str }}</div>
                <div class="k-box" style="border-left-color: #52c41a;"><b>Local:</b> {{ r.k_prop_home_str }}</div>
            </td>
            <td>
                <div class="analisis-box">{{ r.analisis | safe }}</div>
                <div class="estatus-cell" style="color: {{ r.estatus_color }}; margin-top: 6px;">{{ r.estatus }}</div>
                <div style="font-size: 10px; color: #555;">{{ r.detalle_evaluacion }}</div>
            </td>
        </tr>
        {% endfor %}
    </tbody>
</table>
</body>
</html>
"""

# ==========================================
# 6. EJECUCIÓN
# ==========================================
if __name__ == "__main__":
    fecha_consulta = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d")
    print(f"Ejecutando Deep Analytics + Multi-Mercado para: {fecha_consulta}...")
    
    partidos = obtener_partidos_mlb(fecha_consulta)
    
    if partidos:
        resultados, plenos, parciales, fallados = [], 0, 0, 0
        for p in partidos:
            res = analizar_partido_deep(p)
            resultados.append(res)
            if "COMPLETO" in res["estatus"] and "✓" in res["estatus"]:
                plenos += 1
            elif "PARCIAL" in res["estatus"]:
                parciales += 1
            elif "FALLADO COMPLETO" in res["estatus"]:
                fallados += 1

        template = Template(HTML_TEMPLATE)
        html_out = template.render(
            fecha=fecha_consulta, total=len(partidos),
            plenos=plenos, parciales=parciales, fallados=fallados,
            resultados=resultados
        )
        
        nombre_archivo = f"Reporte_MLB_K_Props_{fecha_consulta}.html"
        with open(nombre_archivo, "w", encoding="utf-8") as f:
            f.write(html_out)
            
        print(f"¡Éxito! Reporte generado en: '{nombre_archivo}'.")
    else:
        print(f"No se encontraron partidos registrados para la fecha {fecha_consulta}.")