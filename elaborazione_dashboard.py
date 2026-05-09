import os
import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def find_file(keyword):
    for ext in [".csv", ".xlsx", ".xlsm"]:
        for fname in os.listdir(BASE_DIR):
            if keyword.lower() in fname.lower() and fname.lower().endswith(ext):
                return os.path.join(BASE_DIR, fname)
    raise FileNotFoundError(f"File non trovato: {keyword}")

FILE_CAMERA   = find_file("camera")
FILE_SENATO   = find_file("senato")
FILE_EUROPEE  = find_file("europee")
FILE_COMUNALI = find_file("comunali")

PARTY_COLORS = {
    "FDI":      "#1a3a6b",
    "LEGA":     "#009246",
    "FI / PDL": "#2b77c5",
    "PD":       "#e3000f",
    "M5S":      "#f5c400",
    "AVS":      "#d64e12",
    "AZIONE":   "#e8733a",
    "IV":       "#c65d1a",
    "ALTRO":    "#888888",
}

def get_color(party):
    return PARTY_COLORS.get(party, "#555555")

def read_file(path):
    try:
        if path.endswith(".csv"):
            df = pd.read_csv(path)
        else:
            df = pd.read_excel(path)
        df.columns = [str(c).strip().lower() for c in df.columns]
        if "lista" in df.columns and "lista/partito" not in df.columns:
            df = df.rename(columns={"lista": "lista/partito"})
        return df
    except Exception as e:
        print(f"Errore lettura {path}: {e}")
        return pd.DataFrame()

def normalize_party(n):
    n = str(n).lower().strip()
    if not n or "totale" in n or "candidato" in n or "uninominale" in n:
        return None
    if "pd" in n or "ulivo" in n or "democratico" in n or "progressista" in n:
        return "PD"
    if "forza italia" in n or "pdl" in n or "popolo della liberta" in n or "moderati" in n:
        return "FI / PDL"
    if "lega" in n:
        return "LEGA"
    if "fdi" in n or "fratelli" in n:
        return "FDI"
    if "5 stelle" in n or "m5s" in n or "movimento 5" in n:
        return "M5S"
    if "verdi" in n or "sinistra" in n or "avs" in n:
        return "AVS"
    if "azione" in n:
        return "AZIONE"
    if "italia viva" in n or "calenda" in n:
        return "IV"
    return None

def parse_pct(val):
    try:
        return float(str(val).replace(",", ".").replace("%", "").strip())
    except:
        return None

def extract_year(value):
    try:
        s = str(value).strip()
        if "/" in s:
            return int(s.split("/")[-1])
        return int(s[:4])
    except:
        return None

def build_trend(df):
    if df.empty:
        return {}
    res = {}
    for _, r in df.iterrows():
        p = normalize_party(r.get("lista/partito", ""))
        if not p:
            continue
        anno = extract_year(r.get("data", r.get("anno", "")))
        if not anno:
            continue
        val = parse_pct(r.get("percentuale"))
        if val is None:
            continue
        res.setdefault(p, {})
        res[p][anno] = res[p].get(anno, 0) + val
    filtered = {}
    for p, values in res.items():
        anni = sorted(values.keys())
        if len(anni) < 3:
            continue
        if max(values.values()) < 3:
            continue
        filtered[p] = values
    return filtered

def build_snapshot(df):
    if df.empty:
        return [], "N/D"
    anni = [extract_year(r.get("data", "")) for _, r in df.iterrows()]
    anni = [a for a in anni if a]
    if not anni:
        return [], "N/D"
    anno_max = max(anni)
    res = {}
    for _, r in df.iterrows():
        if extract_year(r.get("data", "")) != anno_max:
            continue
        p = normalize_party(r.get("lista/partito", ""))
        if not p:
            continue
        val = parse_pct(r.get("percentuale"))
        if val is None:
            continue
        res[p] = res.get(p, 0) + val
    return sorted(res.items(), key=lambda x: -x[1]), anno_max

def build_comunali(df):
    if df.empty:
        return {}
    res = {}
    for _, r in df.iterrows():
        anno = extract_year(r.get("data", ""))
        if not anno:
            continue
        lista = str(r.get("lista/partito", "")).strip()
        if "candidato sindaco" in lista.lower():
            continue
        val = parse_pct(r.get("percentuale"))
        if val is None:
            continue
        cand = str(r.get("candidato_riferimento", "N/D")).strip()
        res.setdefault(anno, [])
        res[anno].append({"lista": lista, "pct": val, "cand": cand})
    return res

DF_CAM  = read_file(FILE_CAMERA)
DF_SEN  = read_file(FILE_SENATO)
DF_EUR  = read_file(FILE_EUROPEE)
DF_COM  = read_file(FILE_COMUNALI)

T_CAM = build_trend(DF_CAM)
T_SEN = build_trend(DF_SEN)
T_EUR = build_trend(DF_EUR)

ALL_P = sorted(set(list(T_CAM.keys()) + list(T_SEN.keys()) + list(T_EUR.keys())))
COM_DATA = build_comunali(DF_COM)
SNAP_CAM, ANNO_CAM = build_snapshot(DF_CAM)
SNAP_SEN, ANNO_SEN = build_snapshot(DF_SEN)
SNAP_EUR, ANNO_EUR = build_snapshot(DF_EUR)

GRAPH_CONFIG = {"staticPlot": True, "displayModeBar": False, "scrollZoom": False, "doubleClick": False, "responsive": True}

