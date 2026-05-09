import os
import glob
import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd

# =========================================================
# CONFIGURAZIONE FILE (Logica per Render)
# =========================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def find_file(keyword):
    # Cerca i file villa_cortese_... come presenti su GitHub
    patterns = [f"villa_cortese_{keyword}.xlsx", f"*{keyword}*.xlsx", f"*{keyword}*.csv"]
    for p in patterns:
        files = glob.glob(os.path.join(BASE_DIR, p))
        if files: return files[0]
    raise FileNotFoundError(f"Manca file: {keyword}")

FILE_CAMERA   = find_file("camera")
FILE_SENATO   = find_file("senato")
FILE_EUROPEE  = find_file("europee")
FILE_COMUNALI = find_file("comunali")

# =========================================================
# ELABORAZIONE DATI (Logica da elaborazione_dashboard_bis.py)
# =========================================================
def read_file(path):
    try:
        df = pd.read_csv(path) if path.endswith(".csv") else pd.read_excel(path)
        df.columns = [str(c).strip().lower() for c in df.columns]
        if 'lista' in df.columns and 'lista/partito' not in df.columns:
            df = df.rename(columns={'lista': 'lista/partito'})
        return df
    except: return pd.DataFrame()

def normalize_party(n):
    n = str(n).lower()
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
            anno, val = int(r["anno"]), float(str(r["percentuale"]).replace(",", ".").replace("%", ""))
            res.setdefault(p, {})
            res[p][anno] = res[p].get(anno, 0) + val
        except: continue
    return {p: v for p, v in res.items() if len(v) >= 1} # Logica originale

# Caricamento dati per tutte le categorie
T_CAM = build_trend(read_file(FILE_CAMERA))
T_SEN = build_trend(read_file(FILE_SENATO))
T_EUR = build_trend(read_file(FILE_EUROPEE))
T_COM = build_trend(read_file(FILE_COMUNALI))

ALL_P = sorted(set(list(T_CAM.keys()) + list(T_SEN.keys()) + list(T_EUR.keys()) + list(T_COM.keys())))

# =========================================================
# DASH APP
# =========================================================
app = dash.Dash(__name__, 
                external_stylesheets=[dbc.themes.FLATLY],
                meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}])
server = app.server

app.layout = dbc.Container([
    html.H1("📊 Osservatorio Villa Cortese", className="text-center my-4 text-primary fw-bold"),

    dbc.Tabs([
        # 1. SCHEDA COMUNALI (Logica identica a trend storico)
        dbc.Tab(label="🏛️ Comunali", children=[
            html.Div([
                html.Label("Seleziona Partito (Comunali):", className="mt-3 fw-bold"),
                dcc.Dropdown(id="sel-p-com", options=[{"label": p, "value": p} for p in sorted(T_COM.keys())], 
                             value=sorted(T_COM.keys())[0] if T_COM else None, className="mb-4"),
                dbc.Row([
                    dbc.Col(dcc.Graph(id="t-com", config={'staticPlot': True}), width=12, className="mb-4"),
                ])
            ], className="p-3")
        ]),

        # 2. SCHEDA TREND NAZIONALI
        dbc.Tab(label="📈 Trend Nazionali/Europee", children=[
            html.Div([
                html.Label("Seleziona Partito:", className="mt-3 fw-bold"),
                dcc.Dropdown(id="sel-p", options=[{"label": p, "value": p} for p in ALL_P], 
                             value=ALL_P[0] if ALL_P else None, className="mb-4"),
                
                dbc.Row([
                    dbc.Col(dcc.Graph(id="t-cam", config={'staticPlot': True}), width=12, lg=4, className="mb-4"),
                    dbc.Col(dcc.Graph(id="t-sen", config={'staticPlot': True}), width=12, lg=4, className="mb-4"),
                    dbc.Col(dcc.Graph(id="t-eur", config={'staticPlot': True}), width=12, lg=4, className="mb-4"),
                ])
            ], className="mt-2")
        ])
    ])
], fluid=True)

# Callback per la scheda Comunali
@app.callback(Output("t-com", "figure"), Input("sel-p-com", "value"))
def update_comunali(p):
    if not p or p not in T_COM: return go.Figure().update_layout(title="Dati non disponibili")
    anni = sorted(T_COM[p].keys()); valori = [T_COM[p][a] for a in anni]
    fig = go.Figure(go.Scatter(x=anni, y=valori, mode="lines+markers+text", 
                             text=[f"{v}%" for v in valori], textposition="top center",
                             line=dict(width=4, color="#e63946")))
    fig.update_layout(title=dict(text=f"Trend Comunali - {p}", x=0.5), template="plotly_white", height=450)
    return fig

# Callback per Camera, Senato, Europee
@app.callback(
    [Output("t-cam", "figure"), Output("t-sen", "figure"), Output("t-eur", "figure")],
    Input("sel-p", "value")
)
def update_trends(p):
    figs = []
    for tit, d in [("Camera", T_CAM), ("Senato", T_SEN), ("Europee", T_EUR)]:
        if not p or p not in d:
            fig = go.Figure().update_layout(title=tit)
        else:
            anni = sorted(d[p].keys()); valori = [d[p][a] for a in anni]
            fig = go.Figure(go.Scatter(x=anni, y=valori, mode="lines+markers+text", 
                                     text=[f"{v}%" for v in valori], textposition="top center",
                                     line=dict(width=4, color="#1a5a96")))
            fig.update_layout(title=dict(text=f"Trend {tit}", x=0.5), template="plotly_white", height=350)
        figs.append(fig)
    return figs[0], figs[1], figs[2]

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=8050)
