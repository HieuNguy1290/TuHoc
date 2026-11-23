"""Build 03C.18: non-invasive static audit of exercise layout coverage.

Run from the application directory: python audit_layout_coverage.py
Only reads .py files; does not import pygame or modify application data.
"""
from __future__ import annotations
import argparse
import ast
from collections import Counter
from zipfile import ZipFile
import json
from pathlib import Path
import re

from tools.checks.paths import ROOT, report_path, source_file

MODULES = {
    'new_exercise_runtime.py': ['image_multi_choice', 'picture_missing_letters', 'sentence_gaps', 'passage_gaps', 'conversation_gaps'],
    'image_write_extension.py': ['image_write_answer'],
    'dropdown_extension.py': ['dropdown_fill_blank'],
    'inline_dropdown_extension.py': ['inline_dropdown_fill'],
    'underline_extension.py': ['image_underline_choice', 'sentence_underline_words'],
    'image_sentence_extension.py': ['image_sentence_fill'],
    'multi_select_extension.py': ['image_multi_select', 'text_multi_select', 'audio_multi_select'],
    'multi_fill_blanks_extension.py': ['multi_fill_blanks'],
    'listening_image_choice.py': ['listening_image_choice'],
    'image_letter_pick_extension.py': ['image_letter_pick'],
}
KEYS = ('question_text', 'question_image', 'answer_area', 'complete_button', 'question_counter')

def inspect(path):
    source = path.read_text(encoding='utf-8-sig')
    ast.parse(source, filename=str(path))
    return {
        'syntax': 'ok',
        'layout_lookup': bool(re.search(r'\b(element|layout_of|question_layout_runtime)\b', source)),
        'scroll_page': bool(re.search(r'\bPage\s*\(|\bpage\.events\s*\(', source)),
        'scroll_wheel': 'MOUSEWHEEL' in source or 'page.events' in source,
        'mouse_hitbox': 'collidepoint' in source,
        'fixed_control_mentions': {k: k in source for k in ('complete_button', 'question_counter')},
    }

def runtime_delegate(path):
    """Recognize a thin run() wrapper that imports and invokes another module's run()."""
    tree = ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or node.name != 'run':
            continue
        aliases = {}
        for child in ast.walk(node):
            if isinstance(child, ast.ImportFrom) and child.module:
                for name in child.names:
                    if name.name == 'run':
                        aliases[name.asname or name.name] = child.module
        for child in ast.walk(node):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                if child.func.id in aliases:
                    return aliases[child.func.id] + '.py'
    return None


def inspect_with_delegate(path):
    result = inspect(path)
    delegate_name = runtime_delegate(path)
    if delegate_name:
        delegate = source_file(delegate_name)
        if delegate.is_file() and delegate.resolve() != path.resolve():
            target = inspect(delegate)
            result['delegated_runtime'] = delegate_name
            result['delegate_syntax'] = target['syntax']
            for key in ('layout_lookup', 'scroll_page', 'scroll_wheel', 'mouse_hitbox'):
                result[key] = result[key] or target[key]
            result['fixed_control_mentions'] = {
                key: result['fixed_control_mentions'][key] or target['fixed_control_mentions'][key]
                for key in result['fixed_control_mentions']
            }
        else:
            result['delegate_missing'] = delegate_name
    return result


def _literal_assignment(filename, variable):
    """Read a literal tuple/set assignment without importing application modules."""
    path = source_file(filename)
    if not path.is_file():
        return None
    try:
        tree = ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == variable for t in node.targets):
                try:
                    value = ast.literal_eval(node.value)
                except (ValueError, TypeError, SyntaxError):
                    return None
                return sorted(value) if isinstance(value, (tuple, list, set)) and all(isinstance(x, str) for x in value) else None
    except (SyntaxError, UnicodeError, OSError):
        return None
    return None


