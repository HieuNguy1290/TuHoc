"""Pure, read-only analytics for a completed exercise attempt."""
from collections import defaultdict

TYPE_NAMES = {
    'choice': 'Trắc nghiệm', 'multi_choice': 'Trắc nghiệm',
    'true_false': 'Đúng / Sai', 'listening': 'Nghe',
    'listening_choice': 'Nghe và chọn', 'listening_fill': 'Nghe và điền',
    'picture_choice': 'Chọn hình', 'image_multi_choice': 'Chọn hình',
    'listening_image_choice': 'Nghe và chọn hình',
    'matching': 'Nối cặp', 'ordering': 'Sắp xếp',
    'fill': 'Điền từ', 'fill_blank': 'Điền từ',
    'sentence_gaps': 'Hoàn thành câu', 'conversation_gaps': 'Hội thoại',
    'passage_gaps': 'Điền đoạn văn', 'picture_missing_letters': 'Điền chữ',
    'error_correction': 'Sửa lỗi',
    'image_sentence_fill': 'Hoàn thành câu', 'image_letter_pick': 'Chọn chữ cái', 'inline_dropdown_fill': 'Chọn trong câu',
}

def summarize(answers):
    """Return aggregate counts; never mutate question or answer data."""
    groups = defaultdict(lambda: [0, 0])
    wrong_numbers = []
    for number, row in enumerate(answers, 1):
        question, _answer, ok = row
        kind = str(question.get('type') or 'choice') if isinstance(question, dict) else 'choice'
        label = TYPE_NAMES.get(kind, kind.replace('_', ' ').capitalize())
        groups[label][1] += 1
        if ok is True or ok == 1:
            groups[label][0] += 1
        else:
            wrong_numbers.append(number)
    by_type = [dict(name=name, correct=values[0], total=values[1])
               for name, values in sorted(groups.items(), key=lambda item: (-item[1][1], item[0]))]
    return dict(by_type=by_type, wrong_numbers=wrong_numbers,
                total=len(answers), correct=len(answers)-len(wrong_numbers))
