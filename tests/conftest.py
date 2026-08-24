import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON_SOURCE = PROJECT_ROOT / "src" / "python"

# Make the repository's Python helpers importable without installing a package.
sys.path.insert(0, str(PYTHON_SOURCE))

# Tests exercise the Release binding unless the caller explicitly chooses another build.
os.environ.setdefault("APOGEE_BUILD_CONFIG", "Release")

from add_build_to_path import add_apogee_build_to_path


# Add the compiled extension directory before importing apogee in test modules.
add_apogee_build_to_path()
