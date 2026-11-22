"""Optional inline dropdown syntax for dropdown_fill_blank; legacy questions unchanged."""
import re

TAG = re.compile(r'\|([A-Za-z0-9_]+)\s+(\.{4})\s*\|\1/')
PLAIN = re.compile(r'\.{4}')

def slots(prompt):
    text = str(prompt or '')
    tagged = list(TAG.finditer(text))
    if tagged:
        masked = TAG.sub('', text)
        if PLAIN.search(masked):
            raise ValueError('Không được trộn ô .... thường với ô có mã nhóm.')
        if re.search(r'\|[A-Za-z0-9_]+/?', masked):
            raise ValueError('Thẻ ô trống không hợp lệ hoặc chưa đóng.')
        names = [m.group(1) for m in tagged]
        if len(names) != len(set(names)):
            raise ValueError('Mỗi mã ô trống chỉ được dùng một lần.')
        return names
    if re.search(r'\|[A-Za-z0-9_]+/?', text):
        raise ValueError('Thẻ ô trống không hợp lệ; dùng |1 .... |1/.')
    return [None] * len(PLAIN.findall(text))

def pairs(value):
    result = {}
    for line in str(value or '').splitlines():
        line = line.strip()
        if not line: continue
        match = re.fullmatch(r'\|([A-Za-z0-9_]+)\s+(.+)', line)
        if not match: raise ValueError('Mỗi dòng cần có dạng |1 lựa chọn 1, lựa chọn 2.')
        key, body = match.groups()
        if key in result: raise ValueError('Mã ô trống bị khai báo lặp: '+key)
        result[key] = [v.strip() for v in body.split(',') if v.strip()]
    return result

def parse(prompt, options_text, answers_text):
    keys = slots(prompt)
    if not keys: return None
    if keys[0] is None:
        opts = [x.strip() for x in str(options_text).splitlines() if x.strip()]
        answers = [x.strip() for x in str(answers_text).splitlines() if x.strip()]
        if len(answers) != len(keys): raise ValueError('Mỗi ô .... cần một đáp án đúng (mỗi dòng một đáp án).')
        all_opts = [opts[:] for _ in keys]
    else:
        option_map = pairs(options_text); answer_map = pairs(answers_text)
        if set(keys) != set(option_map) or set(keys) != set(answer_map):
            raise ValueError('Mã ô trong câu, danh sách lựa chọn và đáp án phải khớp nhau.')
        all_opts = [option_map[k] for k in keys]
        if any(len(answer_map[k]) != 1 for k in keys):
            raise ValueError('Mỗi mã ô cần đúng một đáp án.')
        answers = [answer_map[k][0] for k in keys]
    for i,(opts,answer) in enumerate(zip(all_opts,answers),1):
        if not 2 <= len(opts) <= 8: raise ValueError(f'Ô {i}: cần từ 2 đến 8 lựa chọn.')
        if len(set(opts)) != len(opts): raise ValueError(f'Ô {i}: các lựa chọn không được trùng.')
        if answer not in opts: raise ValueError(f'Ô {i}: đáp án không nằm trong danh sách lựa chọn.')
    return {'blank_options':all_opts,'blank_answers':answers}

def display_text(prompt):
    return TAG.sub('....',str(prompt or ''))

def correct(question,answer):
    expected = question.get('blank_answers') or []
    return isinstance(answer,(list,tuple)) and len(answer)==len(expected) and bool(expected) and all(str(a).strip()==str(b).strip() for a,b in zip(answer,expected))
