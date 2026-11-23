"""Optional, safe migration of legacy absolute exam media references.

Usage:
  python exam_media_migrate.py --root .
  python exam_media_migrate.py --root . --apply
"""
import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path

from tuhoc.exams.exam_bank import ExamBank, _atomic


def migrate(root, apply=False):
    bank = ExamBank(root)
    path = bank.questions_path
    if not path.is_file():
        return {'total': 0, 'changed': 0, 'missing': [], 'backup': None, 'applied': False}
    rows = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(rows, list):
        raise ValueError('exam_questions.json must contain a list')
    # Validate all legacy sources before any file copy or JSON modification.
    missing = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('Invalid question row')
        fields = [row.get('image'), row.get('audio')]
        if row.get('type') == 'image_multi_choice':
            fields.extend(row.get('options', []) if isinstance(row.get('options'), list) else [])
            fields.append(row.get('answer'))
        for value in fields:
            if isinstance(value, str) and Path(value).is_absolute() and not Path(value).is_file():
                missing.append({'id': row.get('id'), 'path': value})
    if missing:
        return {'total': len(rows), 'changed': 0, 'missing': missing, 'backup': None, 'applied': False}
    changed = 0
    proposed = []
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f'Invalid question at index {i}')
        new = dict(row)
        keys = ['image', 'audio']
        if row.get('type') == 'image_multi_choice':
            keys.extend(['options', 'answer'])
        for key in keys:
            values = row.get(key)
            if key == 'options':
                if not isinstance(values, list):
                    continue
                converted = []
                for value in values:
                    converted.append(_convert(value, bank, missing, apply, row.get('id'), key))
                new[key] = converted
            elif isinstance(values, str) and values:
                new[key] = _convert(values, bank, missing, apply, row.get('id'), key)
        if new != row:
            changed += 1
        proposed.append(new)
    # Missing files cause a hard stop: never partially migrate an inconsistent bank.
    if missing:
        return {'total': len(rows), 'changed': changed, 'missing': missing, 'backup': None, 'applied': False}
    backup = None
    if apply and changed:
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        backup = path.with_name(f'exam_questions.backup_{stamp}.json')
        shutil.copy2(path, backup)
        try:
            _atomic(path, proposed)
        except Exception:
            shutil.copy2(backup, path)
            raise
    return {'total': len(rows), 'changed': changed, 'missing': missing, 'backup': str(backup) if backup else None, 'applied': bool(apply and changed)}


def _convert(value, bank, missing, apply, question_id, field):
    if not isinstance(value, str) or not value:
        return value
    path = Path(value)
    if not path.is_absolute():
        return value
    if not path.is_file():
        missing.append({'id': question_id, 'field': field, 'path': value})
        return value
    if apply:
        return bank._store_asset(value)
    # Preview never copies files or changes JSON.
    return 'exam_media/<will-copy>'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default='.', help='Project folder containing content_library')
    parser.add_argument('--apply', action='store_true', help='Copy assets and rewrite JSON after backup')
    args = parser.parse_args()
    result = migrate(args.root, args.apply)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result['missing']:
        print('Stopped: missing media paths; original JSON left unchanged.')
        return 2
    if not args.apply:
        print('Dry run only. Add --apply to migrate.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
