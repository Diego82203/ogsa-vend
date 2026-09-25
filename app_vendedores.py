import os
import runpy
from pathlib import Path

import streamlit as st

from bootstrap_data import ensure_database

st.set_page_config(
    page_title="OGSA · Portal Comercial",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="auto",
)

portal = str(st.query_params.get("portal", "vendedores")).strip().lower()
mode = "Gerencial" if portal in {"gerencial", "gerencia", "manager"} else "Vendedor"

os.environ.setdefault("OGSA_DEMO", "0")
os.environ["OGSA_APP_MODE"] = mode
os.environ["OGSA_PAGE_CONFIGURED"] = "1"

ensure_database()
runpy.run_path(str(Path(__file__).with_name("dashboard_core.py")), run_name="__main__")
