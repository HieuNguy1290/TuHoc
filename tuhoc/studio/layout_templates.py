"""Optional starting layouts grouped by the renderer's input controls."""
from tuhoc.studio.layout_registry import controls_for


def template_for(kind):
    """Return fresh desktop pixel overrides for a new draft."""
    controls = controls_for(kind).editable
    elements = {}
    if 'question_text' in controls:
        elements['question_text'] = {'x': 58, 'y': 104, 'width': 844, 'height': 96}
    if 'input_area' in controls:
        elements['input_area'] = {'x': 72, 'y': 352, 'width': 816, 'height': 55}
    elif 'dropdown_area' in controls:
        elements['dropdown_area'] = {'x': 173, 'y': 304, 'width': 346, 'height': 48}
    elif 'word_bank' in controls:
        elements['answer_area'] = {'x': 65, 'y': 265, 'width': 810, 'height': 165}
        elements['word_bank'] = {'x': 65, 'y': 505, 'width': 825, 'height': 35}
    elif 'answer_area' in controls:
        elements['answer_area'] = {'x': 65, 'y': 240, 'width': 810, 'height': 170}
    return {'version': 2, 'desktop': elements}


def read_template(path, kind):
    """Read an explicitly saved per-type template from the current profile."""
    import json
    from tuhoc.studio.question_layout_store import validate_layout

    if path is None or not path.is_file():
        return None
    return validate_layout(json.loads(path.read_text(encoding='utf-8')).get(kind)) or None


def save_template(path, kind, layout):
    import json
    from tuhoc.studio.question_layout_store import validate_layout
    from tuhoc.storage.safe_storage import commit_json

    records = json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}
    records[kind] = validate_layout(layout)
    commit_json({path:records})


def apply_lesson_layout(rows, key, layout):
    """Prepare a bulk update without touching the caller's questions."""
    from tuhoc.studio.question_layout_store import set_layout, validate_layout

    layout = validate_layout(layout)
    def matches(row):
        return (str(row.get('theme','')),str(row.get('level','')),
                str(row.get('lesson') or 1),row.get('type')) == key

    hits = [i for i,row in enumerate(rows) if matches(row)]
    changes = [i for i in hits if rows[i].get('layout') != layout]
    changed = set(changes)
    return [set_layout(row,layout) if i in changed else row for i,row in enumerate(rows)], len(hits), len(changes)
