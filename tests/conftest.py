import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON_SOURCE = PROJECT_ROOT / "src" / "python"

sys.path.insert(0, str(PYTHON_SOURCE))
os.environ["APOGEE_BUILD_CONFIG"] = "Release"

from add_build_to_path import add_apogee_build_to_path


add_apogee_build_to_path()
