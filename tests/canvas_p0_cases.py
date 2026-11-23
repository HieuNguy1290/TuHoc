"""Synthetic fixtures and explicit answer expectations for the lesson canvas."""
from dataclasses import dataclass
from pathlib import Path
import wave

from PIL import Image
from PIL import ImageDraw


@dataclass
class Case:
    question: dict
    right: object
    wrong: object
    boundary: object
    boundary_correct: bool = False

    @property
    def kind(self):
        return self.question["type"]


def cases(directory):
    refs = ["red.png", "blue.png", "green.png"]
    images = {}
    for color, ref in zip(("red", "blue", "green"), refs):
        path = directory / ref
        image = Image.new("RGB", (160, 96), color)
        ImageDraw.Draw(image).ellipse((44, 12, 116, 84), fill="white")
        image.save(path)
        images[ref] = str(path)
    audio = directory / "silence.wav"
    with wave.open(str(audio), "wb") as wav:
        wav.setparams((1, 2, 8000, 0, "NONE", "not compressed"))
        wav.writeframes(bytes(8000))

    def case(kind, right, wrong, boundary, boundary_correct=False, **fields):
        q = {"id": kind, "type": kind, "prompt": "Bài tập mẫu", "answer": right,
             "_index": 1, "_total": 26, **fields}
        return Case(q, right, wrong, boundary, boundary_correct)

    audio_fields = {"audio": audio.name, "_resolved_audio": str(audio),
                    "_pygame_audio": str(audio)}
    picture_fields = {"image": refs[0], "_pygame_image": images[refs[0]]}
    choice_fields = {"options": ["cat", "dog"]}
    yield case("choice", "cat", "dog", " CAT ", True, **choice_fields)
    yield case("picture_choice", "cat", "dog", "", **choice_fields, **picture_fields)
    yield case("true_false", "Đúng", "Sai", "", options=["Đúng", "Sai"])
    yield case("listening_choice", "cat", "dog", "", **choice_fields, **audio_fields)
    for kind in ("fill", "listening_fill", "error"):
        yield case(kind, "cà phê", "trà", "  CÀ PHÊ  ", True,
                   **(audio_fields if kind == "listening_fill" else {}))
    yield case("order", "I read books", "books read I", "I|read|books", True,
               options=["I", "read", "books"], answer="I|read|books")
    yield case("matching", {0: 0, 1: 1}, {0: 1, 1: 0}, {0: 0},
               options=["cat = mèo", "dog = chó"], answer="cat = mèo | dog = chó")
    image_options = [{"image": ref, "label": ref.split(".")[0]} for ref in refs[:2]]
    yield case("listening_image_choice", refs[0], refs[1], "", image_options=image_options,
               _choice_images=images, **audio_fields)
    yield case("image_multi_choice", refs[0], refs[1], "", image_options=image_options,
               _choice_images=images)
    yield case("picture_missing_letters", "CAT", "COT", "cat", True, hidden_indices=[1],
               **picture_fields)
    for kind in ("sentence_gaps", "passage_gaps", "conversation_gaps"):
        # Long tail gives the passage a real scroll range while the first row remains
        # actionable after a wheel step. Move the blanks below the clipping edge.
        words = " ".join(["Chúng ta cùng đọc."] * 30).split()
        words[17:19] = ["cat", "dog"]
        text = " ".join(words)
        fields = {"dialogue": [{"text": text, "hidden_indices": [17, 18]}]} if kind == "conversation_gaps" else {
            "source_text": text, "hidden_indices": [17, 18]}
        yield case(kind, ["cat", "dog"], ["bird", "fish"], ["cat"],
                   answer="cat | dog", distractors=["bird", "fish"], **fields)
    for kind in ("image_multi_select", "text_multi_select", "audio_multi_select"):
        fields = picture_fields if kind == "image_multi_select" else audio_fields if kind == "audio_multi_select" else {}
        yield case(kind, ["cat", "dog"], ["dog", "bird"], ["dog", "cat"], True,
                   answer="cat | dog", answers=["cat", "dog"], options=["cat", "dog", "bird"], **fields)
    yield case("image_write_answer", "cà phê", "trà", "  CÀ   PHÊ  ", True, **picture_fields)
    yield case("image_underline_choice", "cat", "dog", [], options=["cat", "dog"], **picture_fields)
    yield case("sentence_underline_words", [0, 2], [1, 2], [2, 0, 0], True,
               answer="cat | dog", source_text="cat or dog", correct_word_indices=[0, 2])
    yield case("dropdown_fill_blank", "cat", "dog", " cat ", True, **choice_fields)
    yield case("multi_fill_blanks", ["cat", "dog"], ["dog", "cat"], [" CAT ", " DOG "], True,
               answer="cat | dog", blank_text="a [[1]] and a [[2]]", blank_answers=["cat", "dog"])
    for kind, valid, invalid in (("image_sentence_fill", ["cat", "dog"], ["dog", "cat"]),
                                 ("image_letter_pick", ["a", "o"], ["o", "a"])):
        yield case(kind, valid, invalid, valid[:1], answer=" | ".join(valid),
                   blank_text="c....t and d....g", blank_answers=valid, **picture_fields)
    yield case("inline_dropdown_fill", ["cat", "dog"], ["dog", "cat"], ["cat"],
               answer="cat | dog", blank_text="a .... and a ....", blank_answers=["cat", "dog"],
               blank_options=[["dog", "cat"], ["cat", "dog"]])


