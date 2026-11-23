"""Presentation names for stable curriculum identifiers."""
from functools import lru_cache
import json
from pathlib import Path
from tuhoc.ui.theme_config import _shared as load_themes

@lru_cache(maxsize=16)
def _read_names(path, stamp):
    try:
        value=json.loads(path.read_text(encoding='utf-8-sig'))
        return value if isinstance(value,dict) else {}
    except (OSError,ValueError):
        return {}


def display_name(data_dir, kind, theme, level=None, lesson=None):
    if kind == 'theme':
        return next((r['title'] for r in load_themes(data_dir) if r['code'] == theme), str(theme))
    path = Path(data_dir) / 'content_library' / 'display_names.json'
    try:
        stat=path.stat()
    except OSError:
        names={}
    else:
        names=_read_names(path,(stat.st_mtime_ns,stat.st_size))
    key = f'{theme}:{level}' if kind == 'level' else f'{theme}:{level}:{lesson}'
    default = f'Level {level}' if kind == 'level' else f'Lesson {lesson}'
    return str(names.get(kind, {}).get(key) or default)

def breadcrumb(data_dir, theme, level, lesson):
    return ' / '.join((display_name(data_dir, 'theme', theme),
                     display_name(data_dir, 'level', theme, level),
                     display_name(data_dir, 'lesson', theme, level, lesson)))
