"""Load TuHoc from the checkout selected for the test run."""
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(os.environ.get("TUHOC_ROOT", ".")).resolve()))
