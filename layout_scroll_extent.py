"""Compute a safe scrollable content extent from optional per-question layout.

This module does not change answer validation or event handling.
"""
from question_layout_runtime import element


def content_bottom(question, minimum, margin=48):
    """Return the lowest configured element edge in logical Pygame pixels."""
    bottom = max(640, int(minimum))
    layout = question.get('layout') or {}
    if not isinstance(layout, dict):
        return bottom
    for key in layout:
        if key in ('complete_button', 'question_counter'):
            continue
        geometry = element(question, key)
        if geometry and 'y' in geometry:
            bottom = max(bottom, int(geometry['y']) + max(1, int(geometry.get('height', 0))) + margin)
    return bottom
