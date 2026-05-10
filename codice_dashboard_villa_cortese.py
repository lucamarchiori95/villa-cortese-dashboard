import os
import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd

# =========================================================
# DIRECTORY FILE
# Render e GitHub: i file devono essere nella stessa
# cartella di questo script.
# =========================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# =========================================================
# RICERCA AUTOMATICA FILE
# =========================================================
def find_file(keyword):
    for ext in [".csv", ".xlsx", ".xlsm", ".xls"]:
        for fname in os.listdir(BASE_DIR):
            if keyword.lower() in fname.lower() and fname.lower().endswith(ext):
                return os.path.join(BASE_DIR, fname)
    raise FileNotFoundError(f"Nessun file trovato per: {keyword}")

FILE_CAMERA   = find_file("camera")
FILE_SENATO   = find_file("senato")
FILE_EUROPEE  = find_file("europee")
FILE_COMUNALI = find_file("comunali")

# =========================================================
# LETTURA FILE
# Supporta sia .xlsx/.xlsm che .csv.
# Rimuove righe duplicate (i CSV originali hanno ogni riga
# ripetuta esattamente due volte per motivi di esportazione).
# =========================================================
def read_file(path):
    try:
        if path.endswith(".csv"):
            df = pd.read_csv(path)
        else:
            df = pd.read_excel(path)
        df.columns = [str(c).strip().lower() for c in df.columns]
        df = df.drop_duplicates()
        return df
    except Exception as e:
        print(f"Errore lettura {path}: {e}")
        return pd.DataFrame()

# =========================================================
# ESTRAZIONE ANNO
# Legge da colonna "anno" se esiste, altrimenti da "data"
# nel formato gg/mm/aaaa tipico dei CSV esportati da Eligendo.
# =========================================================
def extract_year(row):
    if "anno" in row.index:
        try:
            v = row["anno"]
            if pd.notna(v):
                return int(v)
        except:
            pass
    if "data" in row.index:
        try:
            s = str(row["data"]).strip()
            if "/" in s:
                return int(s.split("/")[-1])
            return int(s[:4])
        except:
            pass
    return None

# =========================================================
# NORMALIZZAZIONE PARTITI
# Continuità storica verificata su fonti ufficiali:
#
#   PD (ex Ulivo/DS)
#     <- L'Ulivo (1996-2007), La Margherita, DS,
#        Democratici di Sinistra, Partito Democratico (2007->)
#
#   FI / PDL
#     <- Forza Italia (1994-2009 e 2013->),
#        Il Popolo della Libertà (2009-2013),
#        Casa delle Libertà (coalizione)
#
#   FDI / AN
#     <- Alleanza Nazionale (1994-2009),
#        Fratelli d'Italia (2012->)
#        [AN si è sciolta nel PDL nel 2009; FDI nasce da
#         una corrente che non si riconosce nel PDL]
#
#   LEGA
#     <- Lega Nord (1991-2018), Lega (2018->)
#
#   M5S  <- Movimento 5 Stelle (2009->)
#
#   UDC  <- UDC, CCD, CDU, Unione di Centro
#
#   SINISTRA (Rifondazione/AVS)
#     <- Rifondazione Comunista, Comunisti Italiani,
#        Sinistra Italiana, Alleanza Verdi e Sinistra
#
# NOTA: "azione" (partito fondato nel 2019) NON ha
# continuità con Rifondazione Comunista. Non viene
# aggregato a nessun gruppo storico.
# =========================================================
def normalize_party(name):
    n = str(name).strip().lower()

    exclude_keywords = ["candidato", "uninominale", "totale", "solo", "voti"]
    if any(x in n for x in exclude_keywords):
        return None

    # PD e coalizioni storiche di centrosinistra
    if any(x in n for x in [
        "partito democratico",
        "l'ulivo", "l\u2019ulivo", "uniti nell'ulivo",
        "margherita", "democratici di sinistra",
        "democratici sinistra", "dl.la margherita",
        "italia democratica e progressista", "progressista"
    ]):
        return "PD (ex Ulivo/DS)"
    if n in ["pd"] or n.startswith("pd ") or n.endswith(" pd"):
        return "PD (ex Ulivo/DS)"
    if n in ["ds", "dl", "ulivo"]:
        return "PD (ex Ulivo/DS)"

    # FI / PDL
    if any(x in n for x in [
        "forza italia", "pdl",
        "popolo della libert", "casa delle libert"
    ]):
        return "FI / PDL"
    if n == "fi":
        return "FI / PDL"

    # FDI / AN — Alleanza Nazionale e Fratelli d'Italia
    if any(x in n for x in [
        "fratelli d'italia", "fratelli d\u2019italia",
        "alleanza nazionale"
    ]):
        return "FDI / AN"
    if n in ["fdi", "an"]:
        return "FDI / AN"

    # LEGA — tutte le varianti storiche
    if any(x in n for x in [
        "lega nord", "lega salvini", "lega per salvini"
    ]):
        return "LEGA"
    if n == "lega" or n.startswith("lega ") or n.endswith(" lega"):
        return "LEGA"
    if n.startswith("lega") and (
        "nord" in n or "salvini" in n or "basta euro" in n
    ):
        return "LEGA"

    # M5S
    if any(x in n for x in [
        "movimento 5 stelle", "m5s", "5 stelle", "beppegrillo"
    ]):
        return "M5S"

    # UDC e centro storico
    if any(x in n for x in ["udc", "unione di centro", "ccd", "cdu"]):
        return "UDC"

    # SINISTRA radicale
    # "rifond" cattura sia "rifondazione" che varianti abbreviate.
    # NON include "azione" (partito diverso, fondato nel 2019).
    if any(x in n for x in [
        "rifond", "comunisti italiani",
        "sinistra italiana", "alleanza verdi e sinistra",
        "alleanza verdi sinistra", "avs",
        "sinistra ecologia", "verdi e sinistra"
    ]):
        return "SINISTRA (Rifondazione/AVS)"

    return str(name).strip().upper()

# =========================================================
# COSTRUZIONE TREND
# Filtro: >= 3 tornate elettorali E almeno un valore >= 3%
# Sull'asse X: solo gli anni delle elezioni effettive
# =========================================================
def build_trend(df):
    if df.empty:
        return {}

    result = {}

    for _, row in df.iterrows():
        try:
            anno = extract_year(row)
            if not anno or anno < 2001:
                continue

            partito_norm = normalize_party(row.get("lista/partito", ""))
            if not partito_norm:
                continue

            perc = float(
                str(row.get("percentuale", "")).replace(",", ".")
            )

            result.setdefault(partito_norm, {})
            result[partito_norm][anno] = (
                result[partito_norm].get(anno, 0) + perc
            )
        except:
            continue

    # Filtro: almeno 3 tornate e almeno un picco >= 3%
    filtered = {}
    for p, values in result.items():
        if len(values) >= 3 and any(v >= 3.0 for v in values.values()):
            filtered[p] = {
                anno: round(val, 2)
                for anno, val in sorted(values.items())
            }

    return filtered

# =========================================================
# COSTRUZIONE COMUNALI
# =========================================================
def build_comunali(df):
    if df.empty:
        raise Exception("DataFrame comunali vuoto")

    result = []

    anni_raw = set()
    for _, row in df.iterrows():
        a = extract_year(row)
        if a and a >= 2001:
            anni_raw.add(a)

    for anno in sorted(anni_raw):
        rows_anno = [
            row for _, row in df.iterrows()
            if extract_year(row) == anno
        ]
        if not rows_anno:
            continue

        temp = pd.DataFrame(rows_anno)

        # Escludi righe "Voti candidato Sindaco"
        mask = temp["lista/partito"].str.lower().str.contains(
            "candidato sindaco|voti candidato", na=False
        )
        temp = temp[~mask].copy()

        if temp.empty:
            continue

        temp["voti"] = pd.to_numeric(
            temp["voti"].astype(str).str.replace(",", "."),
            errors="coerce"
        ).fillna(0)
        temp["percentuale"] = pd.to_numeric(
            temp["percentuale"].astype(str).str.replace(",", "."),
            errors="coerce"
        ).fillna(0)

        temp = temp.sort_values(by="voti", ascending=False)

        if len(temp) < 2:
            continue

        primo      = temp.iloc[0]
        opposizione = temp.iloc[1:]

        result.append([
            int(anno),
            int(primo["voti"]),
            round(float(primo["percentuale"]), 2),
            int(opposizione["voti"].sum()),
            round(float(opposizione["percentuale"].sum()), 2)
        ])

    return result

