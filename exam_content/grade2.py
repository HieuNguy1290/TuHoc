"""Vietnamese grade-two content for the Exam Mode question bank."""
import argparse
from pathlib import Path

from exam_content import grade2_math, grade2_vietnamese

LESSON = "Ôn tập lớp 2"
# Enough at every difficulty for all ten default blueprints, even at 50 items.
LEVEL_COUNTS = (35, 15, 15, 18, 17)


def _choice(prompt, correct, *distractors):
    return dict(type="choice", prompt=prompt, answer=str(correct),
                options=[str(value) for value in (correct, *distractors)])


def _fill(prompt, correct):
    return dict(type="fill", prompt=prompt, answer=str(correct))


def _truth(prompt, correct):
    return dict(type="true_false", prompt=prompt, answer="Đúng" if correct else "Sai",
                options=["Đúng", "Sai"])


def _order(prompt, *parts):
    return dict(type="order", prompt=prompt, sequence=list(parts))


def _matching(prompt, *pairs):
    return dict(type="matching", prompt=prompt, matching_mode="Chữ ↔ Chữ",
                pairs=[list(pair) for pair in pairs])


def _gaps(prompt, *answers):
    return dict(type="sentence_gaps", prompt=prompt, gap_answers=list(answers))


def _reading(passage, prompt, correct, *distractors):
    return {**_choice(prompt, correct, *distractors), "passage": passage}


def build_questions():
    shared = (_choice, _fill, _truth, _order, _matching)
    questions = []
    for subject, module, factories in (
        ("toan", grade2_math, shared),
        ("tieng_viet", grade2_vietnamese, (*shared, _gaps, _reading)),
    ):
        for level, expected in enumerate(LEVEL_COUNTS, 1):
            rows = list(module.items(level, *factories))
            if len(rows) != expected:
                raise ValueError(f"Bộ lớp 2, {subject} M{level}: cần {expected} câu, có {len(rows)}.")
            for index, row in enumerate(rows, 1):
                if row["type"] == "choice":
                    options = row["options"]
                    offset = (index + level) % len(options)
                    row["options"] = options[offset:] + options[:offset]
                questions.append({
                    **row,
                    "id": f"TH_G2_{subject.upper()}_M{level}_{index:02d}",
                    "subject": subject,
                    "grade": "2",
                    "lesson": LESSON,
                    "difficulty": level,
                })
    return questions


def install(bank):
    return bank.add_text_questions(build_questions())


def main():
    from tuhoc.exams.exam_bank import ExamBank

    parser = argparse.ArgumentParser(description="Nạp 200 câu Toán và Tiếng Việt lớp 2.")
    parser.add_argument("--root", required=True, type=Path, help="Thư mục hồ sơ TuHocBeta.")
    args = parser.parse_args()
    try:
        count = install(ExamBank(args.root))
    except (ValueError, OSError) as exc:
        parser.exit(1, f"Không nạp được bộ lớp 2: {exc}\n")
    print(f"Đã thêm {count} câu lớp 2. {200 - count} mã đã có được giữ nguyên.")


if __name__ == "__main__":
    main()
