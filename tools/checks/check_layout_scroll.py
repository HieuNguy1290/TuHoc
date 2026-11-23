"""Non-invasive regression checks for per-question layout and scroll extent.

Run from the application directory: python check_layout_scroll.py
Does not start Pygame, edit questions, or change application files.
"""
from pathlib import Path
from tools.checks.paths import ROOT, source_file
import ast
import importlib


def check_sources():
    files = [
        'question_layout_store.py', 'question_layout_runtime.py',
        'layout_scroll_extent.py', 'question_layout_editor.py',
        'multi_fill_blanks_extension.py', 'multi_select_extension.py',
        'listening_image_choice.py', 'image_sentence_extension.py',
        'image_write_extension.py', 'dropdown_extension.py',
        'inline_dropdown_extension.py', 'underline_extension.py',
    ]
    errors = []
    for name in files:
        path = source_file(name)
        if not path.is_file():
            errors.append(f'MISSING {name}')
            continue
        try:
            ast.parse(path.read_text(encoding='utf-8'), filename=name)
        except (SyntaxError, UnicodeError) as exc:
            errors.append(f'SYNTAX {name}: {exc}')
    return errors


def check_geometry():
    from tuhoc.studio.question_layout_store import validate_layout, set_layout
    from tuhoc.studio.question_layout_runtime import element
    from tuhoc.studio.layout_scroll_extent import content_bottom
    q = {'prompt': 'demo', 'answer': 'yes'}
    assert content_bottom(q, 640) == 640
    assert element(q, 'question_text') is None
    layout = {'question_text': {'x': .1, 'y': 2.0, 'width': .7, 'height': .2, 'font_size': 24},
              'answer_area': {'x': .2, 'y': 3.0, 'width': .6, 'height': .3}}
    updated = set_layout(q, layout)
    assert 'layout' not in q
    assert updated['layout'] == validate_layout(layout)
    assert element(updated, 'question_text')['y'] == 1280
    assert content_bottom(updated, 640) >= 2160
    for forbidden in ('complete_button', 'question_counter'):
        try:
            validate_layout({forbidden: {'x': .1}})
        except ValueError:
            pass
        else:
            raise AssertionError(f'Locked element accepted: {forbidden}')
    assert content_bottom({'layout': {}}, 900) == 900


def main():
    issues = check_sources()
    if issues:
        print('\n'.join(issues))
        raise SystemExit(1)
    check_geometry()
    print('PASS: source syntax, layout geometry, extended scroll extent, locked controls')
    print('NOTE: This does not test Pygame mouse interaction or Windows UI.')


if __name__ == '__main__':
    main()
