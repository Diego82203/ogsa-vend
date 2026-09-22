import os
import runpy
from pathlib import Path

from bootstrap_data import ensure_database

os.environ.setdefault("OGSA_DEMO", "0")  # Acceso cerrado por vendedor
os.environ["OGSA_APP_MODE"] = "Vendedor"
ensure_database()
runpy.run_path(str(Path(__file__).with_name("dashboard_core.py")), run_name="__main__")