def legacy_layout(case):
    """Scroll fixture in the editor's current normalized coordinate format."""
    kind = case.kind
    if kind == "image_multi_choice":
        return {"option_0": {"x": .08, "y": .60}, "option_1": {"x": .4, "y": .88}}
    if kind == "picture_missing_letters":
        return {"answer_area": {"x": .07, "y": .92}}
    if kind in ("image_letter_pick", "image_sentence_fill"):
        return {"option_1": {"x": .4, "y": .99}}
    if kind in ("sentence_gaps", "passage_gaps", "conversation_gaps", "listening_image_choice"):
        return {}
    return {"question_image": {"y": 1.05, "height": .10}}


def authored_layout(case):
    """Use v2 element overrides that each renderer consumes while answering."""
    from tuhoc.studio.question_layout_store import layout_v2

    layout = layout_v2(legacy_layout(case))
    desktop = layout['desktop']
    kind = case.kind
    if kind == 'listening_image_choice':
        desktop.update({'option_0': {'x': 75, 'y': 330, 'width': 310, 'height': 125},
                        'option_1': {'x': 475, 'y': 658, 'width': 310, 'height': 125}})
    elif kind in {'choice', 'picture_choice', 'true_false', 'listening_choice', 'order', 'matching'}:
        desktop['answer_area'] = {'x': 86, 'y': 328, 'width': 790}
    elif kind in {'fill', 'error', 'listening_fill', 'image_write_answer'}:
        desktop['input_area'] = {'x': 81, 'y': 481, 'width': 720, 'height': 48}
    elif kind in {'sentence_gaps', 'passage_gaps', 'conversation_gaps'}:
        desktop['word_bank'] = {'x': 76, 'y': 500, 'width': 780, 'height': 35}
    elif kind in {'image_multi_select', 'text_multi_select', 'audio_multi_select'}:
        desktop['option_0'] = {'x': 67, 'y': 603, 'width': 380, 'height': 50}
    elif kind in {'image_underline_choice', 'sentence_underline_words', 'multi_fill_blanks'}:
        desktop['answer_area'] = {'x': 81, 'y': 388, 'width': 810}
    elif kind in {'dropdown_fill_blank', 'inline_dropdown_fill'}:
        desktop['dropdown_area'] = {'x': 145, 'y': 395, 'width': 430}
    return layout
