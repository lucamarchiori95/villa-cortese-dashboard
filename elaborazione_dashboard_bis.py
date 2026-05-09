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

def find_file(keyword):
    patterns = [f"*{keyword}*.xlsx", f"*{keyword}*.xlsm", f"*{keyword}*.csv"]
    for p in patterns:
        files = glob.glob(os.path.join(BASE_DIR, p))
        if files: return files[0]
    raise FileNotFoundError(f"Manca file: {keyword}")

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
    return {p: v for p, v in res.items() if len(v) >= 2}

T_CAM, T_SEN, T_EUR = build_trend(read_file(FILE_CAMERA)), build_trend(read_file(FILE_SENATO)), build_trend(read_file(FILE_EUROPEE))
ALL_P = sorted(set(list(T_CAM.keys()) + list(T_SEN.keys()) + list(T_EUR.keys())))

# =========================================================
# DASH APP - IL FIX DEFINITIVO È QUI
# =========================================================

# Usiamo index_string per iniettare il CSS che BLOCCA TUTTO
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
            /* BLOCCA OGNI INTERAZIONE SUI GRAFICI CON CLASSE 'static-graph' */
            .static-graph {
                pointer-events: none !important;
                touch-action: none !important;
                user-select: none !important;
            }
            /* NASCONDE LA BARRA DEGLI STRUMENTI PLOTLY SEMPRE */
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
                dcc.Dropdown(id="sel-p", options=[{"label": p, "value": p} for p in ALL_P], 
                             value=ALL_P[0] if ALL_P else None, className="mb-4"),
                
                dbc.Row([
                    # Applichiamo la classe 'static-graph' definita nello Style sopra
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
        if p not in d:
            fig = go.Figure().update_layout(title=tit)
        else:
            anni = sorted(d[p].keys()); valori = [d[p][a] for a in anni]
            fig = go.Figure(go.Scatter(x=anni, y=valori, mode="lines+markers+text", 
                                     text=[f"{v}%" for v in valori], textposition="top center",
                                     line=dict(width=4, color="#1a5a96")))
            fig.update_layout(
                title=dict(text=f"Trend {tit}", x=0.5),
                xaxis=dict(tickvals=anni, fixedrange=True),
                yaxis=dict(range=[0, max(valori)+15], fixedrange=True),
                template="plotly_white", margin=dict(l=10, r=10, t=50, b=10), height=350,
                hovermode=False # Disabilita i popup al passaggio del mouse
            )
        figs.append(fig)
    return figs[0], figs[1], figs[2]

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=8050)