def make_trend_fig(title, data, party, color):
    if not party or party not in data:
        fig = go.Figure()
        fig.update_layout(title=f"{title} - dati non disponibili", template="plotly_white", height=320)
        return fig
    anni   = sorted(data[party].keys())
    valori = [round(data[party][a], 1) for a in anni]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=anni, y=valori, mode="lines+markers+text",
        text=[f"{v}%" for v in valori], textposition="top center",
        line=dict(width=3, color=color), marker=dict(size=9, color=color),
        hovertemplate="%{x}: %{y}%<extra></extra>"
    ))
    fig.update_layout(
        title=dict(text=title, x=0.5), template="plotly_white", height=320,
        dragmode=False, hovermode=False, margin=dict(l=35, r=10, t=45, b=30),
        xaxis=dict(fixedrange=True, showgrid=False),
        yaxis=dict(fixedrange=True, ticksuffix="%", gridcolor="#e8e8e8",
                   range=[max(0, min(valori)-8), min(100, max(valori)+14)])
    )
    return fig

def make_bar_fig(title, snap, anno):
    if not snap:
        fig = go.Figure()
        fig.update_layout(title=f"{title} - dati non disponibili", template="plotly_white", height=320)
        return fig
    partiti = [s[0] for s in snap]
    valori  = [round(s[1], 1) for s in snap]
    colori  = [get_color(p) for p in partiti]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=partiti, y=valori, marker_color=colori,
        text=[f"{v}%" for v in valori], textposition="outside",
        hovertemplate="%{x}: %{y}%<extra></extra>"
    ))
    fig.update_layout(
        title=dict(text=f"{title} - {anno}", x=0.5), template="plotly_white", height=350,
        dragmode=False, hovermode=False, margin=dict(l=35, r=10, t=50, b=60),
        xaxis=dict(fixedrange=True),
        yaxis=dict(fixedrange=True, ticksuffix="%", gridcolor="#e8e8e8", range=[0, max(valori)+15])
    )
    return fig

def build_comunali_layout(data):
    if not data:
        return html.P("Nessun dato disponibile.", className="text-muted")
    cards = []
    for anno in sorted(data.keys(), reverse=True):
        candidati = {}
        for v in data[anno]:
            candidati.setdefault(v["cand"], []).append(v)
        rows_html = []
        for cand, liste in candidati.items():
            for i, l in enumerate(liste):
                rows_html.append(html.Tr([
                    html.Td(cand if i == 0 else "", className="text-muted small"),
                    html.Td(l["lista"]),
                    html.Td(f"{l['pct']}%", className="fw-bold text-end")
                ]))
        cards.append(dbc.Card([
            dbc.CardHeader(html.H5(f"Elezioni Comunali {anno}", className="mb-0")),
            dbc.CardBody(dbc.Table([
                html.Thead(html.Tr([html.Th("Candidato"), html.Th("Lista"), html.Th("%", className="text-end")])),
                html.Tbody(rows_html)
            ], striped=True, hover=True, responsive=True, size="sm"))
        ], className="mb-4"))
    return html.Div(cards)

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY],
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}]
)
app.title = "Osservatorio Villa Cortese"
server = app.server

app.layout = dbc.Container([
    html.Div([
        html.H1("📊 Osservatorio Elettorale", className="mb-0"),
        html.H4("Villa Cortese", className="text-muted mt-0")
    ], className="text-center py-3"),
    html.Hr(className="mt-0"),
    dbc.Tabs(id="tabs", active_tab="tab-snapshot", children=[
        dbc.Tab(label="🗳️ Ultima Tornata", tab_id="tab-snapshot", children=[
            html.P("Risultati ultima elezione disponibile.", className="text-muted mt-3"),
            dbc.Row([
                dbc.Col(dcc.Graph(figure=make_bar_fig("Camera", SNAP_CAM, ANNO_CAM), config=GRAPH_CONFIG), xs=12, lg=4),
                dbc.Col(dcc.Graph(figure=make_bar_fig("Senato", SNAP_SEN, ANNO_SEN), config=GRAPH_CONFIG), xs=12, lg=4),
                dbc.Col(dcc.Graph(figure=make_bar_fig("Europee", SNAP_EUR, ANNO_EUR), config=GRAPH_CONFIG), xs=12, lg=4),
            ])
        ]),
        dbc.Tab(label="📈 Trend Storico", tab_id="tab-trend", children=[
            html.Div([
                html.Label("Seleziona partito:", className="fw-bold mt-3"),
                dcc.Dropdown(
                    id="sel-p",
                    options=[{"label": p, "value": p} for p in ALL_P],
                    value=ALL_P[0] if ALL_P else None,
                    clearable=False, className="mb-3"
                ),
                dbc.Row([
                    dbc.Col(dcc.Graph(id="t-cam", config=GRAPH_CONFIG), xs=12, lg=4),
                    dbc.Col(dcc.Graph(id="t-sen", config=GRAPH_CONFIG), xs=12, lg=4),
                    dbc.Col(dcc.Graph(id="t-eur", config=GRAPH_CONFIG), xs=12, lg=4),
                ])
            ])
        ]),
        dbc.Tab(label="🏛️ Comunali", tab_id="tab-comunali", children=[
            html.P("Storico elezioni comunali.", className="text-muted mt-3"),
            build_comunali_layout(COM_DATA)
        ])
    ]),
    html.Hr(),
    html.P("Dati elaborati automaticamente - uso non ufficiale", className="text-center text-muted small mb-3")
], fluid=True, className="px-2 px-md-4")

@app.callback(
    [Output("t-cam", "figure"), Output("t-sen", "figure"), Output("t-eur", "figure")],
    Input("sel-p", "value")
)
def update_trends(p):
    color = get_color(p)
    return (
        make_trend_fig("Camera dei Deputati",     T_CAM, p, color),
        make_trend_fig("Senato della Repubblica", T_SEN, p, color),
        make_trend_fig("Parlamento Europeo",      T_EUR, p, color),
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(debug=False, host="0.0.0.0", port=port)
