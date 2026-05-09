import os
import glob
import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd

# =========================================================
# CONFIGURAZIONE FILE (Compatibile Render/Linux)
# =========================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def find_file(keyword):
    patterns = [
        f"villa_cortese_{keyword}.xlsx",
        f"villa_cortese_{keyword}.xlsm",
        f"villa_cortese_{keyword}.csv",
        f"*{keyword}*.xlsx",
        f"*{keyword}*.xlsm",
        f"*{keyword}*.csv"
    ]

    for pattern in patterns:
        files = glob.glob(os.path.join(BASE_DIR, pattern))
        if files:
            return files[0]

    raise FileNotFoundError(f"File non trovato: {keyword}")

FILE_CAMERA   = find_file("camera")
FILE_SENATO   = find_file("senato")
FILE_EUROPEE  = find_file("europee")
FILE_COMUNALI = find_file("comunali")

# =========================================================
# LETTURA FILE
# =========================================================
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

# =========================================================
# NORMALIZZAZIONE PARTITI
# =========================================================
def normalize_party(n):

    n = str(n).lower().strip()

    if not n:
        return None

    if "totale" in n:
        return None

    if "pd" in n or "ulivo" in n:
        return "PD"

    if "forza italia" in n or "pdl" in n:
        return "FI / PDL"

    if "lega" in n:
        return "LEGA"

    if "fdi" in n or "fratelli" in n:
        return "FDI"

    if "5 stelle" in n or "m5s" in n:
        return "M5S"

    return n.upper()

# =========================================================
# COSTRUZIONE TREND
# =========================================================
def build_trend(df, min_rilevazioni=2):

    if df.empty:
        return {}

    risultati = {}

    for _, r in df.iterrows():

        try:
            partito = normalize_party(r["lista/partito"])

            if not partito:
                continue

            anno = int(r["anno"])

            val = (
                str(r["percentuale"])
                .replace("%", "")
                .replace(",", ".")
                .strip()
            )

            val = float(val)

            risultati.setdefault(partito, {})
            risultati[partito][anno] = (
                risultati[partito].get(anno, 0) + val
            )

        except:
            continue

    # FILTRO SOLO PER CAMERA/SENATO/EUROPEE
    return {
        p: v
        for p, v in risultati.items()
        if len(v) >= min_rilevazioni
    }

# =========================================================
# CARICAMENTO DATI
# =========================================================
DF_CAMERA   = read_file(FILE_CAMERA)
DF_SENATO   = read_file(FILE_SENATO)
DF_EUROPEE  = read_file(FILE_EUROPEE)
DF_COMUNALI = read_file(FILE_COMUNALI)

# Trend nazionali con filtro storico
T_CAM = build_trend(DF_CAMERA, min_rilevazioni=2)
T_SEN = build_trend(DF_SENATO, min_rilevazioni=2)
T_EUR = build_trend(DF_EUROPEE, min_rilevazioni=2)

# Comunali SENZA filtro
T_COM = build_trend(DF_COMUNALI, min_rilevazioni=1)

ALL_P = sorted(
    set(
        list(T_CAM.keys()) +
        list(T_SEN.keys()) +
        list(T_EUR.keys())
    )
)

ALL_COM = sorted(T_COM.keys())

# =========================================================
# DASH APP
# =========================================================
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY],
    meta_tags=[
        {
            "name": "viewport",
            "content": "width=device-width, initial-scale=1"
        }
    ]
)

server = app.server

# =========================================================
# TEMPLATE HTML
# =========================================================
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>Osservatorio Villa Cortese</title>
        {%favicon%}
        {%css%}

        <style>

            body {
                overflow-x: hidden;
            }

            .container-fluid {
                padding-left: 15px;
                padding-right: 15px;
            }

            /* BLOCCA INTERAZIONI GRAFICI */

            .js-plotly-plot,
            .plot-container,
            .svg-container {
                touch-action: none !important;
            }

            .modebar {
                display: none !important;
            }

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

