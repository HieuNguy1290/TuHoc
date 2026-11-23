"""Build 03C.35: verify saved JSON geometry against runtime pixel coordinates.

Place beside application modules and run: python check_layout_json_consistency.py
Does not change app modules or question files. Creates a JSON report.
"""
from __future__ import annotations
import ast
import json
import math
from pathlib import Path
import sys

from tools.checks.paths import ROOT, report_path, source_file

REPORT = report_path('layout_json_consistency_03c35.json')
REQUIRED = ('question_layout_store.py', 'question_layout_runtime.py',
            'question_layout_editor.py', 'layout_scroll_extent.py')


def check(label, callback, results):
    try:
        detail = callback()
        results.append({'name': label, 'status': 'pass', 'detail': detail})
    except Exception as exc:
        results.append({'name': label, 'status': 'fail', 'error': repr(exc)})


def main():
    results = []
    for filename in REQUIRED:
        def parse(name=filename):
            path = source_file(name)
            ast.parse(path.read_text(encoding='utf-8-sig'), filename=name)
            return 'syntax ok'
        check('module: ' + filename, parse, results)

    # Import only the two lightweight, non-GUI geometry modules.
    if all((source_file(x)).is_file() for x in REQUIRED[:2]):
        sys.path.insert(0, str(ROOT))
        try:
            from tuhoc.studio.question_layout_store import get_layout, set_layout, reset_layout, validate_layout
            from tuhoc.studio.question_layout_runtime import element
        except Exception as exc:
            results.append({'name':'module imports','status':'fail','error':repr(exc)})
        else:
            check('JSON save/load + source immutability', lambda: json_roundtrip(set_layout, get_layout), results)
            check('pixel scaling at 960x640', lambda: pixel_contract(element), results)
            check('pixel scaling at alternate resolution', lambda: alternate_resolution(element), results)
            check('locked controls rejected', lambda: locked_contract(validate_layout), results)
            check('legacy fallback and reset', lambda: fallback_contract(element, reset_layout), results)
            check('invalid numeric geometry rejected', lambda: numeric_contract(validate_layout), results)
            check('scroll extent covers offscreen layout', lambda: extent_contract(element), results)

    summary = {k: sum(x['status'] == k for x in results) for k in ('pass','fail')}
    report = {'build':'03C.35', 'checks':results, 'summary':summary,
              'limitations':['Non-GUI contract tests only; do not prove editor drag/zoom accuracy',
                             'No Windows Pygame click, scroll or grading interaction executed']}
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Build 03C.35:', summary)
    for result in results:
        if result['status'] == 'fail': print('FAIL:', result['name'], result['error'])
    print('Report:', REPORT)
    return 1 if summary['fail'] else 0


def sample():
    return {'kind':'choice','answer':'A','layout':{
        'question_text':{'x':0.125,'y':0.25,'width':0.5,'height':0.125,'font_size':28},
        'option_0':{'x':0.25,'y':1.5,'width':0.5,'height':0.1}}}


def json_roundtrip(set_layout, get_layout):
    source = {'kind':'choice','answer':'A'}
    data = sample()['layout']
    saved = set_layout(source, data)
    assert 'layout' not in source
    encoded = json.dumps(saved, ensure_ascii=False)
    loaded = json.loads(encoded)
    assert get_layout(loaded) == data
    loaded['layout']['option_0']['x'] = 0.3
    assert data['option_0']['x'] == 0.25
    return 'JSON roundtrip and independent copies'


def pixel_contract(element):
    text = element(sample(), 'question_text')
    assert text == {'x':120,'y':160,'width':480,'height':80,'font_size':28}, text
    assert element(sample(), 'option_0')['y'] == 960
    return text


def alternate_resolution(element):
    text = element(sample(), 'question_text', screen_size=(1280, 720))
    assert text['x'] == 160 and text['y'] == 180 and text['width'] == 640 and text['height'] == 90
    return text


def locked_contract(validate_layout):
    for name in ('complete_button', 'question_counter'):
        try: validate_layout({name:{'x':0.1}})
        except ValueError: continue
        raise AssertionError('Locked element accepted: ' + name)
    return 'both controls locked'


def fallback_contract(element, reset_layout):
    assert element({'kind':'choice'}, 'question_text') is None
    assert element(reset_layout(sample()), 'option_0') is None
    return 'legacy and reset return None'


def numeric_contract(validate_layout):
    for value in (float('nan'), float('inf'), -0.01, 1.1, True):
        try: validate_layout({'option_0':{'x':value}})
        except ValueError: continue
        raise AssertionError('Invalid coordinate accepted: %r' % value)
    return 'NaN, infinity, negative, overflow and boolean rejected'


def extent_contract(element):
    from tuhoc.studio.layout_scroll_extent import content_bottom
    question = sample()
    bottom = content_bottom(question, 640)
    expected = element(question,'option_0')['y'] + element(question,'option_0')['height']
    assert bottom >= expected, (bottom,expected)
    assert content_bottom({'kind':'choice'},640) == 640
    return {'bottom':bottom,'element_bottom':expected}


if __name__ == '__main__':
    sys.exit(main())
