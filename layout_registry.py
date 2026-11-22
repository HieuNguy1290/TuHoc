"""System geometry exposed by the lesson renderers, grouped by exercise type."""
from dataclasses import dataclass


@dataclass(frozen=True)
class LayoutControls:
    runtime: str
    editable: tuple[str, ...]
    runtime_reads_layout: bool = True

    def properties_for(self, element, kind):
        fields = {'x', 'y', 'width', 'height'}
        if element == 'question_image':
            return fields | {'image_fit'}
        if element in {'audio_player', 'answer_panel'}:
            return fields
        if self.runtime == 'new_exercise_runtime' and kind == 'picture_missing_letters' and element == 'option_0':
            fields -= {'x', 'y'}
        fields |= {'font_family', 'font_size', 'bold', 'italic', 'underline'}
        if element in {'question_text', 'answer_passage'}:
            fields |= {'align', 'line_spacing', 'runs'}
        return fields


DEFAULTS = {
    'question_text': dict(x=.06, y=.12, width=.88, height=.15, font_size=24),
    'question_image': dict(x=.31, y=.31, width=.38, height=.28),
    'audio_player': dict(x=.08, y=.64, width=.84, height=.09),
    'answer_area': dict(x=.10, y=.76, width=.80, height=.15),
    'input_area': dict(x=.08, y=.68, width=.82, height=.10),
    'dropdown_area': dict(x=.18, y=.58, width=.36, height=.08),
    'answer_preview': dict(x=.07, y=.45, width=.84, height=.10),
    'answer_menu': dict(x=.18, y=.67, width=.36, height=.25),
    'answer_panel': dict(x=.50, y=.04, width=.48, height=.51),
    'answer_passage': dict(x=.06, y=.31, width=.86, height=.25),
    'word_bank': dict(x=.07, y=.79, width=.85, height=.055),
}

LEGACY = 'pygame_exercises'
LEGACY_COMMON = ('question_text', 'question_image')
BANK = ('question_text', 'answer_area', 'question_image', 'audio_player', 'word_bank', 'slot_N', 'word_N')
CHIPS = ('question_text', 'answer_area', 'question_image', 'audio_player', 'option_N', 'slot_N')

REGISTRY = {
    **{kind: LayoutControls(LEGACY, (*LEGACY_COMMON, 'answer_area', 'option_N'))
       for kind in ('choice', 'picture_choice', 'true_false', 'matching')},
    'order': LayoutControls(LEGACY, (*LEGACY_COMMON, 'answer_area', 'answer_preview', 'option_N')),
    'listening_choice': LayoutControls(LEGACY, (*LEGACY_COMMON, 'audio_player', 'answer_area', 'option_N')),
    'listening_fill': LayoutControls(LEGACY, (*LEGACY_COMMON, 'audio_player', 'input_area')),
    **{kind: LayoutControls(LEGACY, (*LEGACY_COMMON, 'input_area'))
       for kind in ('fill', 'error')},
    'listening_image_choice': LayoutControls('listening_image_choice', ('question_text', 'question_image', 'audio_player', 'option_N')),
    'image_multi_choice': LayoutControls('new_exercise_runtime', ('question_text', 'question_image', 'audio_player', 'option_N')),
    'picture_missing_letters': LayoutControls('new_exercise_runtime', ('question_text', 'question_image', 'audio_player', 'answer_area', 'option_N', 'slot_N')),
    **{kind: LayoutControls('new_exercise_runtime', BANK)
       for kind in ('sentence_gaps','passage_gaps','conversation_gaps')},
    'image_multi_select': LayoutControls('multi_select_extension', (*LEGACY_COMMON, 'answer_area', 'option_N')),
    'text_multi_select': LayoutControls('multi_select_extension', (*LEGACY_COMMON, 'answer_passage', 'answer_area', 'option_N')),
    'audio_multi_select': LayoutControls('multi_select_extension', (*LEGACY_COMMON, 'audio_player', 'answer_area', 'option_N')),
    'image_write_answer': LayoutControls('image_write_extension', (*LEGACY_COMMON, 'input_area')),
    'image_underline_choice': LayoutControls('underline_extension', (*LEGACY_COMMON, 'answer_area', 'option_N')),
    'sentence_underline_words': LayoutControls('underline_extension', ('question_text', 'answer_area', 'option_N')),
    'dropdown_fill_blank': LayoutControls('dropdown_extension', (*LEGACY_COMMON, 'dropdown_area', 'answer_menu', 'option_N')),
    'inline_dropdown_fill': LayoutControls('inline_dropdown_extension', (*LEGACY_COMMON, 'dropdown_area', 'answer_menu', 'slot_N')),
    'multi_fill_blanks': LayoutControls('multi_fill_blanks_extension', (*LEGACY_COMMON, 'audio_player', 'answer_area', 'slot_N')),
    'image_sentence_fill': LayoutControls('image_sentence_extension', CHIPS),
    'image_letter_pick': LayoutControls('image_sentence_extension', CHIPS),
}


def controls_for(kind, context='lesson'):
    if context == 'exam':
        if kind == 'reading_group':
            return LayoutControls('exam_pygame', ('answer_passage', 'answer_panel'))
        common = (*LEGACY_COMMON, 'audio_player')
        if kind in {'fill', 'error', 'listening_fill', 'picture_missing_letters'}:
            return LayoutControls('exam_pygame', (*common, 'input_area'))
        if kind in {'sentence_gaps', 'passage_gaps', 'conversation_gaps'}:
            return LayoutControls('exam_pygame', (*common, 'answer_area', 'slot_N'))
        if kind == 'order':
            return LayoutControls('exam_pygame', (*common, 'answer_area', 'answer_preview', 'option_N'))
        if kind in {'choice', 'true_false'}:
            return LayoutControls('exam_pygame', (*common, 'answer_passage', 'answer_area', 'option_N'))
        if kind in REGISTRY:
            return LayoutControls('exam_pygame', (*common, 'answer_area', 'option_N'))
    return REGISTRY.get(kind, LayoutControls('', (), False))
