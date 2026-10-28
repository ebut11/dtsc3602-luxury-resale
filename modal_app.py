"""Deploy the Streamlit dashboard on Modal.

One-time:  modal secret create supabase-dtsc3602 SUPABASE_URL=... SUPABASE_KEY=...
Test:      uv run modal serve modal_app.py
Deploy:    uv run modal deploy modal_app.py
"""
import shlex
import subprocess
from pathlib import Path

import modal

DASHBOARD = Path(__file__).parent / "app" / "dashboard.py"
REMOTE = "/root/dashboard.py"

image = (
    modal.Image.debian_slim(python_version="3.13")
    .uv_pip_install("streamlit", "pandas", "plotly", "supabase", "python-dotenv")
    .add_local_file(DASHBOARD, REMOTE)
)

app = modal.App("dtsc3602-luxury-dashboard", image=image)


@app.function(secrets=[modal.Secret.from_name("supabase-dtsc3602")], timeout=3600)
@modal.concurrent(max_inputs=100)
@modal.web_server(8000, startup_timeout=120)
def dashboard():
    cmd = (f"streamlit run {shlex.quote(REMOTE)} --server.port 8000 --server.address 0.0.0.0 "
           "--server.enableCORS=false --server.enableXsrfProtection=false --server.headless true")
    subprocess.Popen(cmd, shell=True)
