import sys
import requests
import json
from datetime import datetime
from jinja2 import Template

# ==========================================
# 1. SCRAPER DE DATOS REALES (ESPN KBO)
# ==========================================
def obtener_datos_reales_kbo(fecha_str):
    # Limpiar cualquier guion o espacio para asegurar formato YYYYMMDD
    fecha_clean = fecha_str.replace("-", "").strip()
    
    # URL directa de la API de ESPN para la KBO
    url = f"https://site.api.espn.com/apis/site/v2/sports/baseball/kbo/scoreboard?dates={fecha_clean}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
    except Exception as e:
        print(f"Error al conectar con la API de ESPN: {e}")
        return []

    partidos = []
    events = data.get("events", [])
    
    for event in events:
        try:
            competition = event["competitions"][0]
            competitors = competition["competitors"]
            
            home_data = next(c for c in competitors if c["homeAway"] == "home")
            away_data = next(c for c in competitors if c["homeAway"] == "away")
            
            home_team = home_data["team"]["displayName"]
            away_team = away_data["team"]["displayName"]
            
            home_score = int(home_data.get("score", 0))
            away_score = int(away_data.get("score", 0))
            
            status_state = event["status"]["type"]["state"]
            status_desc = "Finalizado" if status_state == "post" else ("En Vivo" if status_state == "in" else "Por Jugar")
            
            # Extraer abridores si están disponibles en la API
            away_pitcher = "Por Confirmar"
            home_pitcher = "Por Confirmar"
            
            if "probables" in away_data and len(away_data["probables"]) > 0:
                away_pitcher = away_data["probables"][0].get("athlete", {}).get("displayName", "Por Confirmar")
            if "probables" in home_data and len(home_data["probables"]) > 0:
                home_pitcher = home_data["probables"][0].get("athlete", {}).get("displayName", "Por Confirmar")

            partidos.append({
                "id": event["id"],
                "away_team": away_team,
                "home_team": home_team,
                "away_score": away_score,
                "home_score": home_score,
                "status": status_desc,
                "away_pitcher": away_pitcher,
                "home_pitcher": home_pitcher
            })
        except Exception as err:
            continue
            
    return partidos

# ==========================================
# 2. MOTOR PREDICTIVO MULTI-MERCADO
# ==========================================
def analizar_partido(p):
    AVG_KBO_RUNS = 4.8 
    
    # Proyecciones base por localía y ventaja
    away_expected_runs = round(AVG_KBO_RUNS * 0.95, 1)
    home_expected_runs = round(AVG_KBO_RUNS * 1.05, 1)
    
    total_linea = 9.5
    tt_away_linea = 4.5
    tt_home_linea = 4.5

    # Picks sugeridos
    pick_ml = p["home_team"] if home_expected_runs > away_expected_runs else p["away_team"]
    pick_tt_away = f"{p['away_team']} OVER {tt_away_linea}" if away_expected_runs > tt_away_linea else f"{p['away_team']} UNDER {tt_away_linea}"
    pick_tt_home = f"{p['home_team']} OVER {tt_home_linea}" if home_expected_runs > tt_home_linea else f"{p['home_team']} UNDER {tt_home_linea}"
    pick_total = f"OVER {total_linea}" if (away_expected_runs + home_expected_runs) >= total_linea else f"UNDER {total_linea}"

    # Evaluación contra resultados reales
    estatus_ml, color_ml = "PENDIENTE", "#6c757d"
    estatus_tt_away, color_tt_away = "PENDIENTE", "#6c757d"
    estatus_tt_home, color_tt_home = "PENDIENTE", "#6c757d"
    estatus_total, color_total = "PENDIENTE", "#6c757d"

    if p["status"] == "Finalizado":
        a_sc = p["away_score"]
        h_sc = p["home_score"]
        total_real = a_sc + h_sc
        ganador_real = p["home_team"] if h_sc > a_sc else p["away_team"]

        # Evaluaciones
        estatus_ml, color_ml = ("✓ ACERTADO", "#28a745") if pick_ml == ganador_real else ("X FALLADO", "#dc3545")
        
        cond_tt_away = (a_sc > tt_away_linea) if "OVER" in pick_tt_away else (a_sc < tt_away_linea)
        estatus_tt_away, color_tt_away = ("✓ ACERTADO", "#28a745") if cond_tt_away else ("X FALLADO", "#dc3545")
        
        cond_tt_home = (h_sc > tt_home_linea) if "OVER" in pick_tt_home else (h_sc < tt_home_linea)
        estatus_tt_home, color_tt_home = ("✓ ACERTADO", "#28a745") if cond_tt_home else ("X FALLADO", "#dc3545")

        cond_total = (total_real > total_linea) if "OVER" in pick_total else (total_real < total_linea)
        estatus_total, color_total = ("✓ ACERTADO", "#28a745") if cond_total else ("X FALLADO", "#dc3545")

    return {
        "partido": f"{p['away_team']} vs {p['home_team']}",
        "marcador_real": f"{p['away_score']} - {p['home_score']}" if p["status"] == "Finalizado" else "Por Jugar",
        "status": p["status"],
        "pitchers": f"<b>{p['away_team']}:</b> {p['away_pitcher']}<br><b>{p['home_team']}:</b> {p['home_pitcher']}",
        "pick_ml": pick_ml, "estatus_ml": estatus_ml, "color_ml": color_ml,
        "pick_tt_away": pick_tt_away, "estatus_tt_away": estatus_tt_away, "color_tt_away": color_tt_away,
        "pick_tt_home": pick_tt_home, "estatus_tt_home": estatus_tt_home, "color_tt_home": color_tt_home,
        "pick_total": pick_total, "estatus_total": estatus_total, "color_total": color_total
    }

