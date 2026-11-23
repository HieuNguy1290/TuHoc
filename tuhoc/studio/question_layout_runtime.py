"""Resolve optional pixel geometry for the active exercise viewport."""
from tuhoc.studio.layout_render import DESKTOP
from tuhoc.studio.question_layout_store import get_layout, pixel_elements


def element(question, name, screen_size=DESKTOP):
    """Return pixel geometry, or None when the renderer should use its defaults."""
    elements = pixel_elements(get_layout(question), screen_size)
    value = elements.get(name)
    if not value and name in {'input_area', 'dropdown_area'}:
        value = elements.get('answer_area')
    if not value and name == 'answer_area':
        kind = question.get('type')
        if kind in {'fill', 'error', 'listening_fill', 'image_write_answer'}:
            value = elements.get('input_area')
        elif kind in {'dropdown_fill_blank', 'inline_dropdown_fill'}:
            value = elements.get('dropdown_area')
    return value or None


def rectangle(geometry, default):
    """Apply saved coordinates to a default drawable and interactive box."""
    geometry = geometry or {}
    return tuple(geometry.get(field, fallback)
                 for field, fallback in zip(('x', 'y', 'width', 'height'), default))
