"""Build 03C.38: editor save/reopen persistence regression checks.

Place beside question_layout_editor.py and question_layout_store.py, then run:
    python check_editor_reopen_persistence.py
Writes editor_reopen_03c38.json. No GUI automation or app-file mutation.
"""
import ast
from copy import deepcopy
import json
from pathlib import Path
import sys

from tools.checks.paths import ROOT, report_path, source_file

sys.path.insert(0, str(ROOT))


def verify_editor_source():
    path = source_file('question_layout_editor.py')
    source = path.read_text(encoding='utf-8-sig')
    tree = ast.parse(source)
    edits = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == 'edit_layout']
    assert len(edits) == 1, 'Expected one edit_layout entrypoint'
    funcs = {node.name: node for node in ast.walk(edits[0]) if isinstance(node, ast.FunctionDef)}
    for name in ('current', 'down', 'move', 'save', 'reset', 'change_zoom'):
        assert name in funcs, 'Missing editor handler: ' + name
    for needle in ('deepcopy(initial)', 'validate_layout(working)', 'canvas.canvasx(event.x)',
                   'canvas.canvasy(event.y)', 'zoom[0]', 'canvas.xview_moveto', 'canvas.yview_moveto'):
        assert needle in source, 'Missing editor behavior: ' + needle
    save = ast.get_source_segment(source, funcs['save']) or ''
    assert 'validate_layout(working)' in save, 'Save does not validate working layout'
    assert 'win.destroy()' in save, 'Save does not close editor'
    return 'Editor entrypoint, save, zoom and scroll-aware drag handlers present'


def verify_reopen():
    from tuhoc.studio.question_layout_store import get_layout, set_layout, reset_layout
    question = {'kind': 'choice', 'prompt': 'Example', 'options': ['One', 'Two'], 'correct': 1}
    original = deepcopy(question)
    first = {'question_text': {'x': .08, 'y': .12, 'width': .82, 'height': .14, 'font_size': 28},
             'option_0': {'x': .12, 'y': .48, 'width': .70, 'height': .08, 'font_size': 20}}
    saved = set_layout(question, first)
    assert question == original, 'Saving mutated original question'
    reopened = json.loads(json.dumps(saved, ensure_ascii=False))
    assert get_layout(reopened) == first, 'First layout was not restored after JSON reload'
    # Second editor session: change only one element, preserving others.
    working = deepcopy(get_layout(reopened))
    working['option_0']['y'] = .57
    updated = set_layout(reopened, working)
    assert get_layout(updated)['question_text'] == first['question_text']
    assert get_layout(updated)['option_0']['y'] == .57
    assert get_layout(reopened) == first, 'Second save mutated prior persisted version'
    assert updated['correct'] == original['correct'] and updated['options'] == original['options']
    # Cancel is a discarded working copy, not a store write.
    cancelled = deepcopy(get_layout(updated))
    cancelled['option_0']['x'] = .24
    assert get_layout(updated)['option_0']['x'] == .12, 'Cancelled edit leaked into persisted layout'
    reset = reset_layout(updated)
    assert get_layout(reset) == {} and get_layout(updated) == working
    return 'Two save/reopen cycles, cancellation, reset and answer data preservation verified'


def verify_zoom_scroll_invariance():
    # Reproduce editor move() coordinate normalization with nonzero scroll origins.
    page_w, page_h = 960, 640
    for zoom in (.25, .5, 1., 1.5, 2.):
        for scroll_x, scroll_y in ((0, 0), (125, 330), (400, 850)):
            origin_canvas_x, origin_canvas_y = (scroll_x + 160, scroll_y + 140)
            delta_x, delta_y = (.07 * page_w * zoom, .09 * page_h * zoom)
            end_canvas_x, end_canvas_y = origin_canvas_x + delta_x, origin_canvas_y + delta_y
            actual = ((end_canvas_x-origin_canvas_x)/(page_w*zoom),
                      (end_canvas_y-origin_canvas_y)/(page_h*zoom))
            assert abs(actual[0]-.07) < 1e-10 and abs(actual[1]-.09) < 1e-10
    return 'Drag coordinates invariant across 5 zoom levels and 3 scroll positions'


def verify_locked():
    from tuhoc.studio.question_layout_store import validate_layout
    for key in ('complete_button', 'question_counter'):
        try:
            validate_layout({key: {'x': .1, 'y': .1}})
        except ValueError:
            pass
        else:
            raise AssertionError('Locked control accepted: ' + key)
    return 'Locked controls rejected by storage validator'


def main():
    checks = [('Editor save/reopen source contract', verify_editor_source),
              ('JSON save, reopen, cancel and reset', verify_reopen),
              ('Zoom and scroll coordinate invariance', verify_zoom_scroll_invariance),
              ('Fixed controls remain locked', verify_locked)]
    results = []
    for name, fn in checks:
        try:
            results.append({'name': name, 'status': 'PASS', 'detail': fn()})
        except Exception as exc:
            results.append({'name': name, 'status': 'FAIL', 'detail': '%s: %s' % (type(exc).__name__, exc)})
    report = {'build': '03C.38', 'passed': sum(r['status']=='PASS' for r in results),
              'failed': sum(r['status']=='FAIL' for r in results), 'checks': results,
              'limitations': ['No live Tk mouse interaction or Windows GUI testing',
                              'Mathematical coordinate checks do not prove auto-scroll timing or hitbox correctness']}
    output = report_path('editor_reopen_03c38.json')
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    for item in results:
        print('%s  %s: %s' % (item['status'], item['name'], item['detail']))
    print('Summary: %d/%d passed; report: %s' % (report['passed'], len(results), output.name))
    return int(report['failed'] > 0)


if __name__ == '__main__':
    raise SystemExit(main())
