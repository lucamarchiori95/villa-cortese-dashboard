import os
import glob
import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd

# =========================================================
# CONFIGURAZIONE FILE
# =========================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def find_file(name):
    # Cerchiamo il file esatto in minuscolo come su GitHub
    for ext in [".xlsx", ".xlsm", ".csv"]:
        path = os.path.join(BASE_DIR, f"{name}{ext}")
        if os.path.exists(path):
            return path
    # Se non lo trova esatto, prova il vecchio metodo glob (ma solo minuscolo)
    files = glob.glob(os.path.join(BASE_DIR, f"*{name.lower()}*"))
    if files:
        return files[0]
    raise FileNotFoundError(f"Impossibile trovare il file: {name}")

# Nomi file definiti in minuscolo per massima compatibilità Linux/Render
FILE_CAMERA = find_file("camera")
FILE_SENATO = find_file("senato")
FILE_EUROPEE = find_file("europee")
FILE_COMUNALI = find_file("comunali")

# =========================================================
# ELABORAZIONE DATI
# =========================================================
def read_file(path):
    try:
        df = pd.read_csv(path) if path.endswith(".csv") else pd.read_excel(path)
        df.columns = [str(c).strip().lower() for c in df.columns]
        if 'lista' in df.columns and 'lista/partito' not in df.columns:
            df = df.rename(columns={'lista': 'lista/partito'})
        return df
    except Exception as e:
        print(f"Errore lettura {path}: {e}")
        return pd.DataFrame()

def normalize_party(n):
    n = str(n).lower().strip()
    if not n or "totale" in n: return None
    if "pd" in n or "ulivo" in n: return "PD"
    if "forza italia" in n or "pdl" in n: return "FI / PDL"
    if "lega" in n: return "LEGA"
    if "fdi" in n or "fratelli" in n: return "FDI"
    if "5 stelle" in n or "m5s" in n: return "M5S"
    return n.upper()

def build_trend(df):
    if df.empty: return {}
    res = {}
    for _, r in df.iterrows():
        try:
            p = normalize_party(r["lista/partito"])
            if not p: continue
            anno = int(r["anno"])
            # Pulizia valore percentuale
            val_str = str(r["percentuale"]).replace(",", ".").replace("%", "").strip()
            val = float(val_str)
            res.setdefault(p, {})
            res[p][anno] = res[p].get(anno, 0) + val
        except: continue
    # Mostra solo partiti con almeno 2 rilevazioni storiche
    return {p: v for p, v in res.items() if len(v) >= 2}

T_CAM = build_trend(read_file(FILE_CAMERA))
T_SEN = build_trend(read_file(FILE_SENATO))
T_EUR = build_trend(read_file(FILE_EUROPEE))

ALL_P = sorted(set(list(T_CAM.keys()) + list(T_SEN.keys()) + list(T_EUR.keys())))

# =========================================================
# DASH APP
# =========================================================
app = dash.Dash(__name__, 
                external_stylesheets=[dbc.themes.FLATLY],
                meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}])

app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>Osservatorio Villa Cortese</title>
        {%favicon%}
        {%css%}
        <style>
            /* Reset per evitare scroll laterali su mobile */
            body { overflow-x: hidden; }
            .container-fluid { padding: 0 15px; }
            
            /* BLOCCA OGNI INTERAZIONE SUI GRAFICI */
            .static-graph {
                pointer-events: none !important;
                touch-action: none !important;
                user-select: none !important;
            }
            .modebar { display: none !important; }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

server = app.server

app.layout = dbc.Container([
    html.H1("📊 Osservatorio Villa Cortese", className="text-center my-4 text-primary fw-bold"),

    dbc.Tabs([
        dbc.Tab(label="📈 Trend Storico", children=[
            html.Div([
                html.Label("Seleziona Partito:", className="mt-3 fw-bold"),
                dcc.Dropdown(
                    id="sel-p", 
                    options=[{"label": p, "value": p} for p in ALL_P], 
                    value=ALL_P[0] if ALL_P else None, 
                    className="mb-4",
                    clearable=False
                ),
                
                dbc.Row([
                    dbc.Col(dcc.Graph(id="t-cam", className="static-graph", config={'staticPlot': True}), width=12, lg=4, className="mb-4"),
                    dbc.Col(dcc.Graph(id="t-sen", className="static-graph", config={'staticPlot': True}), width=12, lg=4, className="mb-4"),
                    dbc.Col(dcc.Graph(id="t-eur", className="static-graph", config={'staticPlot': True}), width=12, lg=4, className="mb-4"),
                ])
            ], className="mt-2")
        ])
    ])
], fluid=True)

@app.callback(
    [Output("t-cam", "figure"), Output("t-sen", "figure"), Output("t-eur", "figure")],
    Input("sel-p", "value")
)
def update_trends(p):
    figs = []
    for tit, d in [("Camera", T_CAM), ("Senato", T_SEN), ("Europee", T_EUR)]:
        if not p or p not in d:
            # Crea un grafico vuoto pulito se il partito non ha dati in quella categoria
            fig = go.Figure().update_layout(
                title=dict(text=f"Trend {tit} (Dati non disp.)", x=0.5),
                template="plotly_white", height=350
            )
        else:
            anni = sorted(d[p].keys())
            valori = [round(d[p][a], 2) for a in anni]
            fig = go.Figure(go.Scatter(
                x=anni, y=valori, 
                mode="lines+markers+text", 
                text=[f"{v}%" for v in valori], 
                textposition="top center",
                line=dict(width=4, color="#1a5a96"),
                marker=dict(size=10)
            ))
            fig.update_layout(
                title=dict(text=f"Trend {tit}", x=0.5),
                xaxis=dict(tickvals=anni, fixedrange=True, showgrid=False),
                yaxis=dict(range=[0, max(valori) + 15] if valori else [0, 100], fixedrange=True),
                template="plotly_white", 
                margin=dict(l=10, r=10, t=50, b=10), 
                height=350,
                hovermode=False
            )
        figs.append(fig)
    return figs[0], figs[1], figs[2]

if __name__ == "__main__":
    # In locale usa la porta 8050, Render userà la variabile d'ambiente PORT
    port = int(os.environ.get("PORT", 8050))
    app.run(debug=False, host='0.0.0.0', port=port)