import os
import glob
import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd

# =========================================================
# DIRECTORY FILE - CORRETTA PER FILE SFUSI
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# =========================================================
# RICERCA AUTOMATICA FILE
# =========================================================

def find_file(keyword):
    # Cerca sia minuscolo che con iniziale maiuscola per compatibilità Linux
    patterns = [
        f"*{keyword}*.xlsx",
        f"*{keyword.capitalize()}*.xlsx",
        f"*{keyword}*.xlsm",
        f"*{keyword.capitalize()}*.xlsm",
        f"*{keyword}*.csv"
    ]
    for pattern in patterns:
        files = glob.glob(os.path.join(BASE_DIR, pattern))
        if files:
            return files[0]
    raise FileNotFoundError(f"Nessun file trovato per: {keyword}")

FILE_CAMERA = find_file("camera")
FILE_SENATO = find_file("senato")
FILE_EUROPEE = find_file("europee")
FILE_COMUNALI = find_file("comunali")

# =========================================================
# LETTURA FILE
# =========================================================

def read_file(path):
    try:
        if path.lower().endswith('.csv'):
            df = pd.read_csv(path)
        else:
            df = pd.read_excel(path)

        df.columns = [str(c).strip().lower() for c in df.columns]

        if 'lista' in df.columns and 'lista/partito' not in df.columns:
            df = df.rename(columns={'lista': 'lista/partito'})

        return df
    except Exception as e:
        print(f"Errore lettura {path}: {e}")
        return pd.DataFrame()

# =========================================================
# NORMALIZZAZIONE STORICA
# =========================================================

def normalize_party(name):
    n = str(name).strip().lower()

    exclude_keywords = ["candidato", "uninominale", "totale", "solo", "voti", "n.d.", "schede"]
    if any(x in n for x in exclude_keywords) or n == "":
        return None

    if any(x in n for x in ["partito democratico", "pd", "ulivo", "margherita", "democratici di sinistra", " ds ", "unione"]):
        return "PD (ex Ulivo/DS/Margherita)"

    if any(x in n for x in ["forza italia", "pdl", "popolo della libertà", "popolo della liberta"]):
        return "FI / PDL"

    if any(x in n for x in ["fratelli d'italia", "fratelli di italia", "fdi", "alleanza nazionale", " an "]):
        return "FDI / AN"

    if "lega" in n:
        return "LEGA"

    if any(x in n for x in ["movimento 5 stelle", "m5s", "5 stelle"]):
        return "M5S"

    if any(x in n for x in ["udc", "unione di centro", "ccd", "cdu", "noi moderati"]):
        return "UDC / CENTRO"

    if any(x in n for x in ["rifondazione", "comunisti italiani", "sinistra italiana", "verdi", "avs"]):
        return "SINISTRA (Rif./Verdi/AVS)"

    return str(name).strip().upper()

# =========================================================
# TREND
# =========================================================

def build_trend(df):
    if df.empty:
        return {}

    col_partito = 'lista/partito' if 'lista/partito' in df.columns else 'partito'

    result = {}

    for _, row in df.iterrows():
        try:
            anno = int(row["anno"])
            if anno < 2001:
                continue

            partito_norm = normalize_party(row[col_partito])
            if not partito_norm:
                continue

            p_val = row["percentuale"]
            perc = float(str(p_val).replace(",", ".").replace("%", "")) if isinstance(p_val, str) else float(p_val)

            result.setdefault(partito_norm, {})
            result[partito_norm][anno] = result[partito_norm].get(anno, 0) + perc

        except:
            continue

    filtered = {}

    for p, values in result.items():
        if len(values) >= 3 and any(val >= 3.0 for val in values.values()):
            filtered[p] = {anno: round(val, 2) for anno, val in sorted(values.items())}

    return filtered

# =========================================================
# COMUNALI
# =========================================================

def build_comunali(df):
    required = ["anno", "lista/partito", "voti", "percentuale"]
    if not all(c in df.columns for c in required):
        return []

    result = []
    anni = sorted([int(a) for a in df["anno"].dropna().unique() if int(a) >= 2001])

    for anno in anni:
        temp = df[df["anno"] == anno].copy()

        temp["voti"] = pd.to_numeric(temp["voti"], errors="coerce").fillna(0)
        temp["percentuale"] = pd.to_numeric(temp["percentuale"], errors="coerce").fillna(0)

        temp = temp.sort_values(by="voti", ascending=False)

        if len(temp) < 2:
            continue

        primo = temp.iloc[0]
        opp = temp.iloc[1:]

        result.append([
            int(anno),
            int(primo["voti"]),
            round(float(primo["percentuale"]), 2),
            int(opp["voti"].sum()),
            round(float(opp["percentuale"].sum()), 2)
        ])

    return result

# =========================================================
# DATA INIT
# =========================================================

df_camera = read_file(FILE_CAMERA)
df_senato = read_file(FILE_SENATO)
df_europee = read_file(FILE_EUROPEE)
df_comunali = read_file(FILE_COMUNALI)

TREND_CAMERA = build_trend(df_camera)
TREND_SENATO = build_trend(df_senato)
TREND_EUROPEE = build_trend(df_europee)
DATA_COM = build_comunali(df_comunali)

ALL_PARTIES = sorted(list(set(
    list(TREND_CAMERA.keys()) +
    list(TREND_SENATO.keys()) +
    list(TREND_EUROPEE.keys())
)))

# =========================================================
# DASH APP
# =========================================================

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
server = app.server  

