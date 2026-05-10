import os
import glob
import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd

# =========================================================
# 1. DIRECTORY FILE (CORRETTA PER GITHUB/RENDER)
# =========================================================
# Questo comando dice al codice di cercare i file nella stessa cartella dove si trova lo script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# =========================================================
# 2. RICERCA AUTOMATICA FILE
# =========================================================
def find_file(keyword):
    # Cerchiamo i tuoi file .xlsm
    patterns = [f"*{keyword}*.xlsm", f"*{keyword}*.xlsx", f"*{keyword}*.xls"]
    for pattern in patterns:
        files = glob.glob(os.path.join(BASE_DIR, pattern))
        if files:
            return files[0]
    return None

FILE_CAMERA = find_file("camera")
FILE_SENATO = find_file("senato")
FILE_EUROPEE = find_file("europee")
FILE_COMUNALI = find_file("comunali")

# =========================================================
# 3. LETTURA FILE (ENGINE PER XLSM)
# =========================================================
def read_file(path):
    if not path or not os.path.exists(path):
        return pd.DataFrame()
    try:
        # Usiamo openpyxl per leggere i file Excel con macro
        df = pd.read_excel(path, engine='openpyxl')
        df.columns = [str(c).strip().lower() for c in df.columns]
        return df
    except Exception as e:
        print(f"Errore lettura {path}: {e}")
        return pd.DataFrame()

# =========================================================
# 4. LOGICA DATI E NORMALIZZAZIONE (IDENTICA ALL'ORIGINALE)
# =========================================================
def normalize_party(name):
    n = str(name).strip().lower()
    exclude_keywords = ["candidato", "uninominale", "totale", "solo", "voti"]
    if any(x in n for x in exclude_keywords): return None
    if any(x in n for x in ["partito democratico", "pd", "l'ulivo", "margherita", "ds"]) or n in ["pd", "ds", "ulivo"]: return "PD (ex Ulivo/DS)"
    if any(x in n for x in ["forza italia", "pdl", "popolo della libertà"]) or n == "fi": return "FI / PDL"
    if any(x in n for x in ["fratelli d'italia", "fdi", "alleanza nazionale"]) or n in ["fdi", "an"]: return "FDI / AN"
    if "lega" in n: return "LEGA"
    if any(x in n for x in ["movimento 5 stelle", "m5s"]): return "M5S"
    if any(x in n for x in ["udc", "unione di centro"]): return "UDC"
    if any(x in n for x in ["rifondazione", "comunisti", "sinistra italiana", "avs"]): return "SINISTRA"
    return str(name).strip().upper()

def build_trend(df):
    if df.empty: return {}
    result = {}
    for _, row in df.iterrows():
        try:
            anno = int(row["anno"])
            partito_norm = normalize_party(row["lista/partito"])
            if not partito_norm: continue
            perc = float(str(row["percentuale"]).replace(",", "."))
            if partito_norm not in result: result[partito_norm] = {}
            result[partito_norm][anno] = result[partito_norm].get(anno, 0) + perc
        except: continue
    return {p: {a: round(v, 2) for a, v in sorted(vals.items())} for p, vals in result.items() if len(vals) >= 3}

def build_comunali(df):
    if df.empty: return []
    result = []
    anni = sorted([int(a) for a in df["anno"].dropna().unique() if int(a) >= 2001])
    for anno in anni:
        temp = df[df["anno"] == anno].copy()
        temp["voti"] = pd.to_numeric(temp["voti"], errors="coerce").fillna(0)
        temp["percentuale"] = pd.to_numeric(temp["percentuale"], errors="coerce").fillna(0)
        temp = temp.sort_values(by="voti", ascending=False)
        if len(temp) < 2: continue
        primo = temp.iloc[0]
        opp = temp.iloc[1:]
        result.append([int(anno), int(primo["voti"]), round(float(primo["percentuale"]), 2), int(opp["voti"].sum()), round(float(opp["percentuale"].sum()), 2)])
    return result

# =========================================================
# 5. INIZIALIZZAZIONE DATI
# =========================================================
df_camera = read_file(FILE_CAMERA)
df_senato = read_file(FILE_SENATO)
df_europee = read_file(FILE_EUROPEE)
df_comunali = read_file(FILE_COMUNALI)

TREND_CAMERA = build_trend(df_camera)
TREND_SENATO = build_trend(df_senato)
TREND_EUROPEE = build_trend(df_europee)
DATA_COM = build_comunali(df_comunali)

ALL_PARTIES = sorted(list(set(list(TREND_CAMERA.keys()) + list(TREND_SENATO.keys()) + list(TREND_EUROPEE.keys()))))

# =========================================================
# 6. DASH APP (CONFIGURAZIONE PER RENDER)
# =========================================================
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
server = app.server # <--- FONDAMENTALE PER GUNICORN
app.title = "Osservatorio Villa Cortese"