def inventory(report):
    """Cross-check declared new types against legacy SUPPORTED set; do not guess the target 26."""
    new_types = _literal_assignment('new_exercise_editors.py', 'NEW_TYPES')
    legacy_path = source_file('pygame_exercises.py')
    legacy_types = ['choice', 'picture_choice', 'true_false', 'listening_choice',
                    'order', 'fill', 'listening_fill', 'error', 'matching']
    if not legacy_path.is_file():
        legacy_types = None
    mapped = set(report['question_types'])
    known = set(new_types or []) | set(legacy_types or [])
    result = {
        'new_types_from_editor': new_types,
        'legacy_types_from_runtime_signals': legacy_types,
        'unique_declared_type_count': len(known) if new_types is not None and legacy_types is not None else None,
        'types_not_in_existing_audit_map': sorted(known - mapped),
        'mapped_types_not_in_inventory': sorted(mapped - known) if new_types is not None and legacy_types is not None else [],
        'target_type_count_user_stated': 26,
        'count_matches_target': len(known) == 26 if new_types is not None and legacy_types is not None else None,
        'verification': 'static inventory only; legacy names inferred from pygame_exercises.py, not confirmed by a single authoritative registry',
    }
    report['type_inventory'] = result
    if new_types is None:
        report['warnings'].append('Unable to read NEW_TYPES from new_exercise_editors.py')
    if legacy_types is None:
        report['warnings'].append('Missing pygame_exercises.py; legacy inventory not checked')
    if result['count_matches_target'] is False:
        report['warnings'].append(f"Inventory count {len(known)} differs from expected 26; reconcile before claiming full coverage")
    return result


def audit_legacy_runtime(report):
    """Inspect legacy shared runner conservatively; never equate signals with working UI."""
    path = source_file('pygame_exercises.py')
    names = ('choice', 'picture_choice', 'true_false', 'listening_choice',
             'listening_fill', 'fill', 'matching', 'order', 'error')
    result = {'module': path.name, 'types': {}, 'warnings': [],
              'verification': 'static inspection; no Pygame interaction executed'}
    if not path.is_file():
        result['status'] = 'missing'
        result['warnings'].append('Legacy runtime pygame_exercises.py is missing')
        report['legacy_runtime_audit'] = result
        report['warnings'].extend(result['warnings'])
        return result
    try:
        source = path.read_text(encoding='utf-8-sig')
        tree = ast.parse(source, filename=str(path))
    except (SyntaxError, UnicodeError, OSError) as exc:
        result['status'] = 'unreadable'
        result['warnings'].append(f'Cannot parse legacy runtime: {exc}')
        report['legacy_runtime_audit'] = result
        report['warnings'].extend(result['warnings'])
        return result
    runner = next((node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == '_run'), None)
    result['runner_found'] = runner is not None
    if runner is None:
        result['warnings'].append('No _run(question) function found in legacy runtime')
    runner_source = ast.get_source_segment(source, runner) if runner is not None else ''
    runner_source = runner_source or ''
    common = {
        'vertical_scroll_state': 'content_scroll' in runner_source,
        'mousewheel_handler': 'MOUSEWHEEL' in runner_source,
        'mouse_coordinate_adjustment': bool(re.search(r'ev\.pos\s*=\s*\(.*content_scroll', runner_source)),
        'scroll_viewport_blit': bool(re.search(r'blit\(screen,.*content_scroll', runner_source)),
        'layout_runtime_lookup': bool(re.search(r'\b(question_layout_runtime|layout_of|element)\b', runner_source)),
        'fixed_complete_button_layout': 'complete_button' in runner_source,
        'fixed_question_counter_layout': 'question_counter' in runner_source,
    }
    result['shared_signals'] = common
    # The nine legacy types are routed through the same function. A name appearing
    # in source is only a routing signal, not proof of behavior or test coverage.
    for name in names:
        result['types'][name] = {
            'name_mentioned_in_runner': bool(re.search(r'[\"\']' + re.escape(name) + r'[\"\']', runner_source)),
            'shared_scroll_signals': all(common[k] for k in ('vertical_scroll_state', 'mousewheel_handler', 'mouse_coordinate_adjustment', 'scroll_viewport_blit')),
            'custom_layout_verified': False,
            'click_and_grading_verified': False,
        }
        if not result['types'][name]['name_mentioned_in_runner']:
            result['warnings'].append(f'Legacy type needs routing review: {name}')
    if not common['layout_runtime_lookup']:
        result['warnings'].append('Legacy _run has no recognized per-question layout lookup; custom placement requires review')
    if not common['fixed_complete_button_layout'] or not common['fixed_question_counter_layout']:
        result['warnings'].append('Legacy _run has no recognized fixed-control layout keys; fixed positioning requires review')
    report['legacy_runtime_audit'] = result
    report['warnings'].extend(result['warnings'])
    return result



def audit_integration(report):
    """Cross-module static integration checks. No imports, writes to app, or GUI claims."""
    required = ('question_layout_store.py', 'question_layout_runtime.py',
                'question_layout_editor.py', 'level_flow.py',
                'new_exercise_editors.py', 'new_exercise_runtime.py',
                'pygame_exercises.py', 'layout_scroll_extent.py')
    checks = {}
    sources = {}
    for filename in required:
        path = source_file(filename)
        entry = {'present': path.is_file(), 'syntax': None, 'signals': {}}
        if path.is_file():
            try:
                src = path.read_text(encoding='utf-8-sig')
                ast.parse(src, filename=str(path))
                entry['syntax'] = 'ok'
                sources[filename] = src
            except (SyntaxError, UnicodeError, OSError) as exc:
                entry['syntax'] = f'error: {exc}'
                report['warnings'].append(f'Integration source unreadable: {filename}: {exc}')
        else:
            report['warnings'].append(f'Integration source missing: {filename}')
        checks[filename] = entry
    store = sources.get('question_layout_store.py', '')
    editor = sources.get('question_layout_editor.py', '')
    flow = sources.get('level_flow.py', '')
    runtime = sources.get('question_layout_runtime.py', '')
    checks['question_layout_store.py']['signals'] = {
        'layout_key': 'layout' in store,
        'serialization_signals': any(x in store for x in ('json', 'deepcopy', 'copy')),
    }
    checks['question_layout_editor.py']['signals'] = {
        'layout_key': 'layout' in editor,
        'answer_area': 'answer_area' in editor,
    }
    checks['level_flow.py']['signals'] = {
        'layout_store_reference': 'question_layout_store' in flow,
        'layout_editor_reference': 'question_layout_editor' in flow,
    }
    checks['question_layout_runtime.py']['signals'] = {
        'layout_key': 'layout' in runtime,
        'geometry_lookup': 'def element(' in runtime,
    }
    known = report.get('type_inventory', {})
    new_types = known.get('new_types_from_editor') or []
    legacy_types = known.get('legacy_types_from_runtime_signals') or []
    by_type = {}
    for kind in sorted(set(new_types) | set(legacy_types)):
        mapping = next((filename for filename, types in MODULES.items() if kind in types), None)
        if kind in legacy_types:
            mapping = 'pygame_exercises.py'
        module_entry = report.get('modules', {}).get(mapping, {}) if kind not in legacy_types else checks.get(mapping, {})
        by_type[kind] = {
            'runtime_module': mapping,
            'module_present': bool((source_file(mapping)).is_file()) if mapping else False,
            'syntax_ok': module_entry.get('syntax') == 'ok',
            'static_layout_signal': bool(module_entry.get('layout_lookup')) if kind not in legacy_types else 'shared runner; not independently proven',
            'ui_verified': False,
            'grading_verified': False,
            'status': 'needs interactive verification',
        }
    report['integration_audit'] = {
        'required_modules': checks,
        'type_matrix': by_type,
        'types_in_matrix': len(by_type),
        'types_missing_runtime_module': [k for k,v in by_type.items() if not v['module_present']],
        'limitations': ['Source-level signals are not runtime tests',
                        'Layout persistence and editor-to-Pygame geometry require interactive testing',
                        'No grading, image, sound, or Windows event loop was executed'],
    }
    return report['integration_audit']

