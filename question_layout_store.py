"""Per-question visual layout storage (stage 1; no rendering changes).

Layout is optional and lives inside each question's existing JSON record.
Coordinates are relative to the original exercise content canvas.
Vertical positions may extend to 4 pages; runtime scrolling is a separate stage.
The completion button and question counter are intentionally not editable.
"""
from copy import deepcopy
from math import isfinite
from layout_render import DESKTOP, SCREENS, PAGE_LIMIT, fit_pixels, to_pixels, to_relative

LAYOUT_KEY = 'layout'
LOCKED = frozenset(('complete_button', 'question_counter'))
EDITABLE = frozenset((
    'question_text', 'question_image', 'audio_player', 'answer_area',
    'answer_text', 'answer_image', 'input_area', 'dropdown_area', 'word_bank',
))
GEOMETRY = frozenset(('x', 'y', 'width', 'height'))
TEXT = frozenset(('font_size',))


def _validate_elements(layout, screen=None):
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
            width, page_height = screen or (1, 1)
            limit = PAGE_LIMIT * page_height if field in ('y', 'height') else width
            if field in GEOMETRY and (not 0 <= value <= limit or (screen is not None and not isinstance(value, int))):
                raise ValueError('Tọa độ hoặc kích thước vượt giới hạn trang thiết kế.')
            if field == 'font_size' and (not 8 <= value <= 96 or (screen is not None and not isinstance(value, int))):
                raise ValueError('Cỡ chữ phải nằm trong khoảng 8–96.')
            cleaned[field] = value
        width, page_height = screen or (1, 1)
        tolerance = 0 if screen else 1e-6
        if (cleaned.get('x', 0) + cleaned.get('width', 0) > width + tolerance
                or cleaned.get('y', 0) + cleaned.get('height', 0) > PAGE_LIMIT * page_height + tolerance):
            raise ValueError('Thành phần nằm ngoài vùng nội dung.')
        result[element] = cleaned
    return result


def validate_layout(layout):
    """Accept the legacy relative map and the version 2 pixel map."""
    if not isinstance(layout, dict) or 'version' not in layout:
        return _validate_elements(layout)
    if type(layout['version']) is not int or layout['version'] != 2 or set(layout) - {'version', *SCREENS}:
        raise ValueError('Phiên bản bố cục không hợp lệ.')
    if 'desktop' not in layout:
        raise ValueError('Bố cục v2 cần khung desktop.')
    checked = {'version': 2}
    for name, screen in SCREENS.items():
        if name in layout:
            if not isinstance(layout[name], dict):
                raise ValueError('Khung bố cục v2 phải là một đối tượng JSON.')
            checked[name] = _validate_elements(layout[name], screen)
    return checked


def pixel_elements(layout, screen=DESKTOP):
    """Resolve overrides for the requested screen, using desktop for mobile fallbacks."""
    layout = validate_layout(layout)
    if layout.get('version') != 2:
        return {key: to_pixels(values, screen) for key, values in layout.items()}
    desktop = layout['desktop']
    if screen == DESKTOP:
        return desktop
    elements = {key: to_pixels(to_relative(values, DESKTOP), screen)
                for key, values in desktop.items()}
    if screen[0] < screen[1]:
        mobile = SCREENS['mobile']
        for key, values in layout.get('mobile', {}).items():
            elements[key] = {**elements.get(key, {}), **to_pixels(to_relative(values, mobile), screen)}
    return {key: fit_pixels(values, screen) for key, values in elements.items()}


def layout_v2(layout):
    """Convert relative desktop overrides to pixels using runtime rounding."""
    checked = validate_layout(layout)
    if checked.get('version') == 2:
        return checked
    pixels = {key: fit_pixels(rect, DESKTOP) for key, rect in pixel_elements(checked).items()}
    return validate_layout({'version': 2, 'desktop': pixels})


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
