# -*- coding: utf-8 -*-
"""Thêm 8 câu hỏi ve2.15 - ve2.22 (Level 1, Lesson 2) vào level_questions.json của Tiếng Anh.

Cách dùng: chép file này vào thư mục app, rồi chạy:   python them_cau_hoi_ve2.py
(hoặc kéo thả đường dẫn level_questions.json vào:       python them_cau_hoi_ve2.py "đường dẫn")
- Tự sao lưu file cũ trước khi ghi (level_questions.backup_<giờ>.json).
- Câu nào đã có mã (theme + id) thì bỏ qua, không ghi đè, không mất câu cũ.
- Các câu chưa có hình: để trống, bạn thêm hình sau trong màn hình sửa câu hỏi.
"""
from tuhoc.paths import PROJECT_ROOT
import json, sys, time, shutil
from pathlib import Path

THEME_TITLE = 'VioeduEng'      # tên chủ đề hiển thị trong ô "Chủ đề"
FALLBACK_THEME = 'theme_002'
LEVEL, LESSON = 1, 2

def row(i, typ, prompt, **kw):
    r = {'id': f've2.{i}', 'prompt': prompt, 'level': LEVEL, 'lesson': LESSON, 'type': typ}
    r.update(kw)
    r.update({'accepted_answers': [], 'audio': '', 'schema_version': '2.0'})
    r.setdefault('image', '')
    return r

ROWS = [
    row(15, 'picture_choice', 'Look and choose:\nDo you like pasta?',
        options=['Yes, I do', "Yes, I don't", "No, I don't"], answer='Yes, I do'),
    row(16, 'image_multi_select', 'What can you see in the picture?',
        options=['A dog', 'An apple', 'Popcorn', 'Pizza'], answers=['Popcorn', 'Pizza'],
        answer='Popcorn | Pizza', passage=''),
    row(17, 'image_sentence_fill', 'Choose the correct word:',
        blank_text='I eat pizza and .... games at my birthday party.', blank_answers=['play'],
        distractors=['go', 'see'], options=['play', 'go', 'see'], answer='play'),
    row(18, 'image_sentence_fill', 'Do you like popcorn?',
        blank_text='.... The popcorn is yummy.', blank_answers=['Yes, I do.'],
        distractors=["No, I don't.", "Yes, I don't."], options=['Yes, I do.', "No, I don't.", "Yes, I don't."],
        answer='Yes, I do.'),
    row(19, 'multi_fill_blanks', 'Look and write:',
        blank_text='I [[1]] games with my friends.', blank_answers=['play'], answer='play', options=[]),
    row(20, 'picture_choice', 'Look and choose:',
        options=['The pizza is yummy', 'I like pizza', "I don't like pizza"], answer="I don't like pizza"),
    row(21, 'multi_fill_blanks', 'Look and write:',
        blank_text='The [[1]] is yummy.', blank_answers=['pizza'], answer='pizza', options=[]),
    row(22, 'image_sentence_fill', 'Make sentence:',
        blank_text='.... .... .... ....', blank_answers=['The', 'pasta', 'is', 'yummy.'],
        distractors=[], options=['The', 'pasta', 'is', 'yummy.'], answer='The | pasta | is | yummy.'),
]

def find_file():
    if len(sys.argv) > 1:
        return Path(sys.argv[1].strip('"'))
    here = PROJECT_ROOT
    for c in (here / 'mon_hoc' / 'tieng_anh' / 'content_library' / 'level_questions.json',
              here / 'app' / 'mon_hoc' / 'tieng_anh' / 'content_library' / 'level_questions.json'):
        if c.exists():
            return c
    raise SystemExit('Không tìm thấy level_questions.json của Tiếng Anh. Hãy chạy kèm đường dẫn file.')

def theme_code(folder):
    try:
        for t in json.loads((folder / 'themes.json').read_text(encoding='utf-8-sig')):
            if THEME_TITLE in (t.get('title'), t.get('code')):
                return t['code']
    except (OSError, ValueError):
        pass
    return FALLBACK_THEME

def main():
    path = find_file()
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    code = theme_code(path.parent)
    have = {(str(r.get('theme')), str(r.get('id'))) for r in data}
    added = []
    for r in ROWS:
        r = dict(r, theme=code)
        if (code, r['id']) in have:
            print('Bỏ qua (đã có):', r['id']); continue
        data.append(r); added.append(r['id'])
    if not added:
        print('Không có câu mới nào để thêm.'); return
    backup = path.with_name(f"level_questions.backup_{time.strftime('%Y%m%d_%H%M%S')}.json")
    shutil.copy2(path, backup)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Đã thêm {len(added)} câu vào chủ đề "{code}", Level {LEVEL}, Lesson {LESSON}:', ', '.join(added))
    print('Sao lưu:', backup.name)

if __name__ == '__main__':
    main()