app.layout = dbc.Container([
    html.H1("📊 Osservatorio Villa Cortese (2001-2024)", className="text-center my-4 text-primary fw-bold"),

    dbc.Tabs([

        dbc.Tab(label="🏘️ Comunali", children=[

            dbc.Row([
                dbc.Col([
                    html.H5("Performance %", className="mt-3 text-secondary"),
                    html.Div(id="tab-com-perc")
                ], md=4),
                dbc.Col(dcc.Graph(id="graf-com-perc"), md=8)
            ]),

            html.Hr(),

            dbc.Row([
                dbc.Col([
                    html.H5("Voti Assoluti", className="mt-3 text-secondary"),
                    html.Div(id="tab-com-voti")
                ], md=4),
                dbc.Col(dcc.Graph(id="graf-com-voti"), md=8)
            ])

        ]),

        dbc.Tab(label="📈 Trend Storico Partiti", children=[

            html.Label("Seleziona Partito:", className="mt-3 fw-bold"),

            dcc.Dropdown(
                id="sel-partito",
                options=[{"label": p, "value": p} for p in ALL_PARTIES],
                value=ALL_PARTIES[0] if ALL_PARTIES else None,
                className="mb-3"
            ),

            dbc.Row([
                dbc.Col(dcc.Graph(id="trend-cam"), md=4),
                dbc.Col(dcc.Graph(id="trend-sen"), md=4),
                dbc.Col(dcc.Graph(id="trend-eur"), md=4)
            ])

        ])
    ])
], fluid=True)

# =========================================================
# CALLBACK COMUNALI
# =========================================================

@app.callback(
    [
        Output("tab-com-perc", "children"),
        Output("tab-com-voti", "children"),
        Output("graf-com-perc", "figure"),
        Output("graf-com-voti", "figure")
    ],
    Input("sel-partito", "value")
)

def update_comunali(_):

    df = pd.DataFrame(DATA_COM, columns=[
        "Anno", "Voti Insieme", "Perc Insieme",
        "Voti Opposizione", "Perc Opposizione"
    ])

    anni = df["Anno"]

    f1 = go.Figure()

    f1.add_trace(go.Scatter(
        x=anni,
        y=df["Perc Insieme"],
        name="Insieme per Villa",
        line=dict(color="#d9534f", width=4),
        mode="lines+markers+text",
        text=df["Perc Insieme"].apply(lambda x: f"{x}%"),
        textposition="top center"
    ))

    f1.add_trace(go.Scatter(
        x=anni,
        y=df["Perc Opposizione"],
        name="Opposizione",
        line=dict(color="#0275d8", width=4),
        mode="lines+markers+text",
        text=df["Perc Opposizione"].apply(lambda x: f"{x}%"),
        textposition="bottom center"
    ))

    f1.update_layout(
        yaxis=dict(range=[0, 105]),
        xaxis=dict(tickvals=anni),
        template="plotly_white",
        height=350,
        margin={"t": 20}
    )

    f2 = go.Figure()

    f2.add_trace(go.Bar(
        x=anni,
        y=df["Voti Insieme"],
        name="Insieme per Villa",
        text=df["Voti Insieme"],
        textposition="outside"
    ))

    f2.add_trace(go.Bar(
        x=anni,
        y=df["Voti Opposizione"],
        name="Opposizione",
        text=df["Voti Opposizione"],
        textposition="outside"
    ))

    f2.update_layout(
        barmode="group",
        xaxis=dict(tickvals=anni),
        template="plotly_white",
        height=350,
        margin={"t": 30}
    )

    return (
        dbc.Table.from_dataframe(df, striped=True, bordered=True),
        dbc.Table.from_dataframe(df, striped=True, bordered=True),
        f1,
        f2
    )

# =========================================================
# TREND CALLBACK
# =========================================================

@app.callback(
    [
        Output("trend-cam", "figure"),
        Output("trend-sen", "figure"),
        Output("trend-eur", "figure")
    ],
    Input("sel-partito", "value")
)

def update_trends(partito):

    figs = []

    datasets = [
        ("Camera", TREND_CAMERA),
        ("Senato", TREND_SENATO),
        ("Europee", TREND_EUROPEE)
    ]

    for titolo, data in datasets:

        if partito not in data:
            fig = go.Figure()
            fig.update_layout(title=f"Trend {titolo}", template="plotly_white", height=400)
            figs.append(fig)
            continue

        anni_p = sorted(data[partito].keys())
        valori = [data[partito][a] for a in anni_p]

        x_pad = 1
        y_min = min(valori)
        y_max = max(valori)
        y_pad = (y_max - y_min) * 0.15 if y_max != y_min else 5

        fig = go.Figure(go.Scatter(
            x=anni_p,
            y=valori,
            mode="lines+markers+text",
            text=[f"{v}%" for v in valori],
            textposition="top center",
            line=dict(width=4, color="#1a5a96"),
            connectgaps=True
        ))

        fig.update_layout(
            title=f"Trend {titolo}",
            xaxis=dict(
                tickvals=anni_p,
                range=[min(anni_p) - x_pad, max(anni_p) + x_pad]
            ),
            yaxis=dict(
                range=[max(0, y_min - y_pad), y_max + y_pad]
            ),
            template="plotly_white",
            height=400,
            margin=dict(l=40, r=20, t=40, b=40)
        )

        figs.append(fig)

    return figs[0], figs[1], figs[2]

# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=8050)