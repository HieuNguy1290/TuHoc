"""Build 03C.40: classify integration-check failures without changing the app.

Place beside full_runtime_03c39.json and run:
    python check_integration_failures_03c40.py

This tool reads the previous report and local source inventory. It does not
import application modules, install packages, or modify application files.
"""
from __future__ import annotations
import json
from pathlib import Path

from tools.checks.paths import ROOT, report_path, source_file

SOURCE = ROOT / 'full_runtime_03c39.json'
OUTPUT = report_path('integration_failures_03c40.json')

# Known prerequisites of the optional regression scripts.
REQUIREMENTS = {
    'check_legacy_runtime_regression.py': ('pygame_exercises.py',),
    'check_coordinate_contracts.py': ('pygame_exercises.py', 'question_layout_runtime.py', 'question_layout_store.py', 'layout_scroll_extent.py'),
    'check_editor_drag_zoom_persistence.py': ('question_layout_editor.py', 'question_layout_store.py'),
    'check_editor_reopen_persistence.py': ('question_layout_editor.py', 'question_layout_store.py'),
    'check_integration_contracts.py': ('question_layout_store.py', 'question_layout_runtime.py'),
    'check_layout_json_consistency.py': ('question_layout_store.py', 'question_layout_runtime.py'),
}


def classify(name, entry):
    status = entry.get('status', 'unknown')
    if status == 'not_available':
        return {'classification': 'not_executed', 'reason': 'Regression script not present in this directory'}
    if status == 'pass':
        return {'classification': 'passed', 'reason': 'Check returned exit code 0'}
    if status == 'timeout':
        return {'classification': 'needs_investigation', 'reason': 'Check timed out'}
    missing = [p for p in REQUIREMENTS.get(name, ()) if not (source_file(p)).is_file()]
    if missing:
        return {'classification': 'blocked_missing_prerequisites', 'missing_files': missing,
                'reason': 'Cannot interpret functional failure until these dependencies are available'}
    if status == 'fail':
        return {'classification': 'needs_investigation', 'reason': 'Dependencies present; inspect failed assertions and runtime behavior'}
    return {'classification': 'unknown', 'reason': 'Unrecognized check status'}


def main():
    if not SOURCE.is_file():
        print('ERROR: full_runtime_03c39.json not found next to this script.')
        return 2
    try:
        prior = json.loads(SOURCE.read_text(encoding='utf-8-sig'))
    except (ValueError, OSError) as exc:
        print('ERROR: Cannot read prior report:', exc)
        return 2
    checks = {}
    for name, entry in prior.get('checks', {}).items():
        classification = classify(name, entry)
        checks[name] = {'previous_status': entry.get('status'), **classification}
    inventory = {}
    for section in ('runtime_modules', 'core_modules'):
        for name, record in prior.get(section, {}).items():
            present_here = (Path(__file__).parent / name).is_file()
            inventory[name] = {
                'reported_present_03c39': bool(record.get('present')),
                'present_in_current_folder': present_here,
                'reported_syntax': record.get('syntax'),
            }
    summary = {
        'checks_passed': sum(v['classification'] == 'passed' for v in checks.values()),
        'checks_blocked': sum(v['classification'] == 'blocked_missing_prerequisites' for v in checks.values()),
        'checks_need_investigation': sum(v['classification'] == 'needs_investigation' for v in checks.values()),
        'checks_not_executed': sum(v['classification'] == 'not_executed' for v in checks.values()),
        'modules_missing_here': sum(not v['present_in_current_folder'] for v in inventory.values()),
        'gui_tests_executed': 0,
    }
    result = {
        'build': '03C.40',
        'scope': 'diagnostic classification of existing static integration results',
        'source_report': SOURCE.name,
        'summary': summary,
        'checks': checks,
        'module_inventory': inventory,
        'next_actions': [
            'Assemble latest versions of all required .py files in one application directory.',
            'Rerun Build 03C.39 from that directory.',
            'Investigate any checks that still fail with prerequisites present.',
            'Perform manual GUI tests on Windows for all 26 exercise types.',
        ],
        'warning': 'Missing prerequisites do not establish application defects; passing static checks do not establish GUI correctness.',
    }
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Build 03C.40 - integration failure classification')
    for key, value in summary.items():
        print('  {}: {}'.format(key, value))
    for name, item in checks.items():
        print('  {}: {}'.format(name, item['classification']))
    print('Report:', OUTPUT)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
