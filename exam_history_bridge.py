"""Read-only bridge from Exam Mode JSON to the existing learning history UI."""
import datetime
import json
from pathlib import Path

def exam_records(conn, student_id, subject=None):
    try:
        db_rows = conn.execute('PRAGMA database_list').fetchall()
        db_path = next((r[2] for r in db_rows if r[1] == 'main' and r[2]), None)
        if not db_path:
            return []
        file_path = Path(db_path).resolve().parent / 'content_library' / 'exam_results.json'
        if not file_path.is_file():
            return []
        rows = json.loads(file_path.read_text(encoding='utf-8-sig'))
        if not isinstance(rows, list):
            return []
        result = []
        for row in rows:
            if not isinstance(row, dict) or str(row.get('student_id')) != str(student_id):
                continue
            kind = row.get('subject', 'tieng_anh')
            aliases = {'tieng_viet': 'vi', 'tieng_anh': 'en'}
            if subject and aliases.get(kind, kind) != aliases.get(subject, subject):
                continue
            try:
                stamp = datetime.datetime.fromisoformat(str(row['submitted_at'])).timestamp()
                total = int(row['total']); correct = int(row['correct'])
                if total <= 0 or correct < 0 or correct > total:
                    continue
            except (KeyError, ValueError, TypeError, OverflowError):
                continue
            result.append((str(row.get('id','')), kind, str(row.get('lesson','')), str(row.get('level','')), stamp, correct, total))
        return result
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return []


def exam_detail(conn, student_id, exam_id):
    """Return a student's own saved attempt, or None; never expose other students' attempts."""
    try:
        db_rows = conn.execute('PRAGMA database_list').fetchall()
        db_path = next((r[2] for r in db_rows if r[1] == 'main' and r[2]), None)
        if not db_path or not exam_id:
            return None
        file_path = Path(db_path).resolve().parent / 'content_library' / 'exam_results.json'
        if not file_path.is_file():
            return None
        rows = json.loads(file_path.read_text(encoding='utf-8-sig'))
        if not isinstance(rows, list):
            return None
        for row in rows:
            if (isinstance(row, dict) and str(row.get('id')) == str(exam_id)
                    and str(row.get('student_id')) == str(student_id)):
                return row
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        pass
    return None
