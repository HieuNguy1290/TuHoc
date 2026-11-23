"""Nhìn hình - bấm chọn chữ cái điền vào chỗ thiếu (ví dụ Hap....y b....rthday).

Dùng chung dữ liệu và cách chấm với image_sentence_fill:
blank_text, blank_answers (từng chữ theo thứ tự), distractors.
"""
from tuhoc.exercises.image_sentence_extension import correct, expected  # noqa: F401


def build_editor(parent, original, import_media, resolve_media=None):
    from tuhoc.exercises.image_sentence_extension import build_editor as build
    return build(parent, original, import_media, resolve_media, kind='image_letter_pick')


def run(question):
    from tuhoc.exercises.image_sentence_extension import run as run_fill
    return run_fill(question, letter_mode=True)
