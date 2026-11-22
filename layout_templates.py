"""Optional starting layouts grouped by the renderer's input controls."""
from layout_registry import controls_for


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
