"""Validated staged JSON writes with rollback on failed multi-file commit."""
import json
import os
import shutil
import tempfile
from pathlib import Path
from datetime import datetime


def commit_json(mapping, backup_dir=None):
    """Stage every file first; restore all prior files if any replacement fails."""
    entries = [(Path(k), v) for k, v in mapping.items()]
    if not entries:
        return None
    staged = {}
    snapshots = {}
    committed = []
    if backup_dir is None:
        backup_dir = entries[0][0].parent / 'backups' / datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backup_dir = Path(backup_dir)
    try:
        for target, data in entries:
            target.parent.mkdir(parents=True, exist_ok=True)
            payload = json.dumps(data, ensure_ascii=False, indent=2)
            fd, temp = tempfile.mkstemp(prefix='.staged_', suffix='.json', dir=target.parent)
            staged[target] = Path(temp)
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
        backup_dir.mkdir(parents=True, exist_ok=True)
        for index, (target, _) in enumerate(entries):
            if target.exists():
                saved = backup_dir / f'{index}_{target.name}'
                shutil.copy2(target, saved)
                snapshots[target] = saved
            else:
                snapshots[target] = None
        for target, _ in entries:
            os.replace(staged[target], target)
            committed.append(target)
    except Exception:
        for target in reversed(committed):
            saved = snapshots.get(target)
            if saved is None:
                target.unlink(missing_ok=True)
            else:
                shutil.copy2(saved, target)
        raise
    finally:
        for temp in staged.values():
            temp.unlink(missing_ok=True)
    return backup_dir
