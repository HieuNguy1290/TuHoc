"""Build 03C.33: non-GUI integration contract checks for the assembled app.
Run: python check_integration_contracts.py
Read-only on application files. Writes integration_contracts_03c33.json.
"""
from __future__ import annotations
import ast
import importlib.util
import json
from pathlib import Path
import sys

from tools.checks.paths import ROOT, report_path, source_file

REQUIRED = ('question_layout_store.py','question_layout_runtime.py','question_layout_editor.py',
            'layout_scroll_extent.py','level_flow.py','new_exercise_runtime.py',
            'pygame_exercises.py','new_exercise_editors.py')
EXTENSIONS = ('image_letter_pick_extension.py','image_sentence_extension.py',
              'multi_fill_blanks_extension.py','multi_select_extension.py',
              'dropdown_extension.py','inline_dropdown_extension.py')


def test_store():
    path = source_file('question_layout_store.py')
    if not path.exists():
        return {'status':'blocked','reason':'missing question_layout_store.py'}
    spec = importlib.util.spec_from_file_location('_layout_store_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original = {'kind':'choice','answer':'A'}
    layout = {'question_text':{'x':0.1,'y':0.2,'width':0.6,'height':0.2},
              'option_0':{'x':0.2,'y':0.5,'width':0.4,'height':0.1}}
    updated = module.set_layout(original,layout)
    assert 'layout' not in original, 'set_layout modified source'
    assert module.get_layout(updated) == layout, 'layout round-trip failed'
    updated['layout']['option_0']['x'] = 0.3
    assert layout['option_0']['x'] == 0.2, 'layout aliases caller data'
    assert module.get_layout(original) == {}, 'legacy question default failed'
    for bad in ({'complete_button':{'x':0.2}}, {'question_counter':{'x':0.1}},
                {'question_text':{'x':1.2}}, {'option_0':{'x':0.8,'width':0.5}}):
        try:
            module.validate_layout(bad)
        except ValueError:
            pass
        else:
            raise AssertionError('invalid layout accepted: %r' % bad)
    reset = module.reset_layout(updated)
    assert module.get_layout(reset) == {}, 'reset_layout failed'
    return {'status':'pass','checks':7}


def main():
    report = {'build':'03C.33','checks':{},'warnings':[],
              'limitations':['No Pygame UI event loop, images, sound or Windows GUI tested',
                             'Source and store contracts do not establish correct hitboxes or grading']}
    for name in REQUIRED + EXTENSIONS:
        path = source_file(name)
        if not path.is_file():
            report['checks'][name] = {'status':'missing'}
            report['warnings'].append('Missing module: '+name)
            continue
        try:
            tree = ast.parse(path.read_text(encoding='utf-8-sig'),filename=name)
            functions = [n.name for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
            report['checks'][name] = {'status':'pass','syntax':'ok','top_level_functions':len(functions)}
        except (SyntaxError,UnicodeError,OSError) as exc:
            report['checks'][name] = {'status':'fail','error':str(exc)}
            report['warnings'].append('Cannot parse '+name+': '+str(exc))
    try:
        report['checks']['layout_store_contract'] = test_store()
    except Exception as exc:
        report['checks']['layout_store_contract'] = {'status':'fail','error':repr(exc)}
        report['warnings'].append('Layout store contract failed: '+repr(exc))
    wrapper = source_file('image_letter_pick_extension.py')
    target = source_file('image_sentence_extension.py')
    if wrapper.exists() and target.exists():
        src = wrapper.read_text(encoding='utf-8-sig')
        report['checks']['letter_pick_delegation'] = {'status':'pass' if 'from tuhoc.exercises.image_sentence_extension import run' in src else 'review',
            'target_exists':True}
    else:
        report['checks']['letter_pick_delegation'] = {'status':'blocked','target_exists':target.exists()}
    statuses = [v['status'] for v in report['checks'].values()]
    report['summary'] = {'pass':statuses.count('pass'),'fail':statuses.count('fail'),
                         'missing':statuses.count('missing'),'blocked':statuses.count('blocked'),
                         'review':statuses.count('review')}
    output = report_path('integration_contracts_03c33.json')
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Build 03C.33 integration contract checks:',report['summary'])
    print('Report:',output)
    if report['warnings']:
        print('Warnings:')
        for warning in report['warnings']: print(' -',warning)
    return 1 if report['summary']['fail'] or report['summary']['missing'] else 0

if __name__ == '__main__':
    sys.exit(main())