# ==========================================
# 3. INTERFAZ GRÁFICA HTML
# ==========================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>KBO Real Analytics Dashboard</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f0f2f5; margin: 0; padding: 20px; color: #1c1e21; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: #001529; color: white; padding: 20px; border-radius: 12px; margin-bottom: 20px; }
        .header h1 { margin: 0; font-size: 22px; }
        .card { background: white; border-radius: 12px; padding: 18px; margin-bottom: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); display: grid; grid-template-columns: 2fr 1fr 2fr 2fr; gap: 15px; align-items: center; }
        .team-title { font-size: 15px; font-weight: bold; color: #001529; }
        .score-badge { font-size: 18px; font-weight: 800; background: #e6f7ff; color: #1890ff; padding: 6px 12px; border-radius: 6px; text-align: center; }
        .pick-group { font-size: 12px; line-height: 1.8; }
        .badge { font-size: 10px; font-weight: bold; padding: 3px 6px; border-radius: 4px; color: white; margin-left: 4px; }
        .pitcher-text { font-size: 11px; color: #666; }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>⚾ KBO Dashboard Predicciones Reales</h1>
        <small>Datos extraídos de ESPN API | Fecha consultada: {{ fecha }}</small>
    </div>

    {% for r in resultados %}
    <div class="card">
        <div>
            <div class="team-title">{{ r.partido }}</div>
            <div class="pitcher-text" style="margin-top: 5px;">{{ r.pitchers | safe }}</div>
        </div>
        <div style="text-align: center;">
            <div class="score-badge">{{ r.marcador_real }}</div>
            <div style="font-size: 10px; color: #8c8c8c; margin-top: 4px;">{{ r.status }}</div>
        </div>
        <div class="pick-group">
            <div><b>Ganador (ML):</b> {{ r.pick_ml }} <span class="badge" style="background: {{ r.color_ml }}">{{ r.estatus_ml }}</span></div>
            <div><b>Total Juego:</b> {{ r.pick_total }} <span class="badge" style="background: {{ r.color_total }}">{{ r.estatus_total }}</span></div>
        </div>
        <div class="pick-group">
            <div><b>Team Total Visita:</b> {{ r.pick_tt_away }} <span class="badge" style="background: {{ r.color_tt_away }}">{{ r.estatus_tt_away }}</span></div>
            <div><b>Team Total Local:</b> {{ r.pick_tt_home }} <span class="badge" style="background: {{ r.color_tt_home }}">{{ r.estatus_tt_home }}</span></div>
        </div>
    </div>
    {% else %}
    <div class="card" style="display:block; text-align:center;">
        <b>No se encontraron partidos para la fecha consultada ({{ fecha }}).</b><br>
        <small style="color:#666;">Prueba con una fecha jugada recientemente (ejemplo: 20240529).</small>
    </div>
    {% endfor %}
</div>
</body>
</html>
"""

if __name__ == "__main__":
    fecha_input = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y%m%d")
    
    print(f"Obteniendo partidos REALES para: {fecha_input}...")
    partidos_reales = obtener_datos_reales_kbo(fecha_input)
    
    resultados = [analizar_partido(p) for p in partidos_reales]
        
    template = Template(HTML_TEMPLATE)
    html_out = template.render(fecha=fecha_input, resultados=resultados)
    
    archivo_salida = f"KBO_Reporte_Real_{fecha_input}.html"
    with open(archivo_salida, "w", encoding="utf-8") as f:
        f.write(html_out)
        
    print(f"¡Listo! Archivo generado: '{archivo_salida}'. Total partidos encontrados: {len(resultados)}")