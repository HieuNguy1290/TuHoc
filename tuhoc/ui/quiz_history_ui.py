"""Read-only, paginated history UI using existing learning_sessions records."""
from tuhoc.ui.strings_vi import t
from tuhoc.ui.ui_components import EmptyState
from tuhoc.ui.ui_tokens import COLORS as TOKEN_COLORS, font_at
from tuhoc.exercises.question_prompt import display_prompt
import datetime
import csv
import io
import json
import os
from pathlib import Path
from tuhoc.exams.exam_history_bridge import exam_records, exam_detail
from tuhoc.exams.exam_bank import SUBJECTS as EXAM_SUBJECTS
import tkinter as tk
from tkinter import ttk

PAGE_SIZE = 20


def fetch_history(conn, student_id, offset=0, limit=PAGE_SIZE, theme=None):
    """Return (total_count, rows) without changing any learning data."""
    where = 'WHERE student_id=?'
    args = [student_id]
    if theme:
        where += ' AND theme=?'
        args.append(theme)
    count = conn.execute('SELECT COUNT(*) FROM learning_sessions '+where, args).fetchone()[0]
    rows = conn.execute(
        'SELECT id, theme, level, started, seconds, correct, total '
        'FROM learning_sessions '+where+' ORDER BY started DESC, id DESC LIMIT ? OFFSET ?',
        args+[int(limit),int(offset)]).fetchall()
    return count, rows


def _duration(seconds):
    seconds=max(0,int(float(seconds or 0)))
    return f'{seconds//60:02d}:{seconds%60:02d}'


def _date(timestamp):
    try:
        return datetime.datetime.fromtimestamp(float(timestamp)).strftime('%d/%m/%Y %H:%M')
    except (ValueError, TypeError, OverflowError, OSError):
        return 'Không rõ'


def _answer_text(value):
    if value is None or value == '':
        return '(Chưa trả lời)'
    if isinstance(value, dict):
        return '; '.join(f'{k} → {v}' for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return ' | '.join(_answer_text(item) for item in value)
    return str(value)


def _correct_answer(question):
    kind = question.get('type')
    if kind in ('sentence_gaps', 'conversation_gaps', 'passage_gaps'):
        return question.get('gap_answers', [])
    if kind == 'matching':
        return question.get('pairs', [])
    if kind == 'order':
        return question.get('sequence', [])
    if kind == 'error':
        return question.get('corrected', '')
    return question.get('answer', '')


def format_exam_detail(record):
    """Format saved exam snapshot without relying on today's mutable question bank."""
    snapshot = record.get('question_snapshot')
    if not isinstance(snapshot, list):
        return 'Bài kiểm tra cũ chưa lưu nội dung câu hỏi.\nChỉ có thể xem điểm tổng kết của lượt làm này.'
    answers = record.get('answers') if isinstance(record.get('answers'), dict) else {}
    ordered = record.get('ordered_answers') if isinstance(record.get('ordered_answers'), dict) else {}
    graded = record.get('graded_answers') if isinstance(record.get('graded_answers'), dict) else {}
    lines = []
    for index, question in enumerate(snapshot, 1):
        if not isinstance(question, dict):
            continue
        qid = str(question.get('id', ''))
        kind = str(question.get('type', ''))
        status = 'ĐÚNG' if graded.get(qid) is True else 'SAI' if graded.get(qid) is False else 'CHƯA CÓ KẾT QUẢ'
        answer = ordered.get(qid, []) if kind == 'order' else answers.get(qid)
        lines.extend((f'CÂU {index} — {status} ({kind})',
                      str(display_prompt(question)),
                      'Đã trả lời: ' + _answer_text(answer),
                      'Đáp án đúng: ' + _answer_text(_correct_answer(question))))
        if question.get('passage'):
            lines.append('Bài đọc: ' + str(question['passage']))
        for media_key in ('image', 'audio'):
            if question.get(media_key):
                lines.append(f'{media_key}: {question[media_key]}')
        lines.append('')
    return '\n'.join(lines) if lines else 'Không có dữ liệu câu hỏi.'


def resolve_exam_media(value, library_dir):
    """Resolve legacy absolute and managed relative media paths, without writing data."""
    if not isinstance(value, str) or not value.strip():
        return None
    candidate = Path(value.strip())
    if not candidate.is_absolute():
        if library_dir is None:
            return None
        root = Path(library_dir).resolve()
        candidate = (root / candidate).resolve()
        # Do not allow stored relative paths to escape the library directory.
        if candidate != root and root not in candidate.parents:
            return None
    return candidate if candidate.is_file() else None


def _history_library_dir(conn):
    try:
        db_rows = conn.execute('PRAGMA database_list').fetchall()
        db_path = next((r[2] for r in db_rows if r[1] == 'main' and r[2]), None)
        return Path(db_path).resolve().parent / 'content_library' if db_path else None
    except (OSError, ValueError, TypeError):
        return None


def _load_preview(path, max_width=570, max_height=230):
    """Return a Tk image and keep its reference alive in the owning dialog."""
    try:
        from PIL import Image, ImageTk
        with Image.open(path) as original:
            picture = original.copy()
        picture.thumbnail((max_width, max_height))
        return ImageTk.PhotoImage(picture)
    except (ImportError, OSError, ValueError):
        try:
            return tk.PhotoImage(file=str(path))  # PNG/GIF supported by Tk.
        except (tk.TclError, OSError):
            return None


def _review_items(record):
    """Pure read-only view model; never recompute grades from a changed bank."""
    snapshot = record.get('question_snapshot')
    if not isinstance(snapshot, list):
        return []
    answers = record.get('answers') if isinstance(record.get('answers'), dict) else {}
    ordered = record.get('ordered_answers') if isinstance(record.get('ordered_answers'), dict) else {}
    graded = record.get('graded_answers') if isinstance(record.get('graded_answers'), dict) else {}
    items = []
    for q in snapshot:
        if not isinstance(q, dict):
            continue
        qid = str(q.get('id', ''))
        kind = str(q.get('type', ''))
        value = ordered.get(qid, []) if kind == 'order' else answers.get(qid)
        # Legacy saved attempts may use integer IDs; JSON roundtrips convert them to strings.
        items.append({'question': q, 'type': kind, 'answer': value,
                      'expected': _correct_answer(q), 'graded': graded.get(qid), 'id': qid})
    return items


def _review_lines(item):
    """Structured text fragments: (text, tag) for the read-only viewer."""
    q = item['question']; kind = item['type']; value = item['answer']
    expected = item['expected']; rows = []
    if kind == 'matching':
        rows.append(('CÁC CẶP ĐÃ NỐI', 'heading'))
        if isinstance(value, dict):
            for left, right in value.items():
                rows.append((f'  {left}   →   {right}', 'answer'))
        elif isinstance(value, (list, tuple)):
            for pair in value:
                rows.append(('  ' + _answer_text(pair), 'answer'))
        else:
            rows.append((_answer_text(value), 'answer'))
        rows.append(('Cặp đúng: ' + _answer_text(expected), 'expected'))
    elif kind == 'order':
        rows.append(('THỨ TỰ ĐÃ SẮP XẾP', 'heading'))
        if isinstance(value, (list, tuple)):
            rows.append(('  →  '.join(str(x) for x in value) or '(Chưa trả lời)', 'answer'))
        else:
            rows.append((_answer_text(value), 'answer'))
        rows.append(('Thứ tự đúng: ' + '  →  '.join(str(x) for x in expected) if isinstance(expected, list) else 'Thứ tự đúng: ' + _answer_text(expected), 'expected'))
    elif kind in ('sentence_gaps', 'conversation_gaps', 'passage_gaps'):
        rows.append(('CÁC CHỖ TRỐNG', 'heading'))
        given = value if isinstance(value, (list, tuple)) else []
        correct = expected if isinstance(expected, (list, tuple)) else []
        for i in range(max(len(given), len(correct))):
            got = given[i] if i < len(given) else None
            want = correct[i] if i < len(correct) else None
            same = str(got or '').strip().casefold() == str(want or '').strip().casefold()
            rows.append((f'  Ô {i+1}: {_answer_text(got)}', 'correct' if same else 'wrong'))
            if not same:
                rows.append((f'        Đúng: {_answer_text(want)}', 'expected'))
    else:
        rows.append(('Đã trả lời: ' + _answer_text(value), 'answer'))
        rows.append(('Đáp án đúng: ' + _answer_text(expected), 'expected'))
    return rows


def _visual_rows(item):
    """Read-only visual cells derived from a saved attempt, not the live bank."""
    kind = item['type']
    value = item['answer']
    expected = item['expected']
    if kind == 'matching':
        correct = dict((str(a), str(b)) for a, b in expected if isinstance(a, (str, int, float))) if isinstance(expected, (list, tuple)) and all(isinstance(p, (list, tuple)) and len(p) == 2 for p in expected) else {}
        selected = value if isinstance(value, dict) else {}
        keys = list(dict.fromkeys(list(correct) + list(selected)))
        return [{'left': k, 'right': str(selected.get(k, '—')), 'expected': correct.get(k, '—'),
                 'ok': k in selected and str(selected[k]).strip().casefold() == str(correct.get(k, '')).strip().casefold()} for k in keys]
    if kind == 'order':
        return [{'left': str(i+1), 'right': str(word), 'expected': str(expected[i]) if isinstance(expected, (list, tuple)) and i < len(expected) else '—',
                 'ok': isinstance(expected, (list, tuple)) and i < len(expected) and str(word) == str(expected[i])}
                for i, word in enumerate(value if isinstance(value, (list, tuple)) else [])]
    if kind in ('sentence_gaps', 'conversation_gaps', 'passage_gaps'):
        got = value if isinstance(value, (list, tuple)) else []
        want = expected if isinstance(expected, (list, tuple)) else []
        return [{'left': f'Ô {i+1}', 'right': str(got[i]) if i < len(got) and got[i] else '(Trống)',
                 'expected': str(want[i]) if i < len(want) else '—',
                 'ok': i < len(got) and i < len(want) and str(got[i]).strip().casefold() == str(want[i]).strip().casefold()}
                for i in range(max(len(got), len(want)))]
    return []


def _reading_context(items, index):
    """Group snapshot reading children by stable group id, preserving exam order."""
    if not 0 <= index < len(items):
        return None
    q = items[index]['question']
    gid = q.get('reading_group')
    if not gid:
        return None
    members = [i for i, entry in enumerate(items)
               if str(entry['question'].get('reading_group', '')) == str(gid)]
    if not members:
        return None
    passage = next((str(items[i]['question'].get('passage')) for i in members
                    if items[i]['question'].get('passage')), '')
    title = next((str(items[i]['question'].get('reading_title')) for i in members
                  if items[i]['question'].get('reading_title')), 'Bài đọc')
    return {'id': str(gid), 'title': title, 'passage': passage,
            'members': members, 'position': members.index(index) + 1,
            'total': len(members)}


def _review_navigation_labels(items):
    """Human-friendly quick navigation labels without relying on mutable bank data."""
    labels = []
    for i, item in enumerate(items):
        context = _reading_context(items, i)
        label = f'Câu {i+1}'
        if context:
            label += f' · {context["title"]} ({context["position"]}/{context["total"]})'
        else:
            label += f' · {item["type"]}'
        if item['graded'] is True:
            label += ' ✓'
        elif item['graded'] is False:
            label += ' ✕'
        labels.append(label)
    return labels


def _reading_group_overview(items, index):
    """Return a saved-attempt reading group, never live bank content."""
    context = _reading_context(items, index)
    if not context:
        return None
    children = []
    for number in context['members']:
        item = items[number]
        children.append({'number': number + 1,
                         'prompt': str(display_prompt(item['question'])),
                         'answer': item.get('answer'), 'expected': item.get('expected'),
                         'graded': item.get('graded'), 'type': item.get('type')})
    return dict(context, children=children,
                correct=sum(c['graded'] is True for c in children),
                wrong=sum(c['graded'] is False for c in children),
                ungraded=sum(c['graded'] is not True and c['graded'] is not False for c in children))


def _review_filter_indices(items, mode='all'):
    """Return snapshot positions; unknown grades are not incorrectly marked wrong."""
    if mode == 'correct':
        return [i for i, item in enumerate(items) if item.get('graded') is True]
    if mode == 'wrong':
        return [i for i, item in enumerate(items) if item.get('graded') is False]
    if mode == 'ungraded':
        return [i for i, item in enumerate(items) if item.get('graded') is not True and item.get('graded') is not False]
    return list(range(len(items)))


def _review_summary(items):
    return {'total': len(items), 'correct': len(_review_filter_indices(items, 'correct')),
            'wrong': len(_review_filter_indices(items, 'wrong')),
            'ungraded': len(_review_filter_indices(items, 'ungraded'))}


def _review_type_summary(items):
    """Counts from the saved attempt only; never consult the live bank."""
    summary = {}
    for item in items:
        kind = str(item.get('type') or 'unknown')
        row = summary.setdefault(kind, {'total': 0, 'correct': 0, 'wrong': 0, 'ungraded': 0})
        row['total'] += 1
        state = item.get('graded')
        row['correct' if state is True else 'wrong' if state is False else 'ungraded'] += 1
    return summary


def _review_combined_indices(items, status='all', kind='all'):
    return [i for i in _review_filter_indices(items, status)
            if kind == 'all' or items[i].get('type') == kind]



def _weakest_question_type(items):
    """Rank by wrong answers among graded questions; ties by wrong count and name.

    A type with no graded answers is not considered weak.
    """
    stats = _review_type_summary(items)
    candidates = [(kind, row) for kind, row in stats.items()
                  if row['correct'] + row['wrong'] > 0 and row['wrong'] > 0]
    if not candidates:
        return None
    return min(candidates, key=lambda pair: (
        -(pair[1]['wrong'] / (pair[1]['correct'] + pair[1]['wrong'])),
        -pair[1]['wrong'], pair[0]))[0]


def _exam_review_csv(record):
    """Export an existing attempt without recalculating or mutating its grades."""
    output = io.StringIO(newline='')
    writer = csv.writer(output)
    writer.writerow(['Cau', 'ID', 'Dang', 'Noi dung', 'Tra loi da nop',
                     'Dap an dung', 'Ket qua'])
    for number, item in enumerate(_review_items(record), 1):
        grade = item['graded']
        writer.writerow([number, item['id'], item['type'],
                         display_prompt(item['question']),
                         _answer_text(item['answer']),
                         _answer_text(item['expected']),
                         'Dung' if grade is True else 'Sai' if grade is False else 'Chua cham'])
    return '\ufeff' + output.getvalue()


def show_exam_detail(parent, record, library_dir=None):
    """Read-only attempt viewer with per-question navigation and saved grading."""
    dialog = tk.Toplevel(parent)
    dialog.title('Chi tiết bài kiểm tra')
    dialog.geometry('900x690')
    dialog.minsize(560, 410)
    dialog.transient(parent.winfo_toplevel())
    dialog._preview_images = []
    items = _review_items(record)
    state = {'index': 0, 'filter': 'all', 'type': 'all', 'group_view': False}
    summary = _review_summary(items)
    type_summary = _review_type_summary(items)
    header = tk.Frame(dialog, bg=TOKEN_COLORS['background'], padx=20, pady=14)
    header.pack(fill='x')
    tk.Label(header, text='CHI TIẾT BÀI KIỂM TRA', bg=TOKEN_COLORS['background'], fg='#173E2B',
             font=font_at(16, 'bold')).pack(anchor='w')
    score = f"{record.get('correct', 0)}/{record.get('total', 0)} câu đúng • {record.get('score_percent', 0)}%"
    tk.Label(header, text=score, bg=TOKEN_COLORS['background'], fg='#287A51',
             font=font_at(11)).pack(anchor='w', pady=(4, 0))
    frame = tk.Frame(dialog, padx=18, pady=6)
    frame.pack(fill='both', expand=True)
    bar = ttk.Scrollbar(frame)
    bar.pack(side='right', fill='y')
    detail = tk.Text(frame, wrap='word', yscrollcommand=bar.set,
                     font=font_at(11), padx=14, pady=12, spacing2=5,
                     bg=TOKEN_COLORS['surface'], fg='#173E2B', relief='flat', cursor='arrow')
    detail.pack(side='left', fill='both', expand=True)
    bar.configure(command=detail.yview)
    for tag, opts in {
        'question': {'foreground': '#173E2B', 'font': font_at(13, 'bold'), 'spacing1': 12},
        'heading': {'foreground': '#617669', 'font': font_at(10, 'bold'), 'spacing1': 12},
        'correct': {'foreground': '#287A51'}, 'wrong': {'foreground': '#B54747'},
        'answer': {'foreground': '#173E2B'}, 'expected': {'foreground': '#287A51'},
        'muted': {'foreground': '#617669'},
    }.items():
        detail.tag_configure(tag, **opts)

    filter_bar = tk.Frame(dialog, bg=TOKEN_COLORS['background'], padx=18, pady=7)
    filter_bar.pack(fill='x')
    tk.Label(filter_bar, text='Lọc câu:', bg=TOKEN_COLORS['background'], fg='#173E2B',
             font=font_at(10, 'bold')).pack(side='left', padx=(0, 9))
    filter_buttons = {}
    filter_options = [
        ('all', 'Tất cả', summary['total']),
        ('wrong', 'Câu sai', summary['wrong']),
        ('correct', 'Câu đúng', summary['correct']),
        ('ungraded', 'Chưa chấm', summary['ungraded']),
    ]
    for mode, title, count in filter_options:
        button = tk.Button(filter_bar, text=f'{title} ({count})',
                           bg='#EFF8EF', fg='#173E2B', relief='solid', bd=1,
                           padx=10, pady=5, cursor='hand2')
        button.pack(side='left', padx=(0, 6))
        filter_buttons[mode] = button

    # Compact breakdown by question type; counts are read from saved grading.
    types_bar = tk.Frame(dialog, bg=TOKEN_COLORS['background'], padx=18, pady=5)
    types_bar.pack(fill='x')
    tk.Label(types_bar, text='Theo dạng:', bg=TOKEN_COLORS['background'], fg='#173E2B',
             font=font_at(10, 'bold')).pack(side='left', padx=(0, 8))
    type_names = {'all': 'Tất cả dạng'}
    type_names.update({kind: f'{kind} ({counts["correct"]}/{counts["total"]} đúng)'
                       for kind, counts in sorted(type_summary.items())})
    type_values = list(type_names.values())
    type_var = tk.StringVar(value=type_names['all'])
    type_combo = ttk.Combobox(types_bar, textvariable=type_var,
                              values=type_values, state='readonly', width=38)
    type_combo.pack(side='left', padx=(0, 12))
    type_stats = tk.Label(types_bar, bg=TOKEN_COLORS['background'], fg='#617669',
                          font=font_at(10))
    type_stats.pack(side='left')

    # One-click targeted revision, based only on the saved attempt.
    weakest_kind = _weakest_question_type(items)
    weakest_button = tk.Button(types_bar, text='Ôn dạng yếu nhất',
                               bg='#FFF1DF', fg='#85511C', relief='solid', bd=1,
                               padx=10, pady=5, cursor='hand2')
    weakest_button.pack(side='right')
    if weakest_kind is None:
        weakest_button.configure(state='disabled', text='Không có câu sai')

    nav = tk.Frame(dialog, bg=TOKEN_COLORS['background'], padx=18, pady=12)
    nav.pack(fill='x')
    counter = tk.Label(nav, bg=TOKEN_COLORS['background'], fg='#617669', font=font_at(10))
    counter.pack(side='left')
    tk.Button(nav, text='Đóng', command=dialog.destroy, bg='#EFF8EF',
              fg='#173E2B', padx=14, pady=8, cursor='hand2').pack(side='right', padx=(8, 0))
    next_button = tk.Button(nav, text='Câu tiếp →', bg='#EFF8EF', fg='#173E2B',
                            padx=12, pady=8, cursor='hand2')
    next_button.pack(side='right')
    prev_button = tk.Button(nav, text='← Câu trước', bg='#EFF8EF', fg='#173E2B',
                            padx=12, pady=8, cursor='hand2')
    prev_button.pack(side='right', padx=(0, 8))

    group_button = tk.Button(nav, text='Xem cả bài đọc', bg='#E8F1FA', fg='#174A73',
                             padx=10, pady=8, cursor='hand2')
    group_button.pack(side='left', padx=(0, 8))

    # Quick navigation stays read-only and is synchronized with Previous/Next.
    all_jump_labels = _review_navigation_labels(items)
    jump_labels = list(all_jump_labels)
    jump_var = tk.StringVar(value=jump_labels[0] if jump_labels else 'Không có câu hỏi')
    jump = ttk.Combobox(nav, textvariable=jump_var, values=jump_labels,
                        state='readonly', width=35)
    jump.pack(side='right', padx=(0, 12))

    def visible_indices():
        return _review_combined_indices(items, state['filter'], state['type'])

    def jump_to(_event=None):
        selected = jump.current()
        visible = visible_indices()
        if 0 <= selected < len(visible):
            state['index'] = visible[selected]
            state['group_view'] = False
            render()

    jump.bind('<<ComboboxSelected>>', jump_to)

    def line(text, tag=None):
        detail.insert('end', str(text) + '\n', (tag,) if tag else ())

    def add_media(value, label, is_audio=False):
        if not value:
            return
        path = resolve_exam_media(value, library_dir)
        if path is None:
            line(f'{label}: Không tìm thấy tài nguyên ({value})', 'muted')
            return
        if is_audio:
            def play(p=path):
                try:
                    if os.name == 'nt':
                        os.startfile(str(p))
                    else:
                        import tuhoc.ui.ui_dialogs as messagebox
                        messagebox.showinfo('File nghe', f'Đường dẫn: {p}', parent=dialog)
                except (OSError, AttributeError) as exc:
                    import tuhoc.ui.ui_dialogs as messagebox
                    messagebox.showerror('Không mở được âm thanh', str(exc), parent=dialog)
            button = tk.Button(detail, text='▶ Nghe âm thanh', command=play,
                               bg='#EFF8EF', fg='#173E2B', relief='solid', bd=1,
                               cursor='hand2', padx=12, pady=6)
            detail.window_create('end', window=button)
            line('')
        else:
            preview = _load_preview(path)
            if preview is None:
                line(f'{label}: {path.name} (không có bộ giải mã ảnh)', 'muted')
            else:
                dialog._preview_images.append(preview)
                detail.image_create('end', image=preview)
                line('')

    def render():
        detail.configure(state='normal')
        detail.delete('1.0', 'end')
        dialog._preview_images.clear()
        visible = visible_indices()
        if not items:
            group_button.configure(state='disabled')
            line('Bài kiểm tra cũ chưa lưu nội dung câu hỏi.', 'muted')
            line('Chỉ có thể xem điểm tổng kết của lượt làm này.', 'muted')
            counter.configure(text='Không có chi tiết')
        elif not visible:
            group_button.configure(state='disabled')
            line('Không có câu hỏi nào thuộc bộ lọc này.', 'muted')
            counter.configure(text='0 câu phù hợp')
        else:
            item = items[state['index']]
            q = item['question']; result = item['graded']; kind = item['type']
            status = 'ĐÚNG' if result is True else 'SAI' if result is False else 'CHƯA CHẤM'
            counter.configure(text=f'Câu {state["index"]+1}/{len(items)} · {visible.index(state["index"])+1}/{len(visible)} trong bộ lọc')
            overview = _reading_group_overview(items, state['index'])
            group_button.configure(state='normal' if overview else 'disabled',
                                   text='Xem từng câu' if state['group_view'] and overview else 'Xem cả bài đọc')
            if overview and state['group_view']:
                line('BÀI ĐỌC: ' + overview['title'], 'question')
                line(overview['passage'] or '(Không có nội dung bài đọc trong bản lưu)', 'answer')
                line(f"TỔNG KẾT NHÓM: {overview['correct']} đúng · {overview['wrong']} sai · {overview['ungraded']} chưa chấm", 'heading')
                for child in overview['children']:
                    result = child['graded']
                    mark = 'ĐÚNG' if result is True else 'SAI' if result is False else 'CHƯA CHẤM'
                    line(f"CÂU {child['number']} — {mark}", 'heading')
                    line(child['prompt'])
                    line('Đã trả lời: ' + _answer_text(child['answer']), 'answer')
                    line('Đáp án đúng: ' + _answer_text(child['expected']), 'expected')
            else:
                line(f'CÂU {state["index"]+1} — {status} ({kind})', 'question')
                line(display_prompt(q))
                reading = _reading_context(items, state['index'])
                if reading:
                    line(f'BÀI ĐỌC: {reading["title"]}', 'heading')
                    line(reading['passage'] or '(Không có nội dung đoạn đọc trong bản lưu)', 'answer')
                    line(f'CÂU HỎI CON {reading["position"]}/{reading["total"]}', 'heading')
                    # Show every child status in the group, while keeping the current answer below.
                    for child_index in reading['members']:
                        child = items[child_index]
                        child_no = child['question'].get('reading_index') or (reading['members'].index(child_index)+1)
                        mark = '✓' if child['graded'] is True else '✕' if child['graded'] is False else '·'
                        label = str(child['question'].get('prompt', '')).replace('\n', ' ').strip()
                        if len(label) > 95:
                            label = label[:92] + '…'
                        prefix = '► ' if child_index == state['index'] else '  '
                        line(f'{prefix}{child_no}. {label}  {mark}',
                             'correct' if child['graded'] is True else 'wrong' if child['graded'] is False else 'muted')
                elif q.get('passage'):
                    line('BÀI ĐỌC', 'heading')
                    line(q['passage'])
                add_media(q.get('image'), 'Hình câu hỏi')
                if kind in ('image_multi_choice', 'listening_image_choice'):
                    for number, option in enumerate(q.get('options', []), 1):
                        line(f'Lựa chọn {number}:', 'muted')
                        add_media(option, 'Hình đáp án')
                add_media(q.get('audio'), 'Âm thanh', is_audio=True)
                if kind in ('matching', 'order', 'sentence_gaps', 'conversation_gaps', 'passage_gaps'):
                    line('CHI TIẾT ĐÁP ÁN ĐÃ NỘP', 'heading')
                    rows = _visual_rows(item)
                    if not rows:
                        line('(Chưa có đáp án)', 'muted')
                    for entry in rows:
                        bg = '#EFF8EF' if entry['ok'] else '#FFF1F0'
                        fg = '#287A51' if entry['ok'] else '#B54747'
                        cell = tk.Frame(detail, bg=bg, padx=12, pady=9)
                        tk.Label(cell, text=entry['left'], bg=bg, fg='#173E2B',
                                 font=font_at(10, 'bold'), width=13, anchor='w').pack(side='left')
                        tk.Label(cell, text='→  ' + entry['right'], bg=bg, fg=fg,
                                 font=font_at(10), anchor='w', wraplength=330).pack(side='left')
                        tk.Label(cell, text='✓' if entry['ok'] else '✕', bg=bg, fg=fg,
                                 font=font_at(12, 'bold')).pack(side='right')
                        detail.window_create('end', window=cell, stretch=1)
                        line('')
                        if not entry['ok']:
                            line('    Đáp án đúng: ' + entry['expected'], 'expected')
                    if kind == 'order':
                        line('Thứ tự chuẩn: ' + _answer_text(item['expected']), 'expected')
                    # Per-cell coloring is explanatory only. Saved graded result remains authoritative.
                else:
                    for text, tag in _review_lines(item):
                        line(text, tag)
        stats = summary if state['type'] == 'all' else type_summary.get(state['type'], {})
        type_stats.configure(text=f"Đúng {stats.get('correct', 0)} · Sai {stats.get('wrong', 0)} · Chưa chấm {stats.get('ungraded', 0)}")
        if jump_labels and visible:
            jump.current(visible.index(state['index']))
        detail.configure(state='disabled')
        detail.yview_moveto(0)
        position = visible.index(state['index']) if visible else -1
        prev_button.configure(state='normal' if position > 0 else 'disabled')
        next_button.configure(state='normal' if position >= 0 and position < len(visible)-1 else 'disabled')
        for mode, button in filter_buttons.items():
            active = mode == state['filter']
            button.configure(bg='#287A51' if active else '#EFF8EF',
                             fg=TOKEN_COLORS['surface'] if active else '#173E2B',
                             relief='sunken' if active else 'solid')

    def move(step):
        visible = visible_indices()
        if state['index'] not in visible:
            return
        position = visible.index(state['index']) + step
        if 0 <= position < len(visible):
            state['index'] = visible[position]
            state['group_view'] = False
            render()

    def select_filter(mode):
        state['filter'] = mode
        state['group_view'] = False
        visible = _review_combined_indices(items, mode, state['type'])
        jump_labels[:] = [all_jump_labels[i] for i in visible]
        jump.configure(values=jump_labels)
        if visible and state['index'] not in visible:
            state['index'] = visible[0]
        if not visible:
            jump_var.set('Không có câu hỏi')
        render()

    def select_type(_event=None):
        chosen = type_var.get()
        state['group_view'] = False
        state['type'] = next((kind for kind, label in type_names.items() if label == chosen), 'all')
        visible = visible_indices()
        jump_labels[:] = [all_jump_labels[i] for i in visible]
        jump.configure(values=jump_labels)
        if visible and state['index'] not in visible:
            state['index'] = visible[0]
        if not visible:
            jump_var.set('Không có câu hỏi')
        render()


    def focus_weakest():
        if weakest_kind is None:
            return
        state['type'] = weakest_kind
        type_var.set(type_names[weakest_kind])
        select_filter('wrong')

    def toggle_group():
        if _reading_context(items, state['index']):
            state['group_view'] = not state['group_view']
            render()

    group_button.configure(command=toggle_group)

    weakest_button.configure(command=focus_weakest)

    def export_csv():
        from tkinter import filedialog
        import tuhoc.ui.ui_dialogs as messagebox
        filename = filedialog.asksaveasfilename(
            parent=dialog, title='Xuất chi tiết bài kiểm tra',
            defaultextension='.csv', filetypes=[('CSV UTF-8', '*.csv')])
        if not filename:
            return
        try:
            with open(filename, 'w', encoding='utf-8-sig', newline='') as stream:
                # The export function includes a BOM for spreadsheet compatibility.
                stream.write(_exam_review_csv(record).lstrip('\ufeff'))
        except OSError as exc:
            messagebox.showerror('Không thể xuất CSV', str(exc), parent=dialog)

    tk.Button(nav, text='Xuất CSV', command=export_csv, bg='#EFF8EF',
              fg='#173E2B', padx=12, pady=8, cursor='hand2').pack(side='left', padx=(8, 0))

    type_combo.bind('<<ComboboxSelected>>', select_type)

    for mode, button in filter_buttons.items():
        button.configure(command=lambda m=mode: select_filter(m))

    prev_button.configure(command=lambda: move(-1))
    next_button.configure(command=lambda: move(1))
    dialog.bind('<Escape>', lambda _event: dialog.destroy())
    dialog.bind('<Left>', lambda _event: move(-1))
    dialog.bind('<Right>', lambda _event: move(1))
    render()
    return dialog


def history_window(rows,days,now=None):
    if days is None:
        return list(rows)
    now=now or datetime.datetime.now()
    cutoff=(now-datetime.timedelta(days=days-1)).replace(hour=0,minute=0,second=0,microsecond=0)
    start,end=cutoff.timestamp(),now.timestamp()
    visible=[]
    for row in rows:
        try:timestamp=float(row[3])
        except (TypeError,ValueError):continue
        if start<=timestamp<=end:visible.append(row)
    return visible


def show_history(parent, conn, student_id, on_back=None, on_retry=None):
    """Modern, borderless learning-history table. Read-only database access."""
    BG = TOKEN_COLORS['background']
    INK = '#173E2B'
    MUTED = '#617669'
    GREEN = '#287A51'
    PALE_GREEN = '#EFF8EF'
    PALE_YELLOW = '#FFF9E8'
    HOVER = '#DDF1DE'
    HEADER = '#E7F1E7'
    WHITE = TOKEN_COLORS['surface']
    font = 'Segoe UI'
    outer = tk.Frame(parent, bg=BG)
    outer.pack(fill='both', expand=True)

    title_row = tk.Frame(outer, bg=BG)
    title_row.pack(fill='x', pady=(6, 3))
    tk.Label(title_row, text=t('history'), bg=BG, fg=INK,
             font=(font, 19, 'bold')).pack(side='left')
    if on_retry:
        tk.Button(title_row,text='Ôn lại câu sai',command=on_retry,
                  bg=PALE_GREEN,fg=INK,bd=0,padx=12,pady=8,takefocus=True).pack(side='right',padx=6)
    if on_back:
        back = tk.Button(title_row, text='← Quay lại', command=on_back,
                         bg=PALE_GREEN, activebackground=HOVER, fg=INK,
                         activeforeground=INK, relief='flat', bd=0,
                         padx=14, pady=8, cursor='hand2', font=(font, 10))
        back.pack(side='right')
        back.bind('<Enter>', lambda e: back.config(bg=HOVER))
        back.bind('<Leave>', lambda e: back.config(bg=PALE_GREEN))

    tk.Label(outer, text='Theo dõi những lần hoàn thành bài tập của bạn',
             bg=BG, fg=MUTED, font=(font, 10)).pack(anchor='w', pady=(0, 16))

    filters = tk.Frame(outer, bg=BG)
    filters.pack(fill='x', pady=(0, 12))
    tk.Label(filters, text='Môn học', bg=BG, fg=INK,
             font=(font, 10, 'bold')).pack(side='left', padx=(0, 12))
    selected = tk.StringVar(value='Tất cả')
    options = {'Tất cả': None, 'Tiếng Anh': 'en', 'Tiếng Việt': 'vi', 'Toán': 'toan'}
    style = ttk.Style()
    style.configure('LearningHistory.TCombobox', padding=6,
                    fieldbackground=WHITE, background=PALE_GREEN,
                    foreground=INK, borderwidth=0)
    combo = ttk.Combobox(filters, textvariable=selected, values=list(options),
                         state='readonly', width=17, style='LearningHistory.TCombobox')
    combo.pack(side='left')
    periods={'Mọi thời gian':None,'7 ngày':7,'30 ngày':30,'90 ngày':90}
    period=tk.StringVar(value='Mọi thời gian')
    time_filter=ttk.Combobox(filters,textvariable=period,values=list(periods),state='readonly',width=15)
    tk.Label(filters,text='Thời gian',bg=BG,fg=INK).pack(side='left',padx=(16,8))
    time_filter.pack(side='left')

    # Each row uses the same grid proportions as the heading, so the table
    # remains aligned when the parent window is resized.
    columns = [
        ('Ngày hoàn thành', 20, 'w'), ('Môn', 13, 'w'),
        ('Chủ đề', 25, 'w'), ('Level', 8, 'center'),
        ('Đúng / Tổng', 12, 'center'), ('Tỷ lệ', 10, 'center'),
        ('Thời gian', 12, 'center')]
    table = tk.Frame(outer, bg=BG)
    table.pack(fill='both', expand=True)

    def make_grid(frame):
        for index, (_, weight, _) in enumerate(columns):
            frame.grid_columnconfigure(index, weight=weight, uniform='history')

    heading = tk.Frame(table, bg=HEADER)
    heading.pack(fill='x', pady=(0, 3))
    make_grid(heading)
    for index, (name, _, anchor) in enumerate(columns):
        tk.Label(heading, text=name, bg=HEADER, fg=INK,
                 font=(font, 9, 'bold'), anchor=anchor,
                 padx=9, pady=12).grid(row=0, column=index, sticky='nsew')

    body = tk.Frame(table, bg=BG)
    body.pack(fill='both', expand=True)
    canvas = tk.Canvas(body, bg=BG, bd=0, highlightthickness=0,
                       relief='flat', takefocus=0)
    scrollbar = ttk.Scrollbar(body, orient='vertical', command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side='right', fill='y')
    canvas.pack(side='left', fill='both', expand=True)
    rows_container = tk.Frame(canvas, bg=BG)
    window = canvas.create_window((0, 0), window=rows_container, anchor='nw')
    rows_container.bind('<Configure>', lambda _e: canvas.configure(scrollregion=canvas.bbox('all')))
    canvas.bind('<Configure>', lambda e: canvas.itemconfigure(window, width=e.width))

    def wheel(event):
        if getattr(event, 'num', None) == 4:
            amount = -1
        elif getattr(event, 'num', None) == 5:
            amount = 1
        else:
            amount = -int(event.delta / 120) if event.delta else 0
        if amount:
            canvas.yview_scroll(amount, 'units')
        return 'break'

    # Bind on each row and label, rather than bind_all, so scrolling elsewhere
    # in the application is unaffected.
    def bind_wheel(widget):
        for event_name in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
            widget.bind(event_name, wheel)
    bind_wheel(canvas)
    bind_wheel(rows_container)

    footer = tk.Frame(outer, bg=BG)
    footer.pack(fill='x', pady=(12, 4))
    summary = tk.Label(footer, bg=BG, fg=MUTED, font=(font, 10))
    summary.pack(side='left')
    page_indicator = tk.Label(footer, bg=BG, fg=INK, font=(font, 10, 'bold'))
    page_indicator.pack(side='left', padx=(18, 0))
    next_btn = tk.Button(footer, text='Trang sau →', bg=PALE_GREEN, fg=INK,
                         activebackground=HOVER, relief='flat', bd=0,
                         padx=12, pady=8, cursor='hand2', font=(font, 10))
    next_btn.pack(side='right', padx=(8, 0))
    prev_btn = tk.Button(footer, text='← Trang trước', bg=PALE_GREEN, fg=INK,
                         activebackground=HOVER, relief='flat', bd=0,
                         padx=12, pady=8, cursor='hand2', font=(font, 10))
    prev_btn.pack(side='right')
    page = [0]

    def render():
        for child in rows_container.winfo_children():
            child.destroy()
        language = options.get(selected.get())
        if language == 'vi':
            where = "AND theme LIKE 'vi:%'"
        elif language == 'en':
            where = "AND theme NOT LIKE 'vi:%'"
        else:
            where = ''
        db_records = [] if language == 'toan' else conn.execute(
            'SELECT id,theme,level,started,seconds,correct,total FROM learning_sessions '
            'WHERE student_id=? '+where+' ORDER BY started DESC,id DESC', (student_id,)).fetchall()
        exams = exam_records(conn, student_id, language)
        exam_subjects = {'exam:'+item[0]: item[1] for item in exams}
        exam_rows = [('exam:'+item[0], '[Kiểm tra] '+item[2], item[3], item[4], None,
                      item[5], item[6]) for item in exams]
        combined = sorted(list(db_records) + exam_rows, key=lambda r: float(r[3] or 0), reverse=True)
        combined=history_window(combined,periods[period.get()])
        count = len(combined)
        max_page = (count - 1) // PAGE_SIZE if count else 0
        page[0] = min(page[0], max_page)
        records = combined[page[0]*PAGE_SIZE:(page[0]+1)*PAGE_SIZE]
        for row_num, (_id, theme, level, started, seconds, correct, total) in enumerate(records):
            is_vi = str(theme).startswith('vi:')
            clean_theme = str(theme)[3:] if is_vi else str(theme)
            total = int(total or 0)
            correct = int(correct or 0)
            percent = correct * 100 / total if total else None
            exam_subject = exam_subjects.get(_id)
            subject_label = EXAM_SUBJECTS.get(
                exam_subject, 'Tiếng Việt' if is_vi or exam_subject == 'vi' else 'Tiếng Anh')
            values = (_date(started), subject_label,
                      clean_theme, str(level), f'{correct}/{total}',
                      f'{percent:.0f}%' if percent is not None else '—',
                      _duration(seconds))
            base = PALE_GREEN if row_num % 2 == 0 else PALE_YELLOW
            row = tk.Frame(rows_container, bg=base)
            row.pack(fill='x', pady=(0, 3))
            make_grid(row)
            labels = []
            for col, value in enumerate(values):
                anchor = columns[col][2]
                fg = GREEN if col == 5 else INK
                label = tk.Label(row, text=value, bg=base, fg=fg,
                                 font=(font, 10, 'bold' if col == 5 else 'normal'),
                                 anchor=anchor, padx=9, pady=11)
                label.grid(row=0, column=col, sticky='nsew')
                labels.append(label)
            def enter(_event, r=row, cells=labels):
                r.configure(bg=HOVER)
                for cell in cells:
                    cell.configure(bg=HOVER)
            def leave(_event, r=row, cells=labels, color=base):
                r.configure(bg=color)
                for cell in cells:
                    cell.configure(bg=color)
            # Hover on individual labels; moving between cells should not flicker.
            def update_hover(_event, r=row, cells=labels, color=base):
                x, y = r.winfo_pointerxy()
                inside = (r.winfo_rootx() <= x < r.winfo_rootx()+r.winfo_width()
                          and r.winfo_rooty() <= y < r.winfo_rooty()+r.winfo_height())
                shade = HOVER if inside else color
                r.configure(bg=shade)
                for cell in cells:
                    cell.configure(bg=shade)
            if str(_id).startswith('exam:'):
                exam_id = str(_id)[5:]
                def open_attempt(_event=None, attempt_id=exam_id):
                    record = exam_detail(conn, student_id, attempt_id)
                    if record is not None:
                        show_exam_detail(outer, record, _history_library_dir(conn))
                for clickable in [row] + labels:
                    clickable.configure(cursor='hand2')
                    clickable.bind('<Button-1>', open_attempt)
            for widget in [row] + labels:
                widget.bind('<Enter>', enter)
                widget.bind('<Leave>', update_hover)
                bind_wheel(widget)
        if not records:
            empty = EmptyState(rows_container, t('history_empty'), background=BG)
            empty.pack(fill='x')
            bind_wheel(empty)
        start = page[0] * PAGE_SIZE + 1 if count else 0
        end = min((page[0] + 1) * PAGE_SIZE, count)
        summary.config(text=f'Hiển thị {start}–{end} / {count} lượt hoàn thành' if count
                       else t('history_empty'))
        page_indicator.config(text=f'Trang {page[0] + 1} / {max(1, (count + PAGE_SIZE - 1) // PAGE_SIZE)}')
        prev_btn.config(state='normal' if page[0] > 0 else 'disabled')
        next_btn.config(state='normal' if end < count else 'disabled')
        canvas.yview_moveto(0)

    def move(delta):
        page[0] = max(0, page[0] + delta)
        render()

    prev_btn.config(command=lambda: move(-1))
    next_btn.config(command=lambda: move(1))
    for selector in (combo,time_filter):
        selector.bind('<<ComboboxSelected>>',lambda _event:(page.__setitem__(0,0),render()))
    render()
