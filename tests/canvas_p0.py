"""Run the original lesson renderer, grade its answers, and capture the P0 baseline."""
import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import random
import sys
from tempfile import TemporaryDirectory
import time
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.update(SDL_AUDIODRIVER="dummy", PYGAME_HIDE_SUPPORT_PROMPT="1", TU_HOC_PROFILE="0")

import pygame

from canvas_p0_cases import authored_layout, cases, legacy_layout


CHOICE = {"choice", "picture_choice", "true_false", "listening_choice"}
TEXT = {"fill", "listening_fill", "error"}
GAPS = {"sentence_gaps", "passage_gaps", "conversation_gaps"}
CHIPS = {"image_sentence_fill", "image_letter_pick"}
MULTI_SELECT = {"image_multi_select", "text_multi_select", "audio_multi_select"}
UNDERLINE = {"image_underline_choice", "sentence_underline_words"}


def numbered(rects, values, name="option"):
    return [((name, values[index]), rect) for rect, index in rects if isinstance(index, int)]


def controls(kind, drawn):
    """Read the actual hit rectangles already computed by the active renderer."""
    if kind in CHOICE | TEXT | {"order", "matching"}:
        if kind in CHOICE:
            hits = numbered(drawn["cells"], drawn["options"])
            key = "fixed_submit_rect"
        elif kind in TEXT:
            hits = [(("field", 0), drawn["r"])]
            key = "fixed_text_rect"
        elif kind == "order":
            hits = numbered(drawn["cells"], drawn["options"])
            key = "fixed_sequence_rect"
        else:
            hits = [(("pair", (side, i)), rect) for rect, side, i in drawn["matching_cells"]]
            key = "fixed_sequence_rect"
        return hits, drawn[key], drawn["content_scroll"], drawn["max_content_scroll"], True

    if kind == "listening_image_choice":
        hits = [(("option", opt[0]), rect) for rect, opt in zip(drawn["cards"], drawn["options"])]
        page = drawn.get("page")
        return hits, drawn["submit"], getattr(page, "scroll", 0), getattr(page, "limit", 0), True
    if kind == "image_multi_choice":
        hits = [(("option", drawn["items"][i]), r) for r, (action, i) in drawn["hits"]]
        page = drawn["choice_page_surface"]
        return (hits, drawn["fixed_submit"], page.scroll, page.limit, True) if page else (
            hits, drawn["submit"], 0, 0, True)
    if kind == "picture_missing_letters":
        page = drawn["letter_page"]
        return [(key, r) for r, key in drawn["hits"]], drawn["fixed_submit"], page.scroll, page.limit, True
    if kind in GAPS | CHIPS:
        hits = [(("option", drawn["choices"][i]) if action == "choice" else (action, i), rect)
                for rect, (action, i) in drawn["hits"]]
        if kind in GAPS:
            return hits, drawn["submit"], drawn["scroll"], drawn["max_scroll"], True
        return hits, drawn["submit"], drawn["scroll_y"], drawn["scroll_max"], True

    page = drawn["page"]
    if kind in MULTI_SELECT:
        hits = numbered(drawn["cells"], drawn["opts"])
        submit, fixed = drawn["fixed_submit"], True
    elif kind == "image_write_answer":
        hits = [(("field", 0), drawn["field"])]
        submit, fixed = drawn["submit"], True
    elif kind in UNDERLINE:
        values = drawn["options"] if kind == "image_underline_choice" else range(len(drawn["words"]))
        hits = numbered(drawn["hit"], values)
        submit, fixed = drawn["button"], True
    elif kind == "dropdown_fill_blank":
        hits = [(("field", 0), drawn["field"])] + numbered(drawn["menu"], drawn["options"])
        submit, fixed = drawn["submit"], True
    elif kind == "multi_fill_blanks":
        hits = [(("field", i), rect) for rect, i in drawn["boxes"]]
        submit, fixed = drawn["fixed_submit"], True
    elif kind == "inline_dropdown_fill":
        hits = [(("field", i), rect) for i, rect in drawn["fields"].items()]
        if drawn["opened"] is not None:
            hits += numbered(drawn["menu"], drawn["options"][drawn["opened"]])
        submit, fixed = drawn["submit"], True
    else:
        raise ValueError(kind)
    return hits, submit, page.scroll, page.limit, fixed


def instructions(kind, answer):
    yield "submit", 0  # Incomplete answers must not submit.
    if kind in CHOICE | {"listening_image_choice", "image_multi_choice", "image_underline_choice"}:
        yield "option", answer
    elif kind in TEXT | {"image_write_answer"}:
        yield "field", 0
        yield "text", answer
    elif kind == "order":
        for tile in answer.split():
            yield "option", tile
    elif kind == "matching":
        for left, right in answer.items():
            yield "pair", (0, left)
            yield "pair", (1, right)
    elif kind == "picture_missing_letters":
        yield "letter", 1
        yield "text", answer[1]
    elif kind in GAPS | CHIPS:
        for i, value in enumerate(answer):
            yield "slot", i
            yield "option", value
    elif kind in MULTI_SELECT | {"sentence_underline_words"}:
        # Click in reverse order: the runtime must still return display order.
        for value in reversed(answer):
            yield "option", value
    elif kind == "dropdown_fill_blank":
        yield "field", 0
        yield "option", answer
    elif kind == "multi_fill_blanks":
        for i, value in enumerate(answer):
            yield "field", i
            for letter in value:
                yield "key", letter
    elif kind == "inline_dropdown_fill":
        for i, value in enumerate(answer):
            yield "field", i
            yield "option", value
    else:
        raise ValueError(kind)
    yield "submit", 0


def event(event_type, **fields):
    return pygame.event.Event(event_type, **fields)


class Replay:
    def __init__(self, kind, answer, output, scrolled):
        self.kind = kind
        self.actions = iter(instructions(kind, answer))
        self.action = next(self.actions)
        self.output = output
        self.scrolled = scrolled
        self.steps = []
        self.frames = 0
        self.wheel_sent = False
        self.submit_viewport = {}
        self.presented_hashes = {}
        self.capture_at_flip = None

    def target_position(self, key, rect, scroll, fixed):
        in_passage = self.kind in GAPS and key[0] == "slot"
        offset = 0 if self.kind in GAPS else scroll
        if key[0] == "submit" and fixed:
            offset = 0
        point = rect.move(0, -offset).center
        top, bottom = (210, 495) if in_passage else (0, 640)
        if self.kind in CHOICE | TEXT | {"matching", "order"} and key[0] != "submit":
            top, bottom = 90, 565
        return point, top, bottom

    def screenshot(self, surface, label):
        if self.output is None:
            return None
        path = self.output / f"{self.kind}-{label}.png"
        pygame.image.save(surface, path)
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def present(self, flip):
        flip()
        if self.capture_at_flip:
            label = self.capture_at_flip
            self.presented_hashes[label] = self.screenshot(pygame.display.get_surface(), label)
            self.capture_at_flip = None

    def poll(self):
        self.frames += 1
        if self.frames > 80:
            raise AssertionError(f"renderer never accepted {self.action}: {self.steps}")
        caller = sys._getframe(1)
        if caller.f_code.co_name == "events":
            caller = caller.f_back
        drawn = caller.f_locals
        hits, submit, scroll, limit, fixed = controls(self.kind, drawn)
        # Some renderers flip after polling. Their display surface is already drawn here.
        surface = pygame.display.get_surface()
        self.submit_viewport[scroll] = self.target_position(("submit", 0), submit, scroll, fixed)[0]
        if self.frames == 1 and self.kind == "listening_image_choice":
            return []  # This renderer polls before its first rendered frame.
        if self.scrolled and not self.wheel_sent:
            self.wheel_sent = True
            return [event(pygame.MOUSEWHEEL, x=0, y=-1)]
        if self.action is None:
            raise AssertionError("final click did not submit")
        key = self.action
        label = ("start" if not self.steps else "submit") if key[0] == "submit" else None
        if self.kind in CHIPS and self.output is not None and label and label not in self.presented_hashes:
            # The chip renderer draws the progress badge after polling.
            self.capture_at_flip = label
            return []
        if key[0] in {"text", "key"}:
            if key[0] == "text":
                action_event = event(pygame.TEXTINPUT, text=key[1])
            else:
                action_event = event(pygame.KEYDOWN, key=ord(key[1]), unicode=key[1], mod=0)
            self.steps.append({"action": key, "scroll": scroll})
        else:
            hits.append((("submit", 0), submit))
            found = [pygame.Rect(rect) for name, rect in hits if name == key]
            if not found and key[0] == "option" and self.kind in GAPS:
                destination = next((i for i, group in enumerate(drawn["pages"])
                                    if any(value == key[1] for _, value, _, _ in group)), None)
                if destination is not None and destination != drawn["choice_page"]:
                    direction = 1 if destination > drawn["choice_page"] else -1
                    control = next(rect for name, rect in hits if name == ("page", direction))
                    return [event(pygame.MOUSEBUTTONDOWN, button=1, pos=control.center)]
            if not found and key[0] == "slot" and self.kind in GAPS and scroll:
                return [event(pygame.MOUSEWHEEL, x=0, y=1)]
            if not found:
                raise AssertionError(f"hitbox missing for {key}: {[name for name, _ in hits]}")
            positions = [(rect, *self.target_position(key, rect, scroll, fixed)) for rect in found]
            visible = [(r, p) for r, p, top, bottom in positions if 0 <= p[0] < 960 and top <= p[1] < bottom]
            if not visible:
                _, point, top, bottom = positions[0]
                direction = -1 if point[1] >= bottom else 1
                if limit and ((direction == -1 and scroll < limit) or (direction == 1 and scroll > 0)):
                    return [event(pygame.MOUSEWHEEL, x=0, y=direction)]
                raise AssertionError(f"{key} is outside the viewport at {point}, scroll={scroll}/{limit}")
            rect, point = visible[0]
            self.steps.append({"action": key, "rect": list(rect), "point": point, "scroll": scroll,
                               "frame_hitboxes": [{"action": name, "rect": list(pygame.Rect(r))}
                                                    for name, r in hits]})
            action_event = event(pygame.MOUSEBUTTONDOWN, button=1, pos=point)
        if len(self.steps) == 1:
            self.first_frame = self.presented_hashes.get("start") or self.screenshot(surface, "start")
        self.action = next(self.actions, None)
        if self.action is None:
            self.final_frame = self.presented_hashes.get("submit") or self.screenshot(surface, "submit")
        return [action_event]


def play(original, item, answer, png, scrolled, font_path):
    from tuhoc.exercises.pygame_exercises import _cached_font

    before = deepcopy(item)
    replay = Replay(item["type"], answer, png, scrolled)
    original_state = random.getstate()
    random.seed(2600)
    flip = pygame.display.flip
    try:
        with patch("pygame.display.flip", side_effect=lambda: replay.present(flip)), \
                patch("pygame.event.get", replay.poll), patch("pygame.mouse.get_pos", return_value=(45, 320)), \
                patch("pygame.time.get_ticks", return_value=0), \
                patch("tuhoc.exercises.listening_image_choice.time", SimpleNamespace(monotonic=lambda: replay.frames / 30)), \
                patch("tuhoc.exercises.pygame_exercises._cached_font", side_effect=lambda path, size, bold: _cached_font(font_path, size, bold)):
            result = original(item)
    finally:
        random.setstate(original_state)
        pygame.mixer.music.stop()
        pygame.event.clear()
    assert replay.action is None, f"submitted early or cancelled at {replay.action}"
    assert item == before, "renderer modified fixture"
    assert type(result) is type(answer) and result == answer, (result, answer)
    if isinstance(answer, dict):
        assert list(result.items()) == list(answer.items()), (result, answer)
    moved_clicks = [step for step in replay.steps if step["scroll"] and "rect" in step
                    and step["action"][0] != "submit"
                    and (item["type"] not in GAPS or step["action"][0] == "slot")]
    return {"answer": result, "answer_type": type(result).__name__, "steps": replay.steps,
            "scrolled_input_clicks": len(moved_clicks), "submit_centers_by_scroll": replay.submit_viewport,
            "start_png_sha256": replay.first_frame, "submit_png_sha256": replay.final_frame}


def verify_submission(db, fixture_dir, mode, rows):
    from tuhoc.exercises.pygame_review_panel import show_review
    from tuhoc.lessons.upgrade_v2 import Curriculum, GameAppMixin, LearningService

    class Quiz(GameAppMixin):
        def layout(self, _title):
            return None

        def media_file(self, reference):
            path = fixture_dir / str(reference or "")
            return path if path.is_file() else None

    quiz = Quiz()
    quiz.db = db
    quiz.lang = "en"
    sid = db.add_student(mode, 1)
    quiz.student = {"id": sid}
    quiz.curriculum = Curriculum(fixture_dir)
    quiz.learning = LearningService(db, quiz.curriculum)
    quiz.s_questions = [q for q, _, _, _ in rows]
    quiz.s_answers = []
    quiz.s_combo = quiz.s_xp = 0
    quiz.s_theme, quiz.s_level = "family", 1
    quiz.s_started = time.monotonic()

    with patch("tuhoc.exercises.pygame_exercises.launch", return_value=True) as launch, \
            patch("tuhoc.exercises.pygame_review_panel.show_review", autospec=show_review) as review:
        quiz.session_quiz(0)
        for index, (q, runtime_answer, expected_correct, expected_text) in enumerate(rows):
            assert launch.call_count == index + 1
            _, delivered, on_answer = launch.call_args.args
            assert delivered["id"] == q["id"]
            assert not db.conn.execute("SELECT 1 FROM attempts WHERE student_id=?", (sid,)).fetchone()
            on_answer(runtime_answer)
            question, answer, correct = quiz.s_answers[-1]
            assert question == q and type(answer) is type(runtime_answer)
            assert (answer, correct, quiz._quiz_answer_text(q, answer)) == (
                runtime_answer, expected_correct, expected_text)
        assert quiz._quiz_saved and review.call_count == 1
        quiz.session_finish()
        assert quiz._draft_store().load(*quiz._draft_key()) is None
    query = """SELECT exercise_id,exercise_type,content_version,correct,answer,typeof(answer),seconds
               FROM attempts WHERE student_id=? ORDER BY id"""
    stored = [tuple(r) for r in db.conn.execute(query, (sid,))]
    assert [row[:-1] for row in stored] == [(q["id"], q["type"], "2.0", int(correct), answer, "text")
                                            for q, _, correct, answer in rows]
    assert all(row[-1] >= 0 for row in stored)
    assert db.conn.execute("SELECT COUNT(*) FROM learning_sessions WHERE student_id=?", (sid,)).fetchone()[0] == 1
    return [list(row[:-1]) for row in stored]


