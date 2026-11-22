"""Static and headless checks for Phase 3 integration. Run in the project folder.

Usage: python VERIFY_PATCH11.py
No pygame window is opened and no student data is changed.
"""
import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
errors = []
files = sorted(ROOT.glob('*.py'))
for file in files:
    try:
        ast.parse(file.read_text(encoding='utf-8-sig'), filename=str(file))
    except (SyntaxError, UnicodeError) as exc:
        errors.append(f'{file.name}: {exc}')

required = ('upgrade_v2.py', 'pygame_exercises.py', 'new_exercise_runtime.py',
            'new_exercise_review.py', 'pygame_review_panel.py', 'main.py',
            'home_ui.py', 'level_flow.py', 'lesson_map_ui.py', 'profile_ui.py')
for name in required:
    if not (ROOT / name).is_file():
        errors.append(f'Missing required file: {name}')

if not errors:
    # No pygame import: validate the data contract that previously caused
    # 4/16 and 7/16 to be rendered as 3/16 and 6/16.
    runtime = (ROOT / 'new_exercise_runtime.py').read_text(encoding='utf-8-sig')
    quiz = (ROOT / 'upgrade_v2.py').read_text(encoding='utf-8-sig')
    if "_index=index+1" not in quiz:
        errors.append('Quiz does not send 1-based _index to pygame')
    if "int(question.get('_index') or 1)" not in runtime:
        errors.append('Extended exercise counter is not 1-based')
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