# =========================================================
# LAYOUT
# =========================================================
app.layout = dbc.Container([

    html.H1(
        "📊 Osservatorio Villa Cortese",
        className="text-center my-4 text-primary fw-bold"
    ),

    dbc.Tabs([

        # =================================================
        # TAB COMUNALI (PRIMA SCHEDA)
        # =================================================
        dbc.Tab(
            label="🏛️ Comunali",
            children=[

                html.Div([

                    html.Label(
                        "Seleziona Partito:",
                        className="mt-3 fw-bold"
                    ),

                    dcc.Dropdown(
                        id="sel-p-com",
                        options=[
                            {"label": p, "value": p}
                            for p in ALL_COM
                        ],
                        value=ALL_COM[0] if ALL_COM else None,
                        clearable=False,
                        className="mb-4"
                    ),

                    dbc.Row([
                        dbc.Col(
                            dcc.Graph(
                                id="t-com",
                                config={
                                    "staticPlot": True,
                                    "displayModeBar": False
                                }
                            ),
                            width=12
                        )
                    ])

                ], className="mt-2")

            ]
        ),

        # =================================================
        # TAB TREND STORICO
        # =================================================
        dbc.Tab(
            label="📈 Trend Storico",
            children=[

                html.Div([

                    html.Label(
                        "Seleziona Partito:",
                        className="mt-3 fw-bold"
                    ),

                    dcc.Dropdown(
                        id="sel-p",
                        options=[
                            {"label": p, "value": p}
                            for p in ALL_P
                        ],
                        value=ALL_P[0] if ALL_P else None,
                        clearable=False,
                        className="mb-4"
                    ),

                    dbc.Row([

                        dbc.Col(
                            dcc.Graph(
                                id="t-cam",
                                config={
                                    "staticPlot": True,
                                    "displayModeBar": False
                                }
                            ),
                            width=12,
                            lg=4,
                            className="mb-4"
                        ),

                        dbc.Col(
                            dcc.Graph(
                                id="t-sen",
                                config={
                                    "staticPlot": True,
                                    "displayModeBar": False
                                }
                            ),
                            width=12,
                            lg=4,
                            className="mb-4"
                        ),

                        dbc.Col(
                            dcc.Graph(
                                id="t-eur",
                                config={
                                    "staticPlot": True,
                                    "displayModeBar": False
                                }
                            ),
                            width=12,
                            lg=4,
                            className="mb-4"
                        ),

                    ])

                ], className="mt-2")

            ]
        )

    ])

], fluid=True)

# =========================================================
# CALLBACK COMUNALI
# =========================================================
@app.callback(
    Output("t-com", "figure"),
    Input("sel-p-com", "value")
)
def update_comunali(p):

    if not p or p not in T_COM:

        fig = go.Figure()

        fig.update_layout(
            title=dict(
                text="Dati non disponibili",
                x=0.5
            ),
            template="plotly_white",
            height=450
        )

        return fig

    anni = sorted(T_COM[p].keys())

    valori = [
        round(T_COM[p][a], 2)
        for a in anni
    ]

    fig = go.Figure(
        go.Scatter(
            x=anni,
            y=valori,
            mode="lines+markers+text",
            text=[f"{v}%" for v in valori],
            textposition="top center",
            line=dict(
                width=4,
                color="#e63946"
            ),
            marker=dict(size=10)
        )
    )

    fig.update_layout(

        title=dict(
            text=f"Trend Comunali - {p}",
            x=0.5
        ),

        template="plotly_white",

        height=450,

        hovermode=False,

        dragmode=False,

        margin=dict(
            l=10,
            r=10,
            t=50,
            b=10
        ),

        xaxis=dict(
            tickvals=anni,
            fixedrange=True,
            showgrid=False
        ),

        yaxis=dict(
            range=[0, max(valori) + 15] if valori else [0, 100],
            fixedrange=True
        )

    )

    return fig

# =========================================================
# CALLBACK TREND STORICI
# =========================================================
@app.callback(
    [
        Output("t-cam", "figure"),
        Output("t-sen", "figure"),
        Output("t-eur", "figure")
    ],
    Input("sel-p", "value")
)
def update_trends(p):

    figs = []

    for titolo, dati in [
        ("Camera", T_CAM),
        ("Senato", T_SEN),
        ("Europee", T_EUR)
    ]:

        if not p or p not in dati:

            fig = go.Figure()

            fig.update_layout(
                title=dict(
                    text=f"Trend {titolo} (Dati non disp.)",
                    x=0.5
                ),
                template="plotly_white",
                height=350
            )

        else:

            anni = sorted(dati[p].keys())

            valori = [
                round(dati[p][a], 2)
                for a in anni
            ]

            fig = go.Figure(
                go.Scatter(
                    x=anni,
                    y=valori,
                    mode="lines+markers+text",
                    text=[f"{v}%" for v in valori],
                    textposition="top center",
                    line=dict(
                        width=4,
                        color="#1a5a96"
                    ),
                    marker=dict(size=10)
                )
            )

            fig.update_layout(

                title=dict(
                    text=f"Trend {titolo}",
                    x=0.5
                ),

                template="plotly_white",

                height=350,

                hovermode=False,

                dragmode=False,

                margin=dict(
                    l=10,
                    r=10,
                    t=50,
                    b=10
                ),

                xaxis=dict(
                    tickvals=anni,
                    fixedrange=True,
                    showgrid=False
                ),

                yaxis=dict(
                    range=[0, max(valori) + 15] if valori else [0, 100],
                    fixedrange=True
                )

            )

        figs.append(fig)

    return figs[0], figs[1], figs[2]

# =========================================================
# AVVIO APP
# =========================================================
if __name__ == "__main__":

    port = int(os.environ.get("PORT", 8050))

    app.run(
        debug=False,
        host="0.0.0.0",
        port=port
    )
