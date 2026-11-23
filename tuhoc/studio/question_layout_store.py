"""Per-question visual layout storage (stage 1; no rendering changes).

Layout is optional and lives inside each question's existing JSON record.
Coordinates are relative to the original exercise content canvas.
Vertical positions may extend to 4 pages; runtime scrolling is a separate stage.
The completion button and question counter are intentionally not editable.
"""
from copy import deepcopy
from math import isfinite
import re
from tuhoc.studio.layout_render import DESKTOP, SCREENS, PAGE_LIMIT, fit_pixels, to_pixels, to_relative

LAYOUT_KEY = 'layout'
LOCKED = frozenset(('complete_button', 'question_counter'))
EDITABLE = frozenset((
    'question_text', 'question_image', 'audio_player', 'answer_area',
    'answer_text', 'answer_image', 'input_area', 'dropdown_area', 'word_bank',
))
GEOMETRY = frozenset(('x', 'y', 'width', 'height'))
TEXT_FLAGS = frozenset(('bold', 'italic', 'underline'))
TEXT = frozenset(('font_size', 'font_family')) | TEXT_FLAGS
FONT_FAMILIES = ('', 'DejaVu Sans', 'DejaVu Serif', 'Liberation Sans', 'Liberation Serif',
                 'Arial', 'Segoe UI', 'Noto Sans', 'Noto Serif',
                 'Be Vietnam Pro', 'Calibri', 'Tahoma', 'Times New Roman', 'Roboto')
ELEMENT_PREFIXES = ('answer_', 'option_', 'slot_', 'word_')


def _valid_text_setting(field, value):
    if field == 'font_family':
        return isinstance(value, str) and value in FONT_FAMILIES
    return type(value) is bool
IMAGE_FITS = ('contain', 'cover', 'stretch')
_COLOR = re.compile(r'#[0-9a-fA-F]{6}')
_EXTRA_ID = re.compile(r'[a-zA-Z][a-zA-Z0-9_-]{0,63}')



def _validate_runs(value):
    if not isinstance(value, list) or len(value) > 256:
        raise ValueError('Mỗi khung chữ có tối đa 256 vùng định dạng.')
    for run in value:
        if not isinstance(run, dict) or set(run) - {'start', 'end'} - TEXT:
            raise ValueError('Vùng định dạng chữ không hợp lệ.')
        start, end = run.get('start'), run.get('end')
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= 10000:
            raise ValueError('Vị trí vùng định dạng chữ không hợp lệ.')
        for key in run.keys() & TEXT:
            valid = (type(run[key]) is int and 8 <= run[key] <= 96 if key == 'font_size'
                     else _valid_text_setting(key, run[key]))
            if not valid:
                raise ValueError('Kiểu chữ hoặc phông chữ không hợp lệ.')
    return deepcopy(value)

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
                                            element.startswith(ELEMENT_PREFIXES)):
            raise ValueError('Thành phần bố cục không hợp lệ: %s' % element)
        if not isinstance(values, dict):
            raise ValueError('Thông số bố cục phải là một đối tượng.')
        cleaned = {}
        for field, value in values.items():
            if field == 'align':
                if value not in ('left', 'center', 'right'):
                    raise ValueError('Cách căn chữ không hợp lệ.')
                cleaned[field] = value
                continue
            if field == 'line_spacing':
                if type(value) is not int or not 0 <= value <= 80:
                    raise ValueError('Khoảng cách dòng phải nằm trong khoảng 0–80 px.')
                cleaned[field] = value
                continue
            if field == 'runs':
                cleaned[field] = _validate_runs(value)
                continue
            if field == 'image_fit' and element == 'question_image':
                if value not in IMAGE_FITS:
                    raise ValueError('Cách đặt ảnh không hợp lệ.')
                cleaned[field] = value
                continue
            if field in TEXT_FLAGS or field == 'font_family':
                if not _valid_text_setting(field, value):
                    raise ValueError('Kiểu chữ hoặc phông chữ không hợp lệ.')
                cleaned[field] = value
                continue
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


