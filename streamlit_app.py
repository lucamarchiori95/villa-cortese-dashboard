import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

# Configurazione Pagina
st.set_page_config(page_title="Osservatorio Villa Cortese", layout="wide")

st.title("📊 Osservatorio Villa Cortese")

# --- FUNZIONI DI CARICAMENTO (Identiche a prima ma adattate) ---
def load_data(file_keyword):
    # Cerca il file nella cartella principale (tutto minuscolo come concordato)
    files = [f for f in os.listdir('.') if file_keyword in f.lower() and (f.endswith('.xlsx') or f.endswith('.csv'))]
    if not files:
        return pd.DataFrame()
    
    path = files[0]
    try:
        df = pd.read_csv(path) if path.endswith('.csv') else pd.read_excel(path)
        df.columns = [str(c).strip().lower() for c in df.columns]
        if 'lista' in df.columns and 'lista/partito' not in df.columns:
            df = df.rename(columns={'lista': 'lista/partito'})
        return df
    except:
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

def get_trends(df):
    if df.empty: return {}
    res = {}
    for _, r in df.iterrows():
        try:
            p = normalize_party(r["lista/partito"])
            if not p: continue
            anno = int(r["anno"])
            val = float(str(r["percentuale"]).replace(",", ".").replace("%", ""))
            res.setdefault(p, {})
            res[p][anno] = res[p].get(anno, 0) + val
        except: continue
    return {p: v for p, v in res.items() if len(v) >= 1}

# Caricamento dati
df_cam = load_data("camera")
df_sen = load_data("senato")
df_eur = load_data("europee")

t_cam = get_trends(df_cam)
t_sen = get_trends(df_sen)
t_eur = get_trends(df_eur)

all_parties = sorted(list(set(list(t_cam.keys()) + list(t_sen.keys()) + list(t_eur.keys()))))

# --- INTERFACCIA STREAMLIT ---
sel_p = st.selectbox("Seleziona Partito:", all_parties)

col1, col2, col3 = st.columns(3)

for title, data, col in [("Camera", t_cam, col1), ("Senato", t_sen, col2), ("Europee", t_eur, col3)]:
    with col:
        if sel_p in data:
            d = data[sel_p]
            anni = sorted(d.keys())
            valori = [d[a] for a in anni]
            
            fig = go.Figure(go.Scatter(
                x=anni, y=valori, mode="lines+markers+text",
                text=[f"{v}%" for v in valori], textposition="top center",
                line=dict(width=4, color="#1a5a96")
            ))
            fig.update_layout(
                title=f"Trend {title}",
                xaxis=dict(tickvals=anni, fixedrange=True),
                yaxis=dict(range=[0, max(valori)+15], fixedrange=True),
                margin=dict(l=10, r=10, t=50, b=10),
                height=400,
                dragmode=False # Blocca zoom
            )
            # Config={'staticPlot': True} in Streamlit si mette qui:
            st.plotly_chart(fig, use_container_width=True, config={'staticPlot': True})
        else:
            st.info(f"Dati {title} non disponibili per {sel_p}")
