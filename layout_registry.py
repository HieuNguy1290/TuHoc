"""System geometry exposed by the lesson renderers, grouped by exercise type."""
from dataclasses import dataclass


@dataclass(frozen=True)
class LayoutControls:
    runtime: str
    editable: tuple[str, ...]
    runtime_reads_layout: bool = True


DEFAULTS = {
    'question_text': dict(x=.06, y=.12, width=.88, height=.15, font_size=24),
    'question_image': dict(x=.31, y=.31, width=.38, height=.28),
    'audio_player': dict(x=.08, y=.64, width=.84, height=.09),
    'answer_area': dict(x=.10, y=.76, width=.80, height=.15),
    'input_area': dict(x=.08, y=.68, width=.82, height=.10),
    'dropdown_area': dict(x=.18, y=.58, width=.36, height=.08),
    'word_bank': dict(x=.07, y=.79, width=.85, height=.055),
}

LEGACY = 'pygame_exercises'
LEGACY_COMMON = ('question_text', 'question_image')
BANK = ('answer_area', 'question_image', 'audio_player', 'word_bank')
CHIPS = ('answer_area', 'question_image', 'option_N')

REGISTRY = {
    **{kind: LayoutControls(LEGACY, (*LEGACY_COMMON, 'answer_area', 'option_N'))
       for kind in ('choice', 'picture_choice', 'true_false', 'order', 'matching')},
    'listening_choice': LayoutControls(LEGACY, (*LEGACY_COMMON, 'audio_player', 'answer_area', 'option_N')),
    'listening_fill': LayoutControls(LEGACY, (*LEGACY_COMMON, 'audio_player', 'input_area', 'answer_area')),
    **{kind: LayoutControls(LEGACY, (*LEGACY_COMMON, 'input_area', 'answer_area'))
       for kind in ('fill', 'error')},
    'listening_image_choice': LayoutControls('listening_image_choice', ('question_image', 'option_N')),
    'image_multi_choice': LayoutControls('new_exercise_runtime', ('question_image', 'audio_player', 'option_N')),
    'picture_missing_letters': LayoutControls('new_exercise_runtime', ('question_image', 'audio_player', 'answer_area', 'option_N')),
    **{kind: LayoutControls('new_exercise_runtime', BANK)
       for kind in ('sentence_gaps','passage_gaps','conversation_gaps')},
    **{kind: LayoutControls('multi_select_extension', ('option_N',))
       for kind in ('image_multi_select', 'text_multi_select', 'audio_multi_select')},
    'image_write_answer': LayoutControls('image_write_extension', (*LEGACY_COMMON, 'input_area', 'answer_area')),
    'image_underline_choice': LayoutControls('underline_extension', ('answer_area', 'option_N')),
    'sentence_underline_words': LayoutControls('underline_extension', ('answer_area',)),
    'dropdown_fill_blank': LayoutControls('dropdown_extension', ('dropdown_area', 'answer_area')),
    'inline_dropdown_fill': LayoutControls('inline_dropdown_extension', ('question_image', 'dropdown_area', 'answer_area')),
    'multi_fill_blanks': LayoutControls('multi_fill_blanks_extension', (*LEGACY_COMMON, 'audio_player', 'answer_area')),
    'image_sentence_fill': LayoutControls('image_sentence_extension', CHIPS),
    'image_letter_pick': LayoutControls('image_sentence_extension', CHIPS),
}


def controls_for(kind):
    return REGISTRY.get(kind, LayoutControls('', (), False))
