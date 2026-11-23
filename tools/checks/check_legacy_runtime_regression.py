"""Build 03C.31: read-only regression audit of the latest legacy runtime.

Run beside pygame_exercises.py: python check_legacy_runtime_regression.py
Exit 0 = static checks pass; exit 1 = failures; exit 2 = missing source.
Static checks cannot replace GUI testing on Windows.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path

from tools.checks.paths import ROOT, report_path, source_file

KINDS = ('choice', 'picture_choice', 'true_false', 'listening_choice',
         'order', 'matching', 'fill', 'listening_fill', 'error')


def audit(path: Path) -> dict:
    report = {'build': '03C.31', 'file': path.name, 'checks': [], 'warnings': [],
              'manual_qa': [
                  'For each of the 9 kinds, test with and without saved layout.',
                  'Scroll to bottom; ensure fixed submit is visible and clickable.',
                  'Click an answer behind header/footer: it must not be selected.',
                  'For matching, reset/relink pairs and submit only when complete.',
                  'For order, select all tokens in sequence, reset and submit.',
                  'For text inputs, type long text and submit without losing content.',
                  'Verify scoring and audio playback on Windows.',
              ]}
    if not path.is_file():
        report['warnings'].append('Missing pygame_exercises.py beside checker')
        report['passed'] = 0
        report['total'] = 0
        return report
    source = path.read_text(encoding='utf-8-sig')
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        report['checks'].append({'name': 'Python syntax', 'ok': False, 'detail': str(exc)})
        report['passed'], report['total'] = 0, 1
        return report
    run = next((node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == '_run'), None)
    run_src = ast.get_source_segment(source, run) if run else ''
    checks = {
        'Python syntax': True,
        'Legacy runtime _run exists': run is not None,
        'All 9 legacy kinds declared': all(repr(k) in source for k in KINDS),
        'Layout geometry lookup': 'question_layout_runtime' in run_src,
        'Answer area geometry': "'answer_area'" in run_src,
        'Individual option geometry': "'option_%d'" in run_src,
        'Scroll bounds': 'max_content_scroll' in run_src,
        'Wheel scroll': 'MOUSEWHEEL' in run_src,
        'PageUp/PageDown': 'K_PAGEUP' in run_src and 'K_PAGEDOWN' in run_src,
        'Viewport hitbox translated': 'ev.pos[1]+content_scroll' in run_src,
        'Choice fixed submit': 'fixed_choice_submit' in run_src and 'fixed_submit_rect.collidepoint(ev.pos)' in run_src,
        'Text fixed submit': 'fixed_text_submit' in run_src and 'fixed_text_rect.collidepoint(ev.pos)' in run_src,
        'Sequence fixed submit': 'fixed_sequence_submit' in run_src and 'fixed_sequence_rect.collidepoint(ev.pos)' in run_src,
        'Matching completion guard': "kind == 'matching' and len(matching_links) == len(matching_pairs)" in run_src,
        'Order completion guard': "kind == 'order' and len(chosen) == len(options)" in run_src,
        'Header/footer click guard': 'ev.pos[1] < 90 or ev.pos[1] >= 565' in run_src,
        'Matching reset control': "matching_buttons['reset'].collidepoint(ev.pos)" in run_src,
    }
    report['checks'] = [{'name': name, 'ok': bool(ok)} for name, ok in checks.items()]
    report['passed'] = sum(c['ok'] for c in report['checks'])
    report['total'] = len(report['checks'])
    report['warnings'].append('Static checks only; actual mouse/keyboard/audio behavior is unverified.')
    return report


def main() -> int:
    path = source_file('pygame_exercises.py')
    report = audit(path)
    output = report_path('legacy_regression_03c31.json')
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print('Report:', output)
    if not path.exists():
        return 2
    return 0 if report['passed'] == report['total'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
