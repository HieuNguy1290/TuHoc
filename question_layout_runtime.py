"""Optional display-only geometry for per-question Pygame layouts.

The stage-2 editor stores normalized coordinates in its preview canvas.
Existing exercises retain their exact legacy layout when no override exists.
"""
from question_layout_store import get_layout


def element(question, name, screen_size=(960, 640)):
    """Return optional pixel geometry, or None for legacy rendering.

    Coordinates use the full logical exercise canvas; locked elements are
    rejected by the storage validator and never consumed here.
    """
    values = get_layout(question).get(name)
    if not values:
        return None
    w, h = screen_size
    result = {}
    for field in ('x', 'width'):
        if field in values:
            result[field] = round(values[field] * w)
    for field in ('y', 'height'):
        if field in values:
            result[field] = round(values[field] * h)
    if 'font_size' in values:
        result['font_size'] = int(values['font_size'])
    return result
