"""Persistent, per-student quiz draft using the existing application SQLite connection."""
import json
import math

class QuizDraftStore:
    def __init__(self, connection):
        self.conn=connection
        self.conn.execute('''CREATE TABLE IF NOT EXISTS quiz_drafts (
            student_id INTEGER NOT NULL, language TEXT NOT NULL,
            theme TEXT NOT NULL, level INTEGER NOT NULL,
            questions TEXT NOT NULL, answers TEXT NOT NULL,
            elapsed REAL NOT NULL DEFAULT 0,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(student_id, language, theme, level))''')
        self.conn.commit()

    def save(self,student_id,language,theme,level,questions,answers,elapsed):
        if not isinstance(questions,list) or not isinstance(answers,(list,tuple)) or len(answers)>len(questions):
            raise ValueError('Invalid draft progress')
        payload=[]
        for item in answers:
            if not isinstance(item,(list,tuple)) or len(item)!=2:
                raise ValueError('Invalid draft answer')
            answer,ok=item
            if not isinstance(ok,bool):
                raise ValueError('Invalid correctness flag')
            payload.append({'answer':answer,'correct':ok})
        duration=float(elapsed)
        if not math.isfinite(duration) or duration<0:raise ValueError('Invalid duration')
        self.conn.execute('''INSERT INTO quiz_drafts(student_id,language,theme,level,questions,answers,elapsed)
            VALUES (?,?,?,?,?,?,?)
            ON CONFLICT(student_id,language,theme,level) DO UPDATE SET
            questions=excluded.questions, answers=excluded.answers,
            elapsed=excluded.elapsed, updated_at=CURRENT_TIMESTAMP''',
            (student_id,language,theme,level,json.dumps(questions,ensure_ascii=False),
             json.dumps(payload,ensure_ascii=False),max(0.0,duration)))
        self.conn.commit()

    def load(self,student_id,language,theme,level):
        row=self.conn.execute('''SELECT questions,answers,elapsed FROM quiz_drafts
            WHERE student_id=? AND language=? AND theme=? AND level=?''',
            (student_id,language,theme,level)).fetchone()
        if row is None:return None
        try:
            questions=json.loads(row[0]);raw=json.loads(row[1]);elapsed=float(row[2])
        except (TypeError,ValueError,OverflowError) as exc:
            raise ValueError('Corrupt draft') from exc
        if not isinstance(questions,list) or not isinstance(raw,list) or len(raw)>len(questions):
            raise ValueError('Corrupt draft')
        answers=[]
        for item in raw:
            if not isinstance(item,dict) or 'answer' not in item:raise ValueError('Corrupt answer')
            if not isinstance(item.get('correct'),bool):raise ValueError('Corrupt correctness flag')
            answers.append((item['answer'],item['correct']))
        if not math.isfinite(elapsed) or elapsed<0:raise ValueError('Invalid duration')
        return {'questions':questions,'answers':answers,'elapsed':max(0.0,elapsed)}

    def delete(self,student_id,language,theme,level):
        self.conn.execute('DELETE FROM quiz_drafts WHERE student_id=? AND language=? AND theme=? AND level=?',
                          (student_id,language,theme,level))
        self.conn.commit()
