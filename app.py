"""Entry point — redirects to Dashboard.py for Streamlit multipage."""
import streamlit as st
import importlib.util
import os

# This file exists only for backward compatibility.
# The actual dashboard is Dashboard.py (Streamlit entry point).
# Run with: streamlit run Dashboard.py

st.set_page_config(page_title='Strawberry Fresh Supply', page_icon='🍓', layout='wide')
st.markdown('## 🍓 Strawberry Fresh Supply')
st.info('Gunakan **Dashboard.py** sebagai entry point. Jalankan: `streamlit run Dashboard.py`')
st.page_link('Dashboard.py', label='Buka Dashboard', icon='🏠')
