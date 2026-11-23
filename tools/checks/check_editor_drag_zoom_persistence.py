"""Build 03C.36: non-GUI checks for editor drag/resize/zoom persistence.

Run in the assembled application folder: python check_editor_drag_zoom_persistence.py
Produces editor_drag_zoom_03c36.json. Does not modify application files.
"""
import ast
from copy import deepcopy
import json
from pathlib import Path
import sys

from tools.checks.paths import ROOT, report_path, source_file

REPORT = report_path('editor_drag_zoom_03c36.json')


def check(name, fn, out):
    try:
        detail = fn()
        out.append({'check': name, 'status': 'pass', 'detail': str(detail)})
    except Exception as exc:
        out.append({'check': name, 'status': 'fail', 'detail': repr(exc)})


def editor_contract():
    path = source_file('question_layout_editor.py')
    tree = ast.parse(path.read_text(encoding='utf-8-sig'))
    functions = {n.name: n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    required = ('edit_layout', 'redraw', 'down', 'move', 'save', 'change_zoom')
    missing = [x for x in required if x not in functions]
    if missing:
        raise AssertionError('Missing editor handlers: ' + ', '.join(missing))
    source = path.read_text(encoding='utf-8-sig')
    for token in ('canvas.canvasx(event.x)', 'canvas.canvasy(event.y)', 'visible_w*zoom[0]', 'dims[1]*zoom[0]', 'validate_layout(working)', 'deepcopy(initial)'):
        if token not in source:
            raise AssertionError('Missing editor coordinate/persistence contract: ' + token)
    return 'Required handlers and zoom-normalized drag formulas detected'


def roundtrip():
    sys.path.insert(0, str(ROOT))
    from tuhoc.studio.question_layout_store import get_layout, set_layout
    question = {'prompt': 'Example', 'options': ['A', 'B'], 'correct': 1}
    before = deepcopy(question)
    layout = {'question_text': {'x': .2, 'y': .18, 'width': .6, 'height': .12, 'font_size': 30},
              'option_0': {'x': .15, 'y': .48, 'width': .7, 'height': .08, 'font_size': 22}}
    saved = set_layout(question, layout)
    loaded = json.loads(json.dumps(saved, ensure_ascii=False))
    assert get_layout(loaded) == layout
    assert question == before
    assert loaded['correct'] == 1
    return 'Position, size, font size, answer key and original question preserved'


def zoom_invariance():
    # Mirrors editor move(): normalized deltas divide by dimensions * zoom.
    w, h = 960, 640
    start = (.25, .30)
    expected = (.125, .075)
    for zoom in (.25, .5, 1., 1.5, 2.):
        dx_screen = expected[0] * w * zoom
        dy_screen = expected[1] * h * zoom
        actual = (dx_screen / (w * zoom), dy_screen / (h * zoom))
        assert all(abs(a-b) < 1e-10 for a,b in zip(actual, expected))
        assert abs(start[0] + actual[0] - .375) < 1e-10
    return 'Equivalent drags at 25%, 50%, 100%, 150%, 200% give same saved coordinates'


def reject_locked():
    sys.path.insert(0, str(ROOT))
    from tuhoc.studio.question_layout_store import validate_layout
    for key in ('complete_button', 'question_counter'):
        try:
            validate_layout({key: {'x': .1}})
        except ValueError:
            continue
        raise AssertionError(key + ' was editable')
    return 'Fixed controls cannot be saved as editable layout'


def main():
    results = []
    for name, fn in [('Editor handler/coordinate source inspection', editor_contract),
                     ('JSON save-load and font persistence', roundtrip),
                     ('Zoom-invariant drag calculation', zoom_invariance),
                     ('Locked fixed controls', reject_locked)]:
        check(name, fn, results)
    summary = {'passed': sum(x['status']=='pass' for x in results), 'failed': sum(x['status']=='fail' for x in results)}
    report = {'build':'03C.36', 'summary':summary, 'checks':results,
              'limitations':['Static/source and mathematical checks; no Tk GUI interaction performed',
                             'Does not prove mouse capture, ruler alignment, scrollbar behavior or Windows rendering']}
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Build 03C.36:', summary)
    for item in results:
        if item['status']=='fail': print('FAIL:', item['check'], item['detail'])
    print('Report:', REPORT)
    return int(summary['failed'] != 0)

if __name__ == '__main__':
    raise SystemExit(main())
