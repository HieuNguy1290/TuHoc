"""Display label for picture questions that intentionally leave the prompt empty."""

OPTIONAL_PROMPT = 'picture_missing_letters'


def display_prompt(question, default=''):
    prompt = question.get('prompt')
    if question.get('type') == OPTIONAL_PROMPT and not str(prompt or '').strip():
        return 'Nhìn hình và điền chữ còn thiếu'
    return default if prompt is None else prompt
