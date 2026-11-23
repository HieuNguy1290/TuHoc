"""Build 03C.34: non-invasive coordinate/scroll regression checks.

Run from the application directory: python check_coordinate_contracts.py
No pygame window or question data is modified.
"""
from __future__ import annotations
import ast
import json
from pathlib import Path

from tools.checks.paths import ROOT, report_path, source_file

REPORT = report_path('coordinate_contracts_03c34.json')


def viewport_to_content(pos, scroll):
    return (pos[0], pos[1] + scroll)


def content_to_viewport(pos, scroll):
    return (pos[0], pos[1] - scroll)


def clamp_scroll(value, bottom, viewport_height=640):
    return max(0, min(int(value), max(0, int(bottom) - viewport_height)))


def in_content_rect(viewport_pos, rect, scroll, top=90, footer=565):
    """Only visible question content is eligible for answer hit testing."""
    x, y = viewport_pos
    if not top <= y < footer:
        return False
    cx, cy = viewport_to_content((x, y), scroll)
    rx, ry, rw, rh = rect
    return rx <= cx < rx + rw and ry <= cy < ry + rh


def run():
    results = []

    def check(name, condition, detail=''):
        results.append({'name': name, 'passed': bool(condition), 'detail': detail})

    for scroll in (0, 1, 65, 480, 1250):
        for point in ((0, 0), (120, 150), (959, 639)):
            check('roundtrip_scroll_%s_%s' % (scroll, point),
                  content_to_viewport(viewport_to_content(point, scroll), scroll) == point)
    check('scroll_no_overflow', clamp_scroll(1000, 640) == 0)
    check('scroll_clamps_to_max', clamp_scroll(1000, 1200) == 560)
    check('scroll_clamps_to_zero', clamp_scroll(-10, 1200) == 0)
    check('answer_hit_scrolled', in_content_rect((120, 200), (100, 500, 180, 80), 320))
    check('answer_miss_unscrolled', not in_content_rect((120, 200), (100, 500, 180, 80), 0))
    check('header_blocks_answer', not in_content_rect((120, 50), (100, 370, 180, 80), 320))
    check('footer_blocks_answer', not in_content_rect((120, 590), (100, 890, 180, 80), 320))

    legacy = source_file('pygame_exercises.py')
    if legacy.exists():
        source = legacy.read_text(encoding='utf-8-sig')
        try:
            ast.parse(source, filename=str(legacy))
            check('legacy_python_syntax', True)
        except SyntaxError as exc:
            check('legacy_python_syntax', False, str(exc))
        check('legacy_scroll_conversion_present', 'ev.pos[1]+content_scroll' in source)
        check('legacy_fixed_choice_submit_present', 'fixed_choice_submit' in source)
        check('legacy_fixed_sequence_submit_present', 'fixed_sequence_submit' in source)
        check('legacy_fixed_text_submit_present', 'fixed_text_submit' in source)
        check('legacy_pageup_pagedown_present', 'pygame.K_PAGEUP' in source and 'pygame.K_PAGEDOWN' in source)
    else:
        check('legacy_source_available', False, 'Place this checker beside pygame_exercises.py')

    for name in ('question_layout_runtime.py', 'question_layout_store.py', 'layout_scroll_extent.py'):
        path = source_file(name)
        if not path.exists():
            check('module_available_' + name, False, 'Missing: ' + name)
            continue
        try:
            ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
            check('module_syntax_' + name, True)
        except SyntaxError as exc:
            check('module_syntax_' + name, False, str(exc))

    payload = {'build': '03C.34', 'scope': 'coordinate math and static integration checks',
               'note': 'Passing does not establish Windows GUI behavior or all 26 exercise types.',
               'passed': sum(r['passed'] for r in results), 'total': len(results), 'checks': results}
    REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Build 03C.34: %s/%s checks passed' % (payload['passed'], payload['total']))
    print('Report:', REPORT.name)
    for item in results:
        if not item['passed']:
            print('FAIL:', item['name'], item['detail'])
    return 0 if payload['passed'] == payload['total'] else 1


if __name__ == '__main__':
    raise SystemExit(run())
