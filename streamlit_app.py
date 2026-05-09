import streamlit as st
import streamlit.components.v1 as components
from elaborazione_dashboard_bis import app  # Carica la tua dashboard

# Configurazione pagina Streamlit
st.set_page_config(layout="wide", page_title="Osservatorio Villa Cortese")

# Titolo invisibile per Streamlit
st.write('<style>div.block-container{padding-top:0rem;}</style>', unsafe_allow_html=True)

# Avvia il server Dash internamente e mostralo in Streamlit
components.html(app.index_string, height=1000, scrolling=True)