def verify_exam(directory, db):
    from tuhoc.exams.exam_grading import is_correct
    from tuhoc.exams.exam_history_bridge import exam_detail, exam_records
    from tuhoc.exams.exam_pygame import ExamUI

    examples = (
        ({"type": "choice", "answer": "cat"}, "  CAT ", "dog", None),
        ({"type": "sentence_gaps", "gap_answers": ["cat", "dog"]}, ["CAT", "dog"], ["dog", "cat"], None),
        ({"type": "matching", "pairs": [["cat", "mèo"], ["dog", "chó"]]},
         {"cat": "mèo", "dog": "chó"}, {"cat": "mèo"}, None),
        ({"type": "order", "sequence": ["I", "read", "books"]}, None, None, ["I", "read", "books"]),
        ({"type": "error", "corrected": "goes"}, "goes", "go", None),
    )
    sid = db.add_student("P0 exam learner", 1)
    exam = ExamUI(directory, sid)
    exam.mode, exam.grade, exam.lesson = "confirm", "1", "Sample"
    exam.exam = {"id": "p0-exam", "questions": []}
    for i, (fields, correct, wrong, order) in enumerate(examples):
        for variant, answer, sequence in (("correct", correct, order),
                                          ("wrong", wrong, order[::-1] if order else None)):
            key = f"{i}-{variant}"
            q = {"id": key, **fields}
            assert is_correct(q, answer, sequence) == (variant == "correct")
            exam.exam["questions"].append(q)
            exam.answers[key] = answer
            if sequence:
                exam.order_inputs[key] = sequence
    exam._submit()
    exam._submit()
    assert exam.error is None and exam.mode == "result"
    assert exam.result["correct"] == len(examples)
    assert len(exam_records(db.conn, sid)) == 1
    assert exam_detail(db.conn, sid, "p0-exam") == exam.result
    assert db.conn.execute("SELECT COUNT(*) FROM attempts WHERE student_id=?", (sid,)).fetchone()[0] == 0
    return {"correct": exam.result["correct"], "total": exam.result["total"],
            "json_results": 1, "sqlite_attempts": 0, "graded_answers": exam.result["graded_answers"]}


def persisted(answer, kind):
    if kind == "matching":
        labels = ("cat", "dog"), ("mèo", "chó")
        return " | ".join(f"{labels[0][i]} → {labels[1][j]}" for i, j in sorted(answer.items()))
    if kind == "sentence_underline_words":
        return " | ".join(("cat", "or", "dog")[i] for i in answer)
    if isinstance(answer, list):
        return " | ".join(answer)
    return answer


