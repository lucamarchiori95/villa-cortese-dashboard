import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

st.set_page_config(page_title="Osservatorio Villa Cortese", layout="wide")
st.title("📊 Osservatorio Villa Cortese")

# --- 1. DIAGNOSI FILE ---
st.sidebar.header("Diagnosi Cartella")
files_in_folder = os.listdir('.')
st.sidebar.write("File trovati su GitHub:", files_in_folder)

# --- 2. MAPPATURA FILE (Nomi esatti dallo screenshot) ---
FILE_MAP = {
    "Camera": "villa_cortese_camera.xlsx",
    "Senato": "villa_cortese_senato.xlsx",
    "Europee": "villa_cortese_europee.xlsx"
}

def load_data(file_name):
    if not os.path.exists(file_name):
        st.sidebar.error(f"File NON trovato: {file_name}")
        return pd.DataFrame()
    try:
        df = pd.read_excel(file_name)
        df.columns = [str(c).strip().lower() for c in df.columns]
        if 'lista' in df.columns and 'lista/partito' not in df.columns:
            df = df.rename(columns={'lista': 'lista/partito'})
        return df
    except Exception as e:
        st.sidebar.error(f"Errore lettura {file_name}: {e}")
        return pd.DataFrame()

def normalize_party(n):
    n = str(n).lower().strip()
    if not n or "totale" in n: return None
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
            val = float(str(r["percentuale"]).replace(",", ".").replace("%", ""))
            res.setdefault(p, {})
            res[p][anno] = res[p].get(anno, 0) + val
        except: continue
    return res

# --- 3. ELABORAZIONE ---
t_data = {k: build_trends(load_data(v)) for k, v in FILE_MAP.items()}
all_parties = sorted(list(set().union(*(d.keys() for d in t_data.values()))))

# --- 4. VISUALIZZAZIONE ---
if not all_parties:
    st.warning("⚠️ Nessun dato caricato. Controlla i messaggi di errore nella barra laterale.")
else:
    sel_p = st.selectbox("Seleziona Partito:", all_parties)
    cols = st.columns(3)

    for (label, data), col in zip(t_data.items(), cols):
        with col:
            if sel_p in data:
                d = data[sel_p]
                anni = sorted(d.keys())
                valori = [round(d[a], 2) for a in anni]
                fig = go.Figure(go.Scatter(
                    x=anni, y=valori, mode="lines+markers+text",
                    text=[f"{v}%" for v in valori], textposition="top center",
                    line=dict(width=4, color="#1a5a96"), marker=dict(size=10)
                ))
                fig.update_layout(title=f"Trend {label}", height=400, template="plotly_white", dragmode=False)
                st.plotly_chart(fig, use_container_width=True, config={'staticPlot': True})
            else:
                st.info(f"Nessun dato per {label}")
