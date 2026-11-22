"""Per-question visual layout storage (stage 1; no rendering changes).

Layout is optional and lives inside each question's existing JSON record.
Coordinates are relative to the original exercise content canvas.
Vertical positions may extend to 4 pages; runtime scrolling is a separate stage.
The completion button and question counter are intentionally not editable.
"""
from copy import deepcopy
from math import isfinite

LAYOUT_KEY = 'layout'
LOCKED = frozenset(('complete_button', 'question_counter'))
EDITABLE = frozenset((
    'question_text', 'question_image', 'audio_player', 'answer_area',
    'answer_text', 'answer_image', 'input_area', 'dropdown_area',
))
GEOMETRY = frozenset(('x', 'y', 'width', 'height'))
TEXT = frozenset(('font_size',))


def validate_layout(layout):
    """Return a safe detached layout; reject malformed or locked elements."""
    if layout is None:
        return {}
    if not isinstance(layout, dict):
        raise ValueError('Bố cục câu hỏi phải là một đối tượng JSON.')
    result = {}
    for element, values in layout.items():
        if element in LOCKED:
            raise ValueError('Không thể chỉnh nút Hoàn thành hoặc số câu.')
        if element not in EDITABLE and not (isinstance(element, str) and
                                            (element.startswith('answer_') or element.startswith('option_'))):
            raise ValueError('Thành phần bố cục không hợp lệ: %s' % element)
        if not isinstance(values, dict):
            raise ValueError('Thông số bố cục phải là một đối tượng.')
        cleaned = {}
        for field, value in values.items():
            if field not in GEOMETRY | TEXT:
                raise ValueError('Thông số bố cục không hợp lệ: %s' % field)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
                raise ValueError('Thông số bố cục phải là số hữu hạn.')
            if field in GEOMETRY and not 0 <= value <= (4 if field in ('y', 'height') else 1):
                raise ValueError('Tọa độ hoặc kích thước vượt giới hạn trang thiết kế.')
            if field == 'font_size' and not 8 <= value <= 96:
                raise ValueError('Cỡ chữ phải nằm trong khoảng 8–96.')
            cleaned[field] = value
        if cleaned.get('x', 0) + cleaned.get('width', 0) > 1.000001 or cleaned.get('y', 0) + cleaned.get('height', 0) > 4.000001:
            raise ValueError('Thành phần nằm ngoài vùng nội dung.')
        result[element] = cleaned
    return result


def get_layout(question):
    """Old questions without layout retain their current default rendering."""
    return validate_layout(question.get(LAYOUT_KEY))


def set_layout(question, layout):
    """Copy-on-write: never mutate the source question or its layout."""
    updated = deepcopy(question)
    updated[LAYOUT_KEY] = validate_layout(layout)
    return updated


def reset_layout(question):
    return set_layout(question, {})