def _validate_extras(extras):
    fields = {'id', 'kind', 'text', 'desktop', 'mobile', 'font_size',
              'bold', 'italic', 'color', 'align', 'bg', 'z'}
    optional = {'mobile', 'font_family', 'underline', 'runs'}
    if not isinstance(extras, list) or len(extras) > 20:
        raise ValueError('Mỗi câu có tối đa 20 hộp văn bản.')
    result = []
    ids = set()
    for extra in extras:
        if not isinstance(extra, dict) or set(extra) - fields - optional or fields - optional - set(extra):
            raise ValueError('Thuộc tính hộp văn bản không hợp lệ.')
        key = extra['id']
        if (not isinstance(key, str) or not _EXTRA_ID.fullmatch(key) or key in ids
                or key in LOCKED | EDITABLE | {'version', 'desktop', 'mobile', 'extras'}
                or key.startswith(ELEMENT_PREFIXES)):
            raise ValueError('Mã hộp văn bản không hợp lệ hoặc bị trùng.')
        ids.add(key)
        if (extra['kind'] != 'text' or not isinstance(extra['text'], str)
                or len(extra['text']) > 500 or type(extra['font_size']) is not int
                or not 8 <= extra['font_size'] <= 96 or type(extra['z']) is not int
                or type(extra['bold']) is not bool or type(extra['italic']) is not bool
                or extra['align'] not in ('left', 'center', 'right')):
            raise ValueError('Nội dung hoặc kiểu chữ của hộp văn bản không hợp lệ.')
        if 'runs' in extra:
            _validate_runs(extra['runs'])
        for field in ('font_family', 'underline'):
            if field in extra and not _valid_text_setting(field, extra[field]):
                raise ValueError('Kiểu chữ hoặc phông chữ không hợp lệ.')
        for name in ('color', 'bg'):
            value = extra[name]
            if not isinstance(value, str) or not (_COLOR.fullmatch(value) or name == 'bg' and value == ''):
                raise ValueError('Màu hộp văn bản phải có dạng #rrggbb.')
        for name, screen in SCREENS.items():
            if name not in extra:
                continue
            box = extra[name]
            if not isinstance(box, dict) or set(box) != GEOMETRY:
                raise ValueError('Hộp văn bản cần đủ X, Y, W và H.')
            _validate_elements({'question_text': box}, screen)
            if min(box['width'], box['height']) < 1:
                raise ValueError('W và H của hộp văn bản phải lớn hơn 0.')
        result.append(deepcopy(extra))
    return result


def validate_layout(layout):
    """Accept legacy relative coordinates and versioned pixel coordinates."""
    if not isinstance(layout, dict) or 'version' not in layout:
        return _validate_elements(layout)
    version = layout['version']
    allowed = {'version', *SCREENS}
    if version in (3, 4):
        allowed.add('extras')
    if type(version) is not int or version not in (2, 3, 4) or set(layout) - allowed:
        raise ValueError('Phiên bản bố cục không hợp lệ.')
    if 'desktop' not in layout:
        raise ValueError('Bố cục cần khung desktop.')
    checked = {'version': version}
    for name, screen in SCREENS.items():
        if name in layout:
            if not isinstance(layout[name], dict):
                raise ValueError('Khung bố cục phải là một đối tượng JSON.')
            checked[name] = _validate_elements(layout[name], screen)
    if version in (3, 4):
        checked['extras'] = _validate_extras(layout.get('extras', []))
    return checked


def pixel_elements(layout, screen=DESKTOP, *, mobile=None):
    """Resolve overrides for the requested screen, using desktop for mobile fallbacks."""
    layout = validate_layout(layout)
    if 'version' not in layout:
        return {key: to_pixels(values, screen) for key, values in layout.items()}
    desktop = layout['desktop']
    if screen == DESKTOP and not mobile:
        return desktop
    elements = {key: to_pixels(to_relative(values, DESKTOP), screen)
                for key, values in desktop.items()}
    if mobile is None:
        mobile = screen[0] < screen[1]
    if mobile:
        for key, values in layout.get('mobile', {}).items():
            elements[key] = {**elements.get(key, {}), **to_pixels(to_relative(values, SCREENS['mobile']), screen)}
    return {key: fit_pixels(values, screen) for key, values in elements.items()}


def layout_v2(layout):
    """Convert relative desktop overrides to pixels using runtime rounding."""
    checked = validate_layout(layout)
    if 'version' in checked:
        return checked
    pixels = {key: fit_pixels(rect, DESKTOP) for key, rect in pixel_elements(checked).items()}
    return validate_layout({'version': 2, 'desktop': pixels})


def layout_v3(layout):
    checked = layout_v2(layout)
    return validate_layout({**checked, 'version': max(3, checked['version']), 'extras': checked.get('extras', [])})


def pixel_extras(layout, screen=DESKTOP, *, mobile=None):
    """Project decorative text without mixing it into system-element lookup."""
    if not isinstance(layout, dict) or layout.get('version') not in (3, 4):
        return []
    result = []
    if mobile is None:
        mobile = screen[0] < screen[1]
    for extra in _validate_extras(layout.get('extras', [])):
        use_mobile = mobile and 'mobile' in extra
        source = 'mobile' if use_mobile else 'desktop'
        rect = extra[source]
        if screen != SCREENS[source]:
            rect = fit_pixels(to_pixels(to_relative(rect, SCREENS[source]), screen), screen)
        result.append({**extra, 'rect': rect})
    return sorted(result, key=lambda extra: extra['z'])


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
