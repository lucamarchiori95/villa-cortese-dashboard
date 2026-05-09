import os
import glob
import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd

# =========================================================
# CONFIGURAZIONE FILE (Compatibile Render)
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

    raise FileNotFoundError(f"Manca file: {keyword}")

FILE_CAMERA   = find_file("camera")
FILE_SENATO   = find_file("senato")
FILE_EUROPEE  = find_file("europee")
FILE_COMUNALI = find_file("comunali")

# =========================================================
# LETTURA FILE
# =========================================================
def read_file(path):

    try:

        df = pd.read_csv(path) if path.endswith(".csv") else pd.read_excel(path)

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

    if not n or "totale" in n:
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

    res = {}

    for _, r in df.iterrows():

        try:

            p = normalize_party(r["lista/partito"])

            if not p:
                continue

            anno = int(r["anno"])

            val_str = (
                str(r["percentuale"])
                .replace(",", ".")
                .replace("%", "")
                .strip()
            )

            val = float(val_str)

            res.setdefault(p, {})

            res[p][anno] = res[p].get(anno, 0) + val

        except:
            continue

    return {
        p: v
        for p, v in res.items()
        if len(v) >= min_rilevazioni
    }

# =========================================================
# CARICAMENTO DATI
# =========================================================
T_CAM = build_trend(read_file(FILE_CAMERA), min_rilevazioni=2)
T_SEN = build_trend(read_file(FILE_SENATO), min_rilevazioni=2)
T_EUR = build_trend(read_file(FILE_EUROPEE), min_rilevazioni=2)

# COMUNALI SENZA FILTRO >=2
T_COM = build_trend(read_file(FILE_COMUNALI), min_rilevazioni=1)

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
    meta_tags=[{
        "name": "viewport",
        "content": "width=device-width, initial-scale=1"
    }]
)

server = app.server

# =========================================================
# HTML TEMPLATE
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
                padding: 0 15px;
            }

            /* GRAFICI STATICI */

            .static-graph {
                pointer-events: none !important;
                touch-action: none !important;
                user-select: none !important;
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
                        className="mb-4",
                        clearable=False
                    ),

                    dbc.Row([

                        dbc.Col(
                            dcc.Graph(
                                id="t-com",
                                className="static-graph",
                                config={"staticPlot": True}
                            ),
                            width=12,
                            className="mb-4"
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
                        className="mb-4",
                        clearable=False
                    ),

                    dbc.Row([

                        dbc.Col(
                            dcc.Graph(
                                id="t-cam",
                                className="static-graph",
                                config={"staticPlot": True}
                            ),
                            width=12,
                            lg=4,
                            className="mb-4"
                        ),

                        dbc.Col(
                            dcc.Graph(
                                id="t-sen",
                                className="static-graph",
                                config={"staticPlot": True}
                            ),
                            width=12,
                            lg=4,
                            className="mb-4"
                        ),

                        dbc.Col(
                            dcc.Graph(
                                id="t-eur",
                                className="static-graph",
                                config={"staticPlot": True}
                            ),
                            width=12,
                            lg=4,
                            className="mb-4"
                        )

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

        fig = go.Figure().update_layout(
            title=dict(
                text="Trend Comunali (Dati non disp.)",
                x=0.5
            ),
            template="plotly_white",
            height=450
        )

        return fig

    anni = sorted(T_COM[p].keys())

    valori = [round(T_COM[p][a], 2) for a in anni]

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
            text=f"Trend Comunali",
            x=0.5
        ),

        xaxis=dict(
            tickvals=anni,
            fixedrange=True,
            showgrid=False
        ),

        yaxis=dict(
            range=[0, max(valori) + 15] if valori else [0, 100],
            fixedrange=True
        ),

        template="plotly_white",

        margin=dict(
            l=10,
            r=10,
            t=50,
            b=10
        ),

        height=450,

        hovermode=False
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

    for tit, d in [
        ("Camera", T_CAM),
        ("Senato", T_SEN),
        ("Europee", T_EUR)
    ]:

        if not p or p not in d:

            fig = go.Figure().update_layout(
                title=dict(
                    text=f"Trend {tit} (Dati non disp.)",
                    x=0.5
                ),
                template="plotly_white",
                height=350
            )

        else:

            anni = sorted(d[p].keys())

            valori = [round(d[p][a], 2) for a in anni]

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
                    text=f"Trend {tit}",
                    x=0.5
                ),

                xaxis=dict(
                    tickvals=anni,
                    fixedrange=True,
                    showgrid=False
                ),

                yaxis=dict(
                    range=[0, max(valori) + 15] if valori else [0, 100],
                    fixedrange=True
                ),

                template="plotly_white",

                margin=dict(
                    l=10,
                    r=10,
                    t=50,
                    b=10
                ),

                height=350,

                hovermode=False
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
