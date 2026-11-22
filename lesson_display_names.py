"""Presentation names for stable curriculum identifiers."""
import json
from pathlib import Path
from theme_config import load as load_themes

def display_name(data_dir, kind, theme, level=None, lesson=None):
    if kind == 'theme':
        return next((r['title'] for r in load_themes(data_dir) if r['code'] == theme), str(theme))
    path = Path(data_dir) / 'content_library' / 'display_names.json'
    try:
        names = json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        names = {}
    key = f'{theme}:{level}' if kind == 'level' else f'{theme}:{level}:{lesson}'
    default = f'Level {level}' if kind == 'level' else f'Lesson {lesson}'
    return str(names.get(kind, {}).get(key) or default)

def breadcrumb(data_dir, theme, level, lesson):
    return ' / '.join((display_name(data_dir, 'theme', theme),
                     display_name(data_dir, 'level', theme, level),
                     display_name(data_dir, 'lesson', theme, level, lesson)))