# =========================================================
# CARICAMENTO DATI
# =========================================================
df_camera   = read_file(FILE_CAMERA)
df_senato   = read_file(FILE_SENATO)
df_europee  = read_file(FILE_EUROPEE)
df_comunali = read_file(FILE_COMUNALI)

TREND_CAMERA  = build_trend(df_camera)
TREND_SENATO  = build_trend(df_senato)
TREND_EUROPEE = build_trend(df_europee)
DATA_COM      = build_comunali(df_comunali)

ALL_PARTIES = sorted(list(set(
    list(TREND_CAMERA.keys()) +
    list(TREND_SENATO.keys()) +
    list(TREND_EUROPEE.keys())
)))

# =========================================================
# COLORI PARTITI per scheda Trend
# =========================================================
PARTY_COLORS = {
    "FDI / AN":                    "#1a3a6b",
    "LEGA":                        "#009246",
    "FI / PDL":                    "#2b77c5",
    "PD (ex Ulivo/DS)":            "#e3000f",
    "M5S":                         "#f5c400",
    "SINISTRA (Rifondazione/AVS)": "#c0392b",
    "UDC":                         "#8e44ad",
}

def get_party_color(partito):
    return PARTY_COLORS.get(partito, "#1a5a96")

# =========================================================
# APP DASH
# =========================================================
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY],
    meta_tags=[{
        "name": "viewport",
        "content": "width=device-width, initial-scale=1, maximum-scale=1"
    }]
)
app.title = "Osservatorio Villa Cortese"
server = app.server  # necessario per Render / Gunicorn

# Config grafici statici: blocca zoom e interazione touch
STATIC_CONFIG = {
    "staticPlot": True,
    "displayModeBar": False,
    "scrollZoom": False,
    "doubleClick": False,
    "responsive": True
}

