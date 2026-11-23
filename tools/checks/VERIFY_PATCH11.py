"""Static and headless checks for Phase 3 integration. Run in the project folder.

Usage: python VERIFY_PATCH11.py
No pygame window is opened and no student data is changed.
"""
import ast
import pathlib
import sys

from tools.checks.paths import ROOT, source_file

errors = []
files = sorted((*ROOT.glob('*.py'), *(ROOT / 'tuhoc').rglob('*.py')))
for file in files:
    try:
        ast.parse(file.read_text(encoding='utf-8-sig'), filename=str(file))
    except (SyntaxError, UnicodeError) as exc:
        errors.append(f'{file.name}: {exc}')

required = ('upgrade_v2.py', 'pygame_exercises.py', 'new_exercise_runtime.py',
            'new_exercise_review.py', 'pygame_review_panel.py', 'main.py',
            'home_ui.py', 'level_flow.py', 'lesson_map_ui.py', 'profile_ui.py')
for name in required:
    if not (source_file(name)).is_file():
        errors.append(f'Missing required file: {name}')

if not errors:
    # No pygame import: validate the data contract that previously caused
    # 4/16 and 7/16 to be rendered as 3/16 and 6/16.
    runtime = (source_file('new_exercise_runtime.py')).read_text(encoding='utf-8-sig')
    quiz = (source_file('upgrade_v2.py')).read_text(encoding='utf-8-sig')
    if "_index=index+1" not in quiz:
        errors.append('Quiz does not send 1-based _index to pygame')
    shared = (source_file('exercise_gfx.py')).read_text(encoding='utf-8-sig')
    if 'draw_question_progress(' not in runtime or "int(question.get('_index') or 0)" not in shared:
        errors.append('Extended exercise counter must use the shared 1-based index')
    if "_index', 1)) - 1" in runtime:
        errors.append('Old off-by-one correction is still present')

print(f'Checked {len(files)} Python files')
if errors:
    print('FAILED:')
    for error in errors:
        print(' -', error)
    sys.exit(1)
print('PASS: syntax, required modules and question-counter contract')
print('NOTE: This is NOT a Windows GUI/SDL runtime test.')
