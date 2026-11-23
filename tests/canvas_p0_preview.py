"""Exercise editor preview through Tk and the real SDL worker on a Linux display."""
import argparse
from copy import deepcopy
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import time
import tkinter as tk
from tkinter import ttk
from unittest.mock import patch

from canvas_p0 import play


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


def verify(directory, feedback_enabled):
    import tuhoc.exercises.pygame_exercises as pygame_exercises
    import tuhoc.lessons.unified_subjects as unified_subjects
    from tuhoc.lessons.level_flow import library_file, save_rows
    from main import App

    source = {"id": "p0-preview", "type": "fill", "prompt": "Câu mẫu",
              "theme": "Family & Friends", "level": 1, "lesson": 1, "answer": "cat"}
    staged = {"answer_area": {"x": .18, "y": .65, "width": .5, "height": .08}}
    prepare = unified_subjects.prepare_subject

    def prepare_fixture(_root, language, bundle, legacy_root=None):
        subject = prepare(directory, language, bundle, legacy_root)
        save_rows(subject, "questions", [source])
        return subject

    class PreviewApp(App):
        def layout(self, _title):
            return tk.Frame(self)

    with patch("tuhoc.lessons.unified_subjects.prepare_subject", side_effect=prepare_fixture):
        app = PreviewApp()
    app._display_settings["dragon_feedback_enabled"] = feedback_enabled
    app.student = {"id": app.db.add_student("P0 preview learner", 1)}
    def report_error(_kind, error, tb):
        raise error.with_traceback(tb)

    app.report_callback_exception = report_error
    saved_path = library_file(app.curriculum.data_dir, "questions")
    saved_bytes = saved_path.read_bytes()
    saved_rows = deepcopy(app.curriculum.rows["questions"])
    launch, render = pygame_exercises.launch, pygame_exercises._run
    completed = []
    frames = []

    def capture_launch(parent, question, on_answer, *args, **kwargs):
        assert question["layout"] == staged and question["answer"] == "cat"
        assert question["prompt"] == "Bản nháp P0"

        def complete(answer):
            on_answer(answer)
            completed.append(answer)
        def frame(size, pixels):
            frames.append((size, len(pixels), len(set(pixels))))

        kwargs['on_frame'] = frame
        return launch(parent, question, complete, *args, **kwargs)

    def replay(question):
        return play(render, question, "cat", None, False,
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")["answer"]

    def button(text):
        return next(w for w in descendants(app) if isinstance(w, tk.Button) and w.cget("text") == text)

    def counts():
        return {table: app.db.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in ("attempts", "learning_sessions", "completion_events", "level_scores")}

    try:
        before = counts()
        exam_history = app.data_dir / "content_library" / "exam_results.json"
        assert not exam_history.exists()
        app.question_editor()
        tree = next(w for w in descendants(app) if isinstance(w, ttk.Treeview))
        tree.selection_set(tree.get_children()[0])
        button("Sửa dòng chọn").invoke()
        # Edit the question prompt and stage a layout through the editor's action.
        prompt = next(w for w in descendants(app) if isinstance(w, tk.Text))
        prompt.delete("1.0", "end")
        prompt.insert("1.0", "Bản nháp P0")
        with patch("tuhoc.studio.question_layout_editor.edit_layout", return_value=staged):
            button("↔ Chỉnh bố cục").invoke()
        with patch("tuhoc.exercises.pygame_exercises.launch", side_effect=capture_launch), \
                patch("tuhoc.exercises.pygame_exercises._run", side_effect=replay), \
                patch.object(app, "_quiz_correct", wraps=app._quiz_correct) as grade:
            button("👁 Xem trước").invoke()
            end = time.monotonic() + 8
            while not completed and time.monotonic() < end:
                app.update()
                time.sleep(.01)
            assert completed == ["cat"], completed
            assert len(frames) == 1, frames
            size, byte_count, colors = frames[0]
            assert size == (960, 640) and byte_count == 960 * 640 * 3 and colors > 10
            grade_calls = grade.call_count
        assert before == counts() == dict.fromkeys(before, 0)
        assert saved_path.read_bytes() == saved_bytes and app.curriculum.rows["questions"] == saved_rows
        assert not exam_history.exists()
        print(f"Preview feedback={feedback_enabled}, answer={completed[0]}, "
              f"grading calls={grade_calls}, submissions=0, result rows=0, fixture bytes unchanged")
        assert grade_calls == 0, "preview must bypass grading even when feedback is enabled"
    finally:
        app._shutdown_app()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feedback", action="store_true")
    args = parser.parse_args()
    with TemporaryDirectory(prefix="tuhoc-p0-preview-") as directory:
        with patch.dict(os.environ, {"LOCALAPPDATA": directory}):
            verify(Path(directory), args.feedback)


if __name__ == "__main__":
    main()
