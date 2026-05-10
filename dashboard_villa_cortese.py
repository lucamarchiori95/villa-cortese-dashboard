import os
import glob
import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd

# =========================================================
# DIRECTORY FILE
# =========================================================

BASE_DIR = r"C:\Users\lucam\Desktop\Risultati_Villa_Cortese\Elaborazione da eligendo\XLMS"

# =========================================================
# RICERCA AUTOMATICA FILE
# =========================================================

def find_file(keyword):
    patterns = [
        f"*{keyword}*.xlsx",
        f"*{keyword}*.xlsm",
        f"*{keyword}*.xls"
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
        df = pd.read_excel(path)
        df.columns = [str(c).strip().lower() for c in df.columns]
        return df
    except Exception as e:
        print(f"Errore lettura {path}: {e}")
        return pd.DataFrame()

# =========================================================
# NORMALIZZAZIONE PARTITI (Sana la continuità storica)
# =========================================================

def normalize_party(name):
    n = str(name).strip().lower()

    # Esclusione esplicita di categorie non partitiche
    exclude_keywords = ["candidato", "uninominale", "totale", "solo", "voti"]
    if any(x in n for x in exclude_keywords):
        return None

    # AREA CENTROSINISTRA
    if any(x in n for x in ["partito democratico", "pd", "l'ulivo", "margherita", "democratici di sinistra", " ds "]) or n in ["pd", "ds", "dl", "ulivo"]:
        return "PD (ex Ulivo/DS)"
    
    # AREA FORZA ITALIA
    if any(x in n for x in ["forza italia", "pdl", "popolo della libertà", "popolo della liberta"]) or n == "fi":
        return "FI / PDL"

    # AREA DESTRA
    if any(x in n for x in ["fratelli d'italia", "fratelli di italia", "fdi", "alleanza nazionale", " an "]) or n in ["fdi", "an"]:
        return "FDI / AN"

    # LEGA
    if "lega" in n:
        return "LEGA"

    # M5S
    if any(x in n for x in ["movimento 5 stelle", "m5s", "5 stelle"]):
        return "M5S"

    # CENTRO (UDC)
    if any(x in n for x in ["udc", "unione di centro", "ccd", "cdu"]):
        return "UDC"

    # SINISTRA RADICALE
    if any(x in n for x in ["rifondazione", "comunisti italiani", "sinistra italiana", "alleanza verdi sinistra", "avs"]):
        return "SINISTRA (Rifondazione/AVS)"

    return str(name).strip().upper()

# =========================================================
# COSTRUZIONE TREND (Con filtri 3% e 3 tornate)
# =========================================================

# =========================================================
# COSTRUZIONE TREND (Modificata per evitare somme intra-elezione)
# =========================================================

def build_trend(df):
    if df.empty: return {}
    
    required = ["anno", "lista/partito", "percentuale"]
    for c in required:
        if c not in df.columns: return {}

    result = {}
    
    for _, row in df.iterrows():
        try:
            anno_raw = row["anno"]
            if pd.isna(anno_raw): continue
            anno = int(anno_raw)
            if anno < 2001: continue
            
            nome_originale = str(row["lista/partito"]).strip().lower()
            partito_norm = normalize_party(row["lista/partito"])
            
            if not partito_norm:
                continue
            
            perc_raw = str(row["percentuale"]).replace(",", ".")
            perc = float(perc_raw)
            
            if partito_norm not in result:
                result[partito_norm] = {}
            
            # LOGICA DI SALVAGUARDIA:
            # Se l'anno non c'è, lo aggiungo.
            # Se l'anno esiste già, sovrasrivo SOLO se il nome originale è "partito democratico", "pd" o "forza italia"
            # Questo evita che liste minori (+Europa, Noi Moderati, ecc.) sovrascrivano il partito principale.
            if anno not in result[partito_norm]:
                result[partito_norm][anno] = perc
            else:
                punti_di_forza = ["partito democratico", " pd ", "forza italia", " fi "]
                if any(p in nome_originale for p in punti_di_forza) or nome_originale in ["pd", "fi"]:
                    result[partito_norm][anno] = perc
            
        except:
            continue

    # Filtro finale: 3 tornate e almeno un exploit sopra il 3%
    filtered = {}
    for p, values in result.items():
        if len(values) >= 3:
            if any(val >= 3.0 for val in values.values()):
                filtered[p] = {anno: round(val, 2) for anno, val in sorted(values.items())}

    return filtered

# =========================================================
# COSTRUZIONE COMUNALI (INVARIATA)
# =========================================================

def build_comunali(df):
    required = ["anno", "lista/partito", "voti", "percentuale"]
    for c in required:
        if c not in df.columns: raise Exception(f"Colonna mancante: {c}")

    result = []
    anni = sorted([int(a) for a in df["anno"].dropna().unique() if int(a) >= 2001])

    for anno in anni:
        temp = df[df["anno"] == anno].copy()
        temp["voti"] = pd.to_numeric(temp["voti"], errors="coerce").fillna(0)
        temp["percentuale"] = pd.to_numeric(temp["percentuale"], errors="coerce").fillna(0)
        temp = temp.sort_values(by="voti", ascending=False)

        if len(temp) < 2: continue

        primo = temp.iloc[0]
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
# DATABASE
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
# APP DASH
# =========================================================

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
app.title = "Osservatorio Villa Cortese"

app.layout = dbc.Container([
    html.H1("📊 Osservatorio Villa Cortese (2001-2024)", className="text-center my-4 text-primary fw-bold"),
    dbc.Tabs([
        dbc.Tab(label="🏘️ Comunali", children=[
            dbc.Row([
                dbc.Col([html.H5("Performance %", className="mt-3 text-secondary"),
                         html.Div(id="tab-com-perc")], md=4),
                dbc.Col(dcc.Graph(id="graf-com-perc"), md=8)
            ]),
            html.Hr(),
            dbc.Row([
                dbc.Col([html.H5("Voti Assoluti", className="mt-3 text-secondary"),
                         html.Div(id="tab-com-voti")], md=4),
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
                dbc.Col(dcc.Graph(id="trend-cam", config={"staticPlot": True}), md=4),
                dbc.Col(dcc.Graph(id="trend-sen", config={"staticPlot": True}), md=4),
                dbc.Col(dcc.Graph(id="trend-eur", config={"staticPlot": True}), md=4)
            ])
        ])
    ])
], fluid=True)

# =========================================================
# CALLBACK COMUNALI (INVARIATA)
# =========================================================

@app.callback(
    [Output("tab-com-perc", "children"), Output("tab-com-voti", "children"),
     Output("graf-com-perc", "figure"), Output("graf-com-voti", "figure")],
    Input("sel-partito", "value")
)
def update_comunali(_):
    df = pd.DataFrame(DATA_COM, columns=["Anno", "Voti Insieme", "Perc Insieme", "Voti Opposizione", "Perc Opposizione"])
    df_t1 = df[["Anno", "Perc Insieme", "Perc Opposizione"]].copy()
    df_t1.columns = ["Anno", "Insieme per Villa", "Opposizione"]
    df_t1["Insieme per Villa"] = df_t1["Insieme per Villa"].astype(str) + "%"
    df_t1["Opposizione"] = df_t1["Opposizione"].astype(str) + "%"

    df_t2 = df[["Anno", "Voti Insieme", "Voti Opposizione"]].copy()
    df_t2.columns = ["Anno", "Insieme per Villa", "Opposizione"]

    anni = df["Anno"].tolist()
    f1 = go.Figure()
    f1.add_trace(go.Scatter(x=anni, y=df["Perc Insieme"], name="Insieme per Villa", line=dict(width=4, color="#d9534f"), mode="lines+markers+text", text=df["Perc Insieme"].apply(lambda x: f"{x}%"), textposition="top center"))
    f1.add_trace(go.Scatter(x=anni, y=df["Perc Opposizione"], name="Opposizione", line=dict(width=4, color="#0275d8"), mode="lines+markers+text", text=df["Perc Opposizione"].apply(lambda x: f"{x}%"), textposition="bottom center"))
    f1.update_layout(yaxis=dict(range=[0, 105]), xaxis=dict(tickvals=anni), template="plotly_white", height=350, margin={"t": 20})

    f2 = go.Figure()
    f2.add_trace(go.Bar(x=anni, y=df["Voti Insieme"], name="Insieme per Villa", marker_color="#d9534f", text=df["Voti Insieme"], textposition="outside"))
    f2.add_trace(go.Bar(x=anni, y=df["Voti Opposizione"], name="Opposizione", marker_color="#0275d8", text=df["Voti Opposizione"], textposition="outside"))
    f2.update_layout(barmode="group", xaxis=dict(tickvals=anni), template="plotly_white", height=350, margin={"t": 30})

    return dbc.Table.from_dataframe(df_t1, striped=True, bordered=True), dbc.Table.from_dataframe(df_t2, striped=True, bordered=True), f1, f2

# =========================================================
# CALLBACK TREND
# =========================================================

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
            figs.append(fig)
            continue

        points = data[partito]
        anni_p = sorted(points.keys())
        valori = [points[a] for a in anni_p]

        fig = go.Figure(go.Scatter(
            x=anni_p, y=valori, mode="lines+markers+text",
            text=[f"{v}%" for v in valori], textposition="top center",
            line=dict(width=4, color="#1a5a96"),
            connectgaps=True
        ))

        fig.update_layout(
            title=f"Trend {titolo}",
            xaxis=dict(tickvals=anni_p, range=[2000, 2025]),
            yaxis=dict(range=[0, max(valori) + 15] if valori else [0, 100]),
            template="plotly_white", height=400
        )
        figs.append(fig)

    return figs[0], figs[1], figs[2]

if __name__ == "__main__":
    app.run(debug=True)