def run(output, font_path, only, layout_format):
    import main
    import tuhoc.exercises.pygame_exercises as pygame_exercises
    from tuhoc.lessons.level_flow import QUESTION_TYPES
    from tuhoc.lessons.upgrade_v2 import GameAppMixin

    pygame.init()
    fixture_dir = output / "fixtures"
    fixture_dir.mkdir()
    fixtures = list(cases(fixture_dir))
    assert len(fixtures) == 26
    assert {c.kind for c in fixtures} == set(QUESTION_TYPES) == pygame_exercises.SUPPORTED
    if only:
        fixtures = [c for c in fixtures if c.kind in only]
        assert len(fixtures) == len(only)
    for mode in ("default", "scroll"):
        (output / mode).mkdir()
    results = {}
    rows = {}
    failures = []
    try:
        for case in fixtures:
            detail = {}
            results[case.kind] = detail
            quiz = GameAppMixin()
            for label, answer, expected in (("right", case.right, True), ("wrong", case.wrong, False),
                                             ("boundary", case.boundary, case.boundary_correct)):
                assert quiz._quiz_correct(case.question, answer) is expected, (case.kind, label)
            detail["grading"] = {"right": True, "wrong": False, "boundary": case.boundary,
                                 "boundary_correct": case.boundary_correct}
            for mode in ("default", "scroll"):
                q = deepcopy(case.question)
                if mode == "scroll":
                    from tuhoc.studio.question_layout_store import layout_v2, layout_v3, set_layout
                    layout = legacy_layout(case)
                    if layout_format == "migrated":
                        layout = layout_v2(layout)
                    elif layout_format in {"authored", "v3", "v4"}:
                        layout = authored_layout(case)
                        if layout_format in {"v3", "v4"}:
                            layout = layout_v3(layout)
                            layout["extras"] = [dict(
                                id="matrix_text", kind="text", text="Tiếng Việt",
                                desktop=dict(x=12,y=660,width=110,height=42),
                                font_size=16,bold=True,italic=False,color="#223344",bg="#eeeeee",
                                align="center",z=0)]
                        if layout_format == "v4":
                            layout["version"] = 4
                            prompt = layout["desktop"].setdefault("question_text", {})
                            prompt.update(font_family="DejaVu Sans", italic=True, underline=True,
                                          runs=[dict(start=0, end=3, bold=True)])
                            layout["extras"][0]["underline"] = True
                            if case.kind == 'multi_fill_blanks':
                                layout['desktop']['slot_0'] = dict(x=245,y=409,width=114,height=48)
                            if case.kind == 'picture_missing_letters':
                                layout['desktop']['slot_1'] = dict(x=226,y=415,width=64,height=55)

                    q = set_layout(q, layout)
                for variant, answer in (("right", case.right), ("wrong", case.wrong)):
                    key = f"{mode}/{variant}"
                    png = output / mode if variant == "right" else None
                    try:
                        detail[key] = play(pygame_exercises._run, q, answer, png, mode == "scroll", font_path)
                        runtime_answer = detail[key]["answer"]
                        if mode == "scroll":
                            if layout_format in {"authored", "v3", "v4"} or case.kind != "listening_image_choice":
                                assert detail[key]["scrolled_input_clicks"], "no answer hitbox received a scrolled click"
                            centers = detail[key]["submit_centers_by_scroll"].values()
                            assert len(set(centers)) == 1, "completion control moved while scrolling"
                        rows.setdefault(key, []).append((q, runtime_answer, variant == "right", persisted(answer, case.kind)))
                    except (AssertionError, KeyError, ValueError, pygame.error) as exc:
                        detail[key] = {"error": str(exc)}
                        failures.append(f"{case.kind} {key}: {exc}")
            print(f"{case.kind}: " + ", ".join(f"{k}={'error' if 'error' in v else 'ok'}" for k, v in detail.items()
                                               if k != "grading"), flush=True)
        attempts = {}
        with TemporaryDirectory(prefix="tuhoc-p0-sqlite-") as directory:
            db = main.Storage(Path(directory) / "attempts.sqlite3")
            try:
                for key, answers in rows.items():
                    attempts[key] = verify_submission(db, fixture_dir, key, answers)
                exam = verify_exam(directory, db)
            finally:
                db.conn.close()
        metadata = {"pygame": pygame.version.ver, "sdl": pygame.get_sdl_version(), "python": sys.version,
                    "driver": pygame.display.get_driver(), "font": font_path,
                    "font_sha256": hashlib.sha256(Path(font_path).read_bytes()).hexdigest(), "seed": 2600}
        (output / "baseline.json").write_text(json.dumps({"metadata": metadata, "types": results,
            "attempts": attempts, "exam": exam, "failures": failures}, ensure_ascii=False, indent=2), encoding="utf-8")
    finally:
        pygame.quit()
    for failure in failures:
        print(failure, file=sys.stderr)
    return bool(failures)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--font", default="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    parser.add_argument("--type", action="append", default=[])
    parser.add_argument("--layout", choices=("legacy", "migrated", "authored", "v3", "v4"), default="legacy")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    with TemporaryDirectory(prefix="tuhoc-p0-profile-") as directory:
        with patch.dict(os.environ, {"LOCALAPPDATA": directory}):
            return run(args.output, args.font, args.type, args.layout)


if __name__ == "__main__":
    raise SystemExit(main())