# =========================================================
# LAYOUT — struttura identica all'originale
# Unica aggiunta: xs=12/md=4|8 per responsive mobile
# =========================================================
app.layout = dbc.Container([

    html.H1(
        "📊 Osservatorio Villa Cortese (2001-2024)",
        className="text-center my-4 text-primary fw-bold",
        style={"fontSize": "clamp(1.1rem, 4vw, 1.8rem)"}
    ),

    dbc.Tabs([

        # ── TAB COMUNALI ──────────────────────────────────
        dbc.Tab(label="🏘️ Comunali", children=[
            dbc.Row([
                dbc.Col([
                    html.H5("Performance %", className="mt-3 text-secondary"),
                    html.Div(id="tab-com-perc")
                ], xs=12, md=4),
                dbc.Col(
                    dcc.Graph(id="graf-com-perc", config=STATIC_CONFIG),
                    xs=12, md=8
                )
            ]),
            html.Hr(),
            dbc.Row([
                dbc.Col([
                    html.H5("Voti Assoluti", className="mt-3 text-secondary"),
                    html.Div(id="tab-com-voti")
                ], xs=12, md=4),
                dbc.Col(
                    dcc.Graph(id="graf-com-voti", config=STATIC_CONFIG),
                    xs=12, md=8
                )
            ])
        ]),

        # ── TAB TREND STORICO ─────────────────────────────
        dbc.Tab(label="📈 Trend Storico Partiti", children=[
            html.Label("Seleziona Partito:", className="mt-3 fw-bold"),
            dcc.Dropdown(
                id="sel-partito",
                options=[{"label": p, "value": p} for p in ALL_PARTIES],
                value=ALL_PARTIES[0] if ALL_PARTIES else None,
                className="mb-3",
                clearable=False
            ),
            dbc.Row([
                dbc.Col(
                    dcc.Graph(id="trend-cam", config=STATIC_CONFIG),
                    xs=12, md=4, className="mb-3"
                ),
                dbc.Col(
                    dcc.Graph(id="trend-sen", config=STATIC_CONFIG),
                    xs=12, md=4, className="mb-3"
                ),
                dbc.Col(
                    dcc.Graph(id="trend-eur", config=STATIC_CONFIG),
                    xs=12, md=4, className="mb-3"
                )
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

    df_t1 = df[["Anno", "Perc Insieme", "Perc Opposizione"]].copy()
    df_t1.columns = ["Anno", "Insieme per Villa", "Opposizione"]
    df_t1["Insieme per Villa"] = df_t1["Insieme per Villa"].astype(str) + "%"
    df_t1["Opposizione"]       = df_t1["Opposizione"].astype(str) + "%"

    df_t2 = df[["Anno", "Voti Insieme", "Voti Opposizione"]].copy()
    df_t2.columns = ["Anno", "Insieme per Villa", "Opposizione"]

    anni = df["Anno"].tolist()

    f1 = go.Figure()
    f1.add_trace(go.Scatter(
        x=anni, y=df["Perc Insieme"],
        name="Insieme per Villa",
        line=dict(width=4, color="#d9534f"),
        mode="lines+markers+text",
        text=df["Perc Insieme"].apply(lambda x: f"{x}%"),
        textposition="top center"
    ))
    f1.add_trace(go.Scatter(
        x=anni, y=df["Perc Opposizione"],
        name="Opposizione",
        line=dict(width=4, color="#0275d8"),
        mode="lines+markers+text",
        text=df["Perc Opposizione"].apply(lambda x: f"{x}%"),
        textposition="bottom center"
    ))
    f1.update_layout(
        yaxis=dict(range=[0, 105], fixedrange=True),
        xaxis=dict(tickvals=anni, fixedrange=True),
        template="plotly_white",
        height=350,
        margin={"t": 20},
        dragmode=False,
        hovermode=False
    )

    f2 = go.Figure()
    f2.add_trace(go.Bar(
        x=anni, y=df["Voti Insieme"],
        name="Insieme per Villa",
        marker_color="#d9534f",
        text=df["Voti Insieme"],
        textposition="outside"
    ))
    f2.add_trace(go.Bar(
        x=anni, y=df["Voti Opposizione"],
        name="Opposizione",
        marker_color="#0275d8",
        text=df["Voti Opposizione"],
        textposition="outside"
    ))
    f2.update_layout(
        barmode="group",
        xaxis=dict(tickvals=anni, fixedrange=True),
        yaxis=dict(fixedrange=True),
        template="plotly_white",
        height=350,
        margin={"t": 30},
        dragmode=False,
        hovermode=False
    )

    return (
        dbc.Table.from_dataframe(df_t1, striped=True, bordered=True),
        dbc.Table.from_dataframe(df_t2, striped=True, bordered=True),
        f1,
        f2
    )

# =========================================================
# CALLBACK TREND
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
        ("Camera",  TREND_CAMERA),
        ("Senato",  TREND_SENATO),
        ("Europee", TREND_EUROPEE)
    ]

    for titolo, data in datasets:
        if not data or partito not in data:
            fig = go.Figure()
            fig.update_layout(
                title=f"Trend {titolo}: N/D",
                template="plotly_white",
                height=400,
                dragmode=False
            )
            figs.append(fig)
            continue

        points = data[partito]
        anni_p = sorted(points.keys())
        valori = [points[a] for a in anni_p]
        colore = get_party_color(partito)

        fig = go.Figure(go.Scatter(
            x=anni_p,
            y=valori,
            mode="lines+markers+text",
            text=[f"{v}%" for v in valori],
            textposition="top center",
            line=dict(width=4, color=colore),
            marker=dict(size=9, color=colore),
            connectgaps=True
        ))
        fig.update_layout(
            title=f"Trend {titolo}",
            xaxis=dict(
                tickvals=anni_p,
                ticktext=[str(a) for a in anni_p],
                range=[2000, 2025],
                fixedrange=True,
                showgrid=False
            ),
            yaxis=dict(
                range=[0, max(valori) + 15] if valori else [0, 100],
                fixedrange=True
            ),
            template="plotly_white",
            height=400,
            dragmode=False,
            hovermode=False
        )
        figs.append(fig)

    return figs[0], figs[1], figs[2]

# =========================================================
# AVVIO
# =========================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(debug=False, host="0.0.0.0", port=port)