def coverage_matrix(root):
    from tuhoc.studio.layout_registry import REGISTRY
    types = Counter()

    def count(value):
        if isinstance(value, list):
            for row in value:
                count(row)
        elif isinstance(value, dict):
            if value.get('type') in REGISTRY and 'prompt' in value:
                types[value['type']] += 1
            for item in value.values():
                if isinstance(item, (list, dict)):
                    count(item)

    for path in root.glob('content_library/**/*.json'):
        count(json.loads(path.read_text(encoding='utf-8-sig')))
    archive = root / 'content_library.zip'
    if archive.is_file():
        with ZipFile(archive) as bundle:
            for name in ('content_library/exam_questions.json','content_library/exam_reading_groups.json'):
                if name in bundle.namelist():
                    count(json.loads(bundle.read(name).decode('utf-8-sig')))
    result = {}
    for kind, spec in sorted(REGISTRY.items()):
        source = source_file(spec.runtime + '.py', root).read_text(encoding='utf-8')
        result[kind] = {'runtime':spec.runtime,'editable':spec.editable,
                        'runtime_reads_layout':spec.runtime_reads_layout and 'question_layout_runtime' in source,
                        'bundled_questions':types[kind]}
    return result


def write_matrix(matrix,path):
    lines = ['# Ma trận bố cục bài học', '',
             'Các cột mô tả điều khiển được Studio mở và tín hiệu đọc layout trong mã runtime. '
             'Hồi quy tương tác chạy riêng bằng tests/canvas_p0.py.', '',
             '| Dạng | Runtime | Thành phần | Đọc layout | Câu trong gói |',
             '| --- | --- | --- | --- | ---: |']
    for kind, row in matrix.items():
        keys = ', '.join(f'`{key}`' for key in row['editable'])
        reads = 'Có' if row['runtime_reads_layout'] else 'Chưa'
        lines.append(f"| `{kind}` | `{row['runtime']}` | {keys} | {reads} | {row['bundled_questions']} |")
    path.write_text('\n'.join(lines)+'\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=report_path('layout_coverage_audit.json'))
    parser.add_argument('--markdown', type=Path)
    args = parser.parse_args()
    report = {'root': str(ROOT), 'modules': {}, 'question_types': {}, 'warnings': []}
    for filename, kinds in MODULES.items():
        path = source_file(filename)
        if not path.exists():
            report['modules'][filename] = {'status': 'missing'}
            report['warnings'].append(f'Missing module: {filename}')
            for kind in kinds: report['question_types'][kind] = 'not checked (module missing)'
            continue
        try:
            result = inspect_with_delegate(path)
            report['modules'][filename] = result
            for kind in kinds:
                report['question_types'][kind] = 'static signals only; GUI verification required'
            if result.get('delegate_missing'):
                report['warnings'].append(f"Missing delegated runtime: {filename} -> {result['delegate_missing']}")
            if not result['layout_lookup']:
                report['warnings'].append(f'No recognized layout lookup: {filename}')
            if not result['scroll_wheel']:
                report['warnings'].append(f'No recognized wheel handler: {filename}')
        except (SyntaxError, UnicodeError) as exc:
            report['modules'][filename] = {'status': 'error', 'message': str(exc)}
            report['warnings'].append(f'Unable to parse {filename}: {exc}')
    report['audited_type_count'] = len(report['question_types'])
    type_inventory = inventory(report)
    legacy_audit = audit_legacy_runtime(report)
    integration = audit_integration(report)
    report['limitations'] = [
        'This is a static source inspection, not a proof that scrolling or hitboxes work.',
        'The original runtime audit covers 17 mapped types; type_inventory adds a separate provisional inventory.',
        'Run with the latest incremental .py files assembled in one application directory.',
        'Thin run() wrappers are audited through their delegated runtime when available.',
        'Manual Windows/Pygame testing is required for click, scroll, grading, images and audio.',
        'Legacy checks inspect one shared _run function and cannot prove per-type layout or fixed hitboxes.',
    ]
    report['registry_matrix'] = coverage_matrix(ROOT)
    if args.markdown:
        write_matrix(report['registry_matrix'],args.markdown)
    destination = args.output
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Audited {len(report["modules"])} modules / {report["audited_type_count"]} mapped types')
    print(f'Warnings: {len(report["warnings"])}')
    print('Inventory unique types:', type_inventory['unique_declared_type_count'])
    print('Legacy types checked:', len(legacy_audit['types']))
    print('Integration type matrix:', integration['types_in_matrix'])
    print('Missing runtime modules:', len(integration['types_missing_runtime_module']))
    print('Not covered by existing audit map:', ', '.join(type_inventory['types_not_in_existing_audit_map']))
    for warning in report['warnings']: print(' -', warning)
    print('Report:', destination)

if __name__ == '__main__': main()
