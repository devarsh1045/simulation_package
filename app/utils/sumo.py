import os
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]  # your_project/

def project_path(filename: str) -> str:
    return str(BASE_DIR / filename)

def sumo_binary(gui: bool = True) -> str:
    exe = "sumo-gui" if gui else "sumo"
    if os.name == "nt":
        exe += ".exe"

    sumo_home = os.environ.get("SUMO_HOME")
    if sumo_home:
        candidate = Path(sumo_home) / "bin" / exe
        if candidate.exists():
            return str(candidate)

    found = shutil.which(exe)
    if found:
        return found

    raise RuntimeError(f"Could not find {exe}. Set SUMO_HOME or add SUMO bin to PATH.")
