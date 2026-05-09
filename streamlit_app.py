import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

st.set_page_config(page_title="Osservatorio Villa Cortese", layout="wide")

st.title("📊 Osservatorio Villa Cortese")

# --- MAPPATURA ESATTA DEI FILE (Dalla tua lista) ---
FILE_MAP = {
    "Camera": "villa_cortese_camera.xlsx",
    "Senato": "villa_cortese_senato.xlsx",
    "Europee": "villa_cortese_europee.xlsx"
}

def load_data(file_name):
    if not os.path.exists(file_name):
        return pd.DataFrame()
    try:
        # Legge il file Excel forzando il primo foglio
        df = pd.read_excel(file_name, sheet_name=0)
        # Pulisce i nomi delle colonne
        df.columns = [str(c).strip().lower() for c in df.columns]
        # Uniforma il nome della colonna partiti
        if 'lista' in df.columns and 'lista/partito' not in df.columns:
            df = df.rename(columns={'lista': 'lista/partito'})
        return df
    except Exception as e:
        st.sidebar.error(f"Errore nel file {file_name}: {e}")
        return pd.DataFrame()

def normalize_party(n):
    n = str(n).lower().strip()
    if not n or "totale" in n or "n.a." in n: return None
    # Regole di accorpamento
    if "pd" in n or "ulivo" in n: return "PD"
    if "forza italia" in n or "pdl" in n: return "FI / PDL"
    if "lega" in n: return "LEGA"
    if "fdi" in n or "fratelli" in n: return "FDI"
    if "5 stelle" in n or "m5s" in n: return "M5S"
    return n.upper()

def build_trends(df):
    if df.empty: return {}
    res = {}
    for _, r in df.iterrows():
        try:
            p = normalize_party(r.get("lista/partito", ""))
            if not p: continue
            
            anno = int(r["anno"])
            # Gestione della percentuale (rimozione simboli e conversione)
            val_str = str(r["percentuale"]).replace(",", ".").replace("%", "").strip()
            val = float(val_str)
            
            res.setdefault(p, {})
            res[p][anno] = res[p].get(anno, 0) + val
        except: continue
    # Mostra solo partiti con una storia (almeno 1 dato valido)
    return res

# --- ELABORAZIONE ---
t_data = {}
for label, filename in FILE_MAP.items():
    df = load_data(filename)
    t_data[label] = build_trends(df)

# Crea la lista unica di tutti i partiti trovati
all_parties = sorted(list(set().union(*(d.keys() for d in t_data.values()))))

# --- VISUALIZZAZIONE ---
if not all_parties:
    st.error("⚠️ Nessun dato trovato nei file Excel. Verifica che le colonne si chiamino 'anno', 'lista/partito' e 'percentuale'.")
else:
    # Seleziona il partito (il primo della lista per default)
    sel_p = st.selectbox("Seleziona Partito:", all_parties)

    col1, col2, col3 = st.columns(3)
    charts = [("Camera", t_data["Camera"], col1), 
              ("Senato", t_data["Senato"], col2), 
              ("Europee", t_data["Europee"], col3)]

    for title, data, col in charts:
        with col:
            if sel_p in data:
                d = data[sel_p]
                anni = sorted(d.keys())
                valori = [round(d[a], 2) for a in anni]
                
                fig = go.Figure(go.Scatter(
                    x=anni, y=valori, mode="lines+markers+text",
                    text=[f"{v}%" for v in valori], textposition="top center",
                    line=dict(width=4, color="#1a5a96"),
                    marker=dict(size=10)
                ))
                fig.update_layout(
                    title=dict(text=f"Trend {title}", x=0.5),
                    xaxis=dict(tickvals=anni, fixedrange=True, showgrid=False),
                    yaxis=dict(range=[0, max(valori)+15], fixedrange=True),
                    height=400, template="plotly_white", dragmode=False
                )
                st.plotly_chart(fig, use_container_width=True, config={'staticPlot': True})
            else:
                st.info(f"Dati {title} non disponibili per {sel_p}")
