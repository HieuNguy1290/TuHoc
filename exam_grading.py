"""Pure answer validation used by the Pygame exam and unit tests."""

def is_correct(q, answer, ordered=None):
    kind=q.get('type')
    if kind in ('sentence_gaps','conversation_gaps','passage_gaps'):
        expected=q.get('gap_answers',[])
        return isinstance(answer,list) and len(answer)==len(expected) and all(str(a).strip().casefold()==str(b).strip().casefold() for a,b in zip(answer,expected))
    if kind=='matching':
        pairs=q.get('pairs',[])
        return isinstance(answer,dict) and len(answer)==len(pairs) and all(answer.get(a)==b for a,b in pairs)
    if kind=='order':
        return list(ordered or [])==list(q.get('sequence',[]))
    expected=q.get('corrected','') if kind=='error' else q.get('answer','')
    return str(answer or '').strip().casefold()==str(expected).strip().casefold()
