import sys
from importlib.metadata import version
from pathlib import Path

import modal


ROOT = Path(__file__).resolve().parents[1]

# Match the package versions used to train the saved model.
packages = [
    "numpy",
    "scipy",
    "pandas",
    "scikit-learn",
    "joblib",
    "fastapi",
    "pydantic",
]

requirements = [
    f"{package}=={version(package)}"
    for package in packages
]

image = (
    modal.Image.debian_slim(
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}"
    )
    .pip_install(*requirements)
    .add_local_dir(
        str(ROOT / "d4"),
        remote_path="/root/d4",
    )
)

app = modal.App("luxury-resale-d4")


@app.function(image=image)
@modal.asgi_app()
def web():
    from d4.api import app as api
    return api
