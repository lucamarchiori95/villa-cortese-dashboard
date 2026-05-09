import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

st.set_page_config(page_title="Osservatorio Villa Cortese", layout="wide")

st.title("📊 Osservatorio Villa Cortese")

# --- FUNZIONE DI CARICAMENTO RIGOROSA ---
def load_and_check(label, keyword):
    # Cerca file che contengono la keyword (es. 'camera')
    files = [f for f in os.listdir('.') if keyword.lower() in f.lower() and (f.endswith('.xlsx') or f.endswith('.csv'))]
    
    if not files:
        st.error(f"❌ File per {label} non trovato su GitHub!")
        return pd.DataFrame()
    
    target_file = files[0]
    st.sidebar.write(f"📁 Caricato per {label}: `{target_file}`") # Debug nel menu laterale
    
    try:
        if target_file.endswith('.csv'):
            df = pd.read_csv(target_file)
        else:
            # Forza la lettura del primo foglio
            df = pd.read_excel(target_file, sheet_name=0)
            
        df.columns = [str(c).strip().lower() for c in df.columns]
        
        # Rinomina la colonna se necessario
        if 'lista' in df.columns and 'lista/partito' not in df.columns:
            df = df.rename(columns={'lista': 'lista/partito'})
            
        return df
    except Exception as e:
        st.error(f"⚠️ Errore nel file {target_file}: {e}")
        return pd.DataFrame()

def normalize_party(n):
    n = str(n).lower().strip()
    if not n or "totale" in n or "n.a." in n: return None
    if "pd" in n or "ulivo" in n: return "PD"
    if "forza italia" in n or "pdl" in n: return "FI / PDL"
    if "lega" in n: return "LEGA"
    if "fdi" in n or "fratelli" in n: return "FDI"
    if "5 stelle" in n or "m5s" in n: return "M5S"
    return n.upper()

def build_trends(df):
    if df.empty: return {}
    res = {}
    # Debug: verifichiamo i partiti trovati nel file
    for _, r in df.iterrows():
        try:
            p_raw = r.get("lista/partito", "")
            p = normalize_party(p_raw)
            if not p: continue
            
            anno = int(r["anno"])
            # Pulizia percentuale
            v_raw = str(r["percentuale"]).replace(",", ".").replace("%", "").strip()
            val = float(v_raw)
            
            res.setdefault(p, {})
            res[p][anno] = res[p].get(anno, 0) + val
        except: continue
    return res

# --- ESECUZIONE ---
st.sidebar.header("Stato File")
df_cam = load_and_check("Camera", "camera")
df_sen = load_and_check("Senato", "senato")
df_eur = load_and_check("Europee", "europee")

t_cam = build_trends(df_cam)
t_sen = build_trends(df_sen)
t_eur = build_trends(df_eur)

all_p = sorted(list(set(list(t_cam.keys()) + list(t_sen.keys()) + list(t_eur.keys()))))

if not all_p:
    st.warning("Nessun dato trovato. Controlla che le colonne degli Excel si chiamino 'anno', 'lista/partito' e 'percentuale'.")
else:
    sel_p = st.selectbox("Seleziona Partito:", all_p)

    col1, col2, col3 = st.columns(3)

    for title, data, col in [("Camera", t_cam, col1), ("Senato", t_sen, col2), ("Europee", t_eur, col3)]:
        with col:
            if sel_p in data and len(data[sel_p]) >= 1:
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
                    title=f"Trend {title}",
                    xaxis=dict(tickvals=anni, fixedrange=True, showgrid=False),
                    yaxis=dict(range=[0, max(valori)+15], fixedrange=True),
                    height=400, template="plotly_white",
                    dragmode=False
                )
                st.plotly_chart(fig, use_container_width=True, config={'staticPlot': True})
            else:
                st.info(f"Dati {title} non disponibili per {sel_p}")
