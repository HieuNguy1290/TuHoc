"""Optional starting layouts grouped by the renderer's input controls."""
INPUTS = frozenset({'fill', 'error', 'listening_fill', 'image_write_answer'})
MENUS = frozenset({'dropdown_fill_blank', 'inline_dropdown_fill'})
TOKENS = frozenset({'picture_missing_letters', 'sentence_gaps', 'passage_gaps',
                    'conversation_gaps', 'image_letter_pick', 'image_sentence_fill'})


def template_for(kind):
    """Return fresh desktop pixel overrides for a new draft."""
    elements = {'question_text': {'x': 58, 'y': 104, 'width': 844, 'height': 96}}
    if kind in INPUTS:
        elements['input_area'] = {'x': 72, 'y': 352, 'width': 816, 'height': 55}
    elif kind in MENUS:
        elements['dropdown_area'] = {'x': 173, 'y': 304, 'width': 346, 'height': 48}
    elif kind in TOKENS:
        elements['answer_area'] = {'x': 65, 'y': 265, 'width': 810, 'height': 165}
        if kind in {'sentence_gaps', 'passage_gaps', 'conversation_gaps'}:
            elements['word_bank'] = {'x': 65, 'y': 505, 'width': 825, 'height': 35}
    else:
        elements['answer_area'] = {'x': 65, 'y': 240, 'width': 810, 'height': 170}
    return {'version': 2, 'desktop': elements}
