"""Verify the actual SDL preview transport using temporary exercise fixtures."""
from pathlib import Path
import random
import time

from canvas_p0_cases import cases
from tuhoc.studio.studio_live_preview import LivePreview


def next_message(preview, revision, message):
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        for kind, payload in preview.read():
            if payload[0] != revision:
                continue
            assert kind != 'error', payload[1]
            if kind == message:
                return payload
        time.sleep(.02)
    raise AssertionError(f'Preview revision {revision} did not deliver {message}')


def next_frame(preview, revision):
    return next_message(preview, revision, 'frame')


def test_each_lesson_renderer_exposes_a_real_frame(tmp_path, monkeypatch):
    monkeypatch.setenv('SDL_AUDIODRIVER', 'dummy')
    for case in cases(Path(tmp_path)):
        preview = LivePreview(case.question)
        try:
            preview.send('layout', (1, {}, True, None))
            _, size, pixels, regions, _, _ = next_frame(preview, 1)
            assert size == (960, 640), case.kind
            assert len(pixels) == 3 * size[0] * size[1], case.kind
            assert 'question_text' in regions and len(regions) > 1, (case.kind, regions)
            layout = {'version': 4, 'desktop': {'question_text': {
                'x': 30, 'y': 72, 'width': 550, 'height': 70, 'font_size': 19}}}
            preview.send('layout', (2, layout, True, None))
            _, _, adjusted, boxes, _, _ = next_frame(preview, 2)
            assert boxes['question_text'][0] == (30, 72, 550, 70), case.kind
            assert pixels != adjusted, case.kind
        finally:
            preview.close()


def test_choice_geometry_and_practice_click_use_the_same_box(monkeypatch):
    monkeypatch.setenv('SDL_AUDIODRIVER', 'dummy')
    preview = LivePreview(dict(type='choice', prompt='Choose the odd one out:', options=['Dog', 'Kite', 'Cat', 'Bird']))
    try:
        preview.send('layout', (1, {}, True, None))
        _, _, _, regions, _, _ = next_frame(preview, 1)
        assert len([key for key in regions if key.startswith('option_')]) == 4
        layout = {'version': 4, 'desktop': {'option_1': {'x': 90, 'y': 780, 'width': 300, 'height': 40}}}
        preview.send('layout', (2, layout, True, None))
        next_frame(preview, 2)
        preview.send('input', ('wheel', -5))
        _, _, before, regions, scroll, _ = next_frame(preview, 2)
        document, screen = regions['option_1']
        assert document == (90, 780, 300, 40)
        assert scroll > 100
        assert screen[1] == document[1] - scroll
        x, y, w, h = screen
        preview.send('input', ('click', (x+w//2, y+h//2)))
        _, _, selected, _, _, _ = next_frame(preview, 2)
        assert before != selected
        preview.send('input', ('key', 'return'))
        _, answer = next_message(preview, 2, 'finished')
        visible_order = ['Dog', 'Kite', 'Cat', 'Bird']
        random.Random(9731).shuffle(visible_order)
        assert answer == visible_order[1]
    finally:
        preview.close()


def test_page_thumb_can_be_dragged_outside_track(tmp_path, monkeypatch):
    monkeypatch.setenv('SDL_AUDIODRIVER', 'dummy')
    case = next(case for case in cases(tmp_path) if case.kind == 'image_write_answer')
    layout = {'version': 4, 'desktop': {'input_area': {'x': 60, 'y': 900, 'width': 600, 'height': 50}}}
    preview = LivePreview(case.question)
    try:
        preview.send('layout', (1, layout, True, None))
        _, _, _, regions, _, limit = next_frame(preview, 1)
        x, y, width, height = regions['_scrollbar'][1]
        preview.send('input', ('click', (x+width//2, y+6)))
        next_frame(preview, 1)
        preview.send('input', ('motion', (x-180, y+height+60)))
        _, _, _, _, scroll, _ = next_frame(preview, 1)
        assert scroll == limit
        preview.send('input', ('release', (x-180, y+height+60)))
        next_frame(preview, 1)
        preview.send('input', ('motion', (x-180, y)))
        assert next_frame(preview, 1)[4] == limit
    finally:
        preview.close()


def test_exam_groups_and_children_use_their_own_viewports(tmp_path, monkeypatch):
    monkeypatch.setenv('SDL_AUDIODRIVER', 'dummy')
    context = dict(_layout_context='exam', _preview_root=str(tmp_path))
    children = [dict(prompt='Chọn phương án', options=['a', 'b']),
                dict(prompt='Câu thứ hai', options=['c', 'd'])]
    group = dict(type='reading_group', prompt='Bài đọc', passage='Một con mèo.', questions=children)
    for question in ({**group, **context}, {**context, **children[1], 'type': 'choice',
                                           '_preview_group': group, '_preview_child_index': 1}):
        preview = LivePreview(question)
        try:
            preview.send('layout', (1, {}, True, None))
            _, size, _, regions, _, _ = next_frame(preview, 1)
            if question['type'] == 'reading_group':
                assert size == (694, 331)
                assert {'answer_passage', 'answer_panel'} <= regions.keys()
            else:
                assert 0 < size[0] < 694
                assert {'question_text', 'option_0', 'option_1'} <= regions.keys()
        finally:
            preview.close()



def test_dropdown_renders_the_editable_menu_only_after_it_opens(tmp_path, monkeypatch):
    monkeypatch.setenv('SDL_AUDIODRIVER', 'dummy')
    for case in cases(tmp_path):
        if case.kind not in ('dropdown_fill_blank', 'inline_dropdown_fill'):
            continue
        preview = LivePreview(case.question)
        try:
            preview.send('layout', (1, {}, True, None))
            _, _, closed, regions, _, _ = next_frame(preview, 1)
            assert 'answer_menu' not in regions
            key = 'slot_0' if case.kind == 'inline_dropdown_fill' else 'dropdown_area'
            _, (x,y,width,height) = regions[key]
            preview.send('input', ('click', (x+width//2,y+height//2)))
            _, _, opened, regions, _, _ = next_frame(preview, 1)
            assert 'answer_menu' in regions and closed != opened
        finally:
            preview.close()
