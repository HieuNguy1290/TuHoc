"""Source paths for diagnostic scripts run from the repository checkout."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def source_file(name, root=ROOT):
    """Resolve a diagnostic's source filename before or after packaging."""
    direct = root / name
    if direct.is_file():
        return direct
    matches = list((root / 'tuhoc').rglob(name)) if (root / 'tuhoc').is_dir() else []
    if len(matches) == 1:
        return matches[0]
    return direct