app.layout = dbc.Container([
    html.H1("📊 Osservatorio Villa Cortese (2001-2024)", className="text-center my-4 text-primary fw-bold"),
    dbc.Tabs([
        dbc.Tab(label="🏘️ Comunali", children=[
            dbc.Row([
                dbc.Col([html.H5("Performance %", className="mt-3 text-secondary"), html.Div(id="tab-com-perc")], md=4),
                dbc.Col(dcc.Graph(id="graf-com-perc"), md=8)
            ]),
            html.Hr(),
            dbc.Row([
                dbc.Col([html.H5("Voti Assoluti", className="mt-3 text-secondary"), html.Div(id="tab-com-voti")], md=4),
                dbc.Col(dcc.Graph(id="graf-com-voti"), md=8)
            ])
        ]),
        dbc.Tab(label="📈 Trend Storico Partiti", children=[
            html.Label("Seleziona Partito:", className="mt-3 fw-bold"),
            dcc.Dropdown(id="sel-partito", options=[{"label": p, "value": p} for p in ALL_PARTIES], value=ALL_PARTIES[0] if ALL_PARTIES else None, className="mb-3"),
            dbc.Row([
                dbc.Col(dcc.Graph(id="trend-cam", config={"staticPlot": True}), md=4),
                dbc.Col(dcc.Graph(id="trend-sen", config={"staticPlot": True}), md=4),
                dbc.Col(dcc.Graph(id="trend-eur", config={"staticPlot": True}), md=4)
            ])
        ])
    ])
], fluid=True)

# Callback Trend (con staticPlot) e Comunali rimaste identiche
@app.callback(
    [Output("tab-com-perc", "children"), Output("tab-com-voti", "children"), Output("graf-com-perc", "figure"), Output("graf-com-voti", "figure")],
    Input("sel-partito", "value")
)
def update_comunali(_):
    if not DATA_COM: return "", "", go.Figure(), go.Figure()
    df = pd.DataFrame(DATA_COM, columns=["Anno", "Voti Insieme", "Perc Insieme", "Voti Opposizione", "Perc Opposizione"])
    df_t1 = df[["Anno", "Perc Insieme", "Perc Opposizione"]].copy()
    df_t1.columns = ["Anno", "Insieme per Villa", "Opposizione"]
    df_t2 = df[["Anno", "Voti Insieme", "Voti Opposizione"]].copy()
    df_t2.columns = ["Anno", "Insieme per Villa", "Opposizione"]
    
    anni = df["Anno"].tolist()
    f1 = go.Figure()
    f1.add_trace(go.Scatter(x=anni, y=df["Perc Insieme"], name="Insieme per Villa", line=dict(width=4, color="#d9534f"), mode="lines+markers+text", text=df["Perc Insieme"].apply(lambda x: f"{x}%"), textposition="top center"))
    f1.add_trace(go.Scatter(x=anni, y=df["Perc Opposizione"], name="Opposizione", line=dict(width=4, color="#0275d8"), mode="lines+markers+text", text=df["Perc Opposizione"].apply(lambda x: f"{x}%"), textposition="bottom center"))
    f1.update_layout(yaxis=dict(range=[0, 105]), xaxis=dict(tickvals=anni), template="plotly_white", height=350)

    f2 = go.Figure()
    f2.add_trace(go.Bar(x=anni, y=df["Voti Insieme"], name="Insieme per Villa", marker_color="#d9534f", text=df["Voti Insieme"], textposition="outside"))
    f2.add_trace(go.Bar(x=anni, y=df["Voti Opposizione"], name="Opposizione", marker_color="#0275d8", text=df["Voti Opposizione"], textposition="outside"))
    f2.update_layout(barmode="group", xaxis=dict(tickvals=anni), template="plotly_white", height=350)
    return dbc.Table.from_dataframe(df_t1, striped=True, bordered=True), dbc.Table.from_dataframe(df_t2, striped=True, bordered=True), f1, f2

@app.callback(
    [Output("trend-cam", "figure"), Output("trend-sen", "figure"), Output("trend-eur", "figure")],
    Input("sel-partito", "value")
)
def update_trends(partito):
    figs = []
    datasets = [("Camera", TREND_CAMERA), ("Senato", TREND_SENATO), ("Europee", TREND_EUROPEE)]
    for titolo, data in datasets:
        if not data or partito not in data:
            fig = go.Figure()
            fig.update_layout(title=f"Trend {titolo}: N/D", template="plotly_white", height=400)
            figs.append(fig); continue
        points = data[partito]
        anni_p = sorted(points.keys())
        valori = [points[a] for a in anni_p]
        fig = go.Figure(go.Scatter(x=anni_p, y=valori, mode="lines+markers+text", text=[f"{v}%" for v in valori], textposition="top center", line=dict(width=4, color="#1a5a96")))
        fig.update_layout(title=f"Trend {titolo}", xaxis=dict(tickvals=anni_p), template="plotly_white", height=400)
        figs.append(fig)
    return figs[0], figs[1], figs[2]

if __name__ == "__main__":
    app.run(debug=True)
