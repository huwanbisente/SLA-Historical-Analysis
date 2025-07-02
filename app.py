import streamlit as st

from chat_viz import run_chat_dashboard
from voice_viz import run_voice_dashboard
from voice_sales_viz import run_voice_sales_dashboard

st.set_page_config(page_title="Unified SLA Dashboards", layout="wide")

st.sidebar.title("📊 SLA Dashboards")
dashboard = st.sidebar.radio("Select a dashboard", [
    "💬 Chat SLA Dashboard",
    "📞 Voice SLA (Pod Skills)",
    "📈 Voice SLA (Sales)"
])

if dashboard == "💬 Chat SLA Dashboard":
    run_chat_dashboard()

elif dashboard == "📞 Voice SLA (Pod Skills)":
    run_voice_dashboard()

elif dashboard == "📈 Voice SLA (Sales)":
    run_voice_sales_dashboard()
