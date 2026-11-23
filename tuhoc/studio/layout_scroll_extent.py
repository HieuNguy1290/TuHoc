"""Compute a safe scrollable content extent from optional per-question layout.

This module does not change answer validation or event handling.
"""
from tuhoc.studio.question_layout_store import pixel_elements, pixel_extras


def content_bottom(question, minimum, margin=48):
    """Return the lowest configured element edge in logical Pygame pixels."""
    bottom = max(640, int(minimum))
    layout = question.get('layout') or {}
    if not isinstance(layout, dict):
        return bottom
    geometry = list(pixel_elements(layout).values())
    geometry.extend(extra['rect'] for extra in pixel_extras(layout))
    for rect in geometry:
        if 'y' in rect:
            bottom = max(bottom, rect['y'] + max(1, rect.get('height', 0)) + margin)
    return bottom
