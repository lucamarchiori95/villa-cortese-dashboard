import os
import glob
import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd

# =========================================================
# CONFIGURAZIONE FILE - LOGICA "VILLA_CORTESE_*"
# =========================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def find_file(keyword):
    # Cerchiamo i file con il nome esatto presente su GitHub
    pattern = os.path.join(BASE_DIR, f"villa_cortese_{keyword}.xlsx")
    if os.path.exists(pattern):
        return pattern
    # Fallback se il nome è diverso
    files = glob.glob(os.path.join(BASE_DIR, f"*{keyword}*.xlsx"))
    if files: return files[0]
    raise FileNotFoundError(f"Manca file: {keyword}")

FILE_CAMERA = find_file("camera")
FILE_SENATO = find_file("senato")
FILE_EUROPEE = find_file("europee")
FILE_COMUNALI = find_file("comunali")

# =========================================================
# ELABORAZIONE DATI (Logica da elaborazione_dashboard_bis)
# =========================================================
def read_file(path):
    try:
        df = pd.read_excel(path)
        df.columns = [str(c).strip().lower() for c in df.columns]
        if 'lista' in df.columns and 'lista/partito' not in df.columns:
            df = df.rename(columns={'lista': 'lista/partito'})
        return df
    except: return pd.DataFrame()

def normalize_party(n):
    n = str(n).lower().strip()
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
    return {p: v for p, v in res.items() if len(v) >= 1}

# Caricamento dati
T_CAM = build_trend(read_file(FILE_CAMERA))
T_SEN = build_trend(read_file(FILE_SENATO))
T_EUR = build_trend(read_file(FILE_EUROPEE))
DF_COM = read_file(FILE_COMUNALI)

ALL_P = sorted(set(list(T_CAM.keys()) + list(T_SEN.keys()) + list(T_EUR.keys())))

# =========================================================
# DASH APP
# =========================================================
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
server = app.server

app.layout = dbc.Container([
    html.H1("📊 Osservatorio Villa Cortese", className="text-center my-4 text-primary fw-bold"),

    dbc.Tabs([
        # SCHEDA COMUNALI - ORA AL PRIMO POSTO
        dbc.Tab(label="🏠 Comunali", children=[
            html.Div([
                html.H3("Risultati Elezioni Comunali", className="mt-4 mb-3"),
                # Qui la logica specifica per le comunali (Tabella o Grafico)
                dcc.Graph(
                    id='graph-comunali',
                    figure=go.Figure(data=[
                        go.Bar(x=DF_COM['lista/partito'], y=DF_COM['percentuale'], marker_color='#1a5a96')
                    ]).update_layout(title="Risultati Comunali", template="plotly_white")
                ) if not DF_COM.empty else html.P("Dati non disponibili")
            ], className="p-3")
        ]),

        # SCHEDA TREND STORICO
        dbc.Tab(label="📈 Trend Storico", children=[
            html.Div([
                html.Label("Seleziona Partito:", className="mt-3 fw-bold"),
                dcc.Dropdown(id="sel-p", options=[{"label": p, "value": p} for p in ALL_P], 
                             value=ALL_P[0] if ALL_P else None, className="mb-4"),
                
                dbc.Row([
                    dbc.Col(dcc.Graph(id="t-cam", config={'staticPlot': True}), width=12, lg=4),
                    dbc.Col(dcc.Graph(id="t-sen", config={'staticPlot': True}), width=12, lg=4),
                    dbc.Col(dcc.Graph(id="t-eur", config={'staticPlot': True}), width=12, lg=4),
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
            fig = go.Figure().update_layout(title=tit)
        else:
            anni = sorted(d[p].keys()); valori = [d[p][a] for a in anni]
            fig = go.Figure(go.Scatter(x=anni, y=valori, mode="lines+markers+text", 
                                     text=[f"{v}%" for v in valori], textposition="top center",
                                     line=dict(width=4, color="#1a5a96")))
            fig.update_layout(title=f"Trend {tit}", template="plotly_white", height=350)
        figs.append(fig)
    return figs[0], figs[1], figs[2]

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=8050)
