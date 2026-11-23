"""Independent, validated exam bank and configurable level blueprint."""
import json
import math
import os
import random
import tempfile
import uuid
import sqlite3
import shutil
import hashlib
import copy
from pathlib import Path

DEFAULT_RATIOS = [
    [70,20,10,0,0],[60,25,15,0,0],[50,30,15,5,0],
    [40,30,20,10,0],[30,30,25,10,5],[20,30,30,15,5],
    [15,25,30,20,10],[10,20,30,25,15],[5,15,25,30,25],
    [0,10,20,35,35],
]
SUBJECTS = {'tieng_anh': 'Tiếng Anh', 'tieng_viet': 'Tiếng Việt', 'toan': 'Toán'}

def subject_of(q):
    # Legacy questions belong to English until the teacher explicitly moves them.
    return str(q.get('subject') or 'tieng_anh')

CHOICE_TYPES = {'choice','picture_choice','listening_choice','image_multi_choice','true_false'}
ALLOWED_TYPES = {'choice','true_false','fill','error','order','matching','sentence_gaps','conversation_gaps','passage_gaps','picture_choice','picture_missing_letters','image_multi_choice','listening_choice','listening_fill'}


def config_defaults():
    return {'question_count':50,'minutes':60,'ratios':{str(i+1):v[:] for i,v in enumerate(DEFAULT_RATIOS)}}


def validate_config(cfg):
    n=int(cfg['question_count']); minutes=int(cfg['minutes'])
    if not 1 <= n <= 50: raise ValueError('Số câu phải từ 1 đến 50.')
    if not 1 <= minutes <= 240: raise ValueError('Thời gian phải từ 1 đến 240 phút.')
    for level in range(1,11):
        row=cfg['ratios'][str(level)]
        if len(row)!=5 or any(not isinstance(x,int) or isinstance(x,bool) or x<0 or x>100 for x in row) or sum(row)!=100:
            raise ValueError(f'Level {level}: cần 5 tỷ lệ nguyên, không âm, tổng bằng 100%.')
    return cfg


class MissingExamMedia(ValueError):
    """An exam question refers to an asset unavailable on this machine."""


def validate_question(q):
    if not isinstance(q,dict):raise ValueError('Câu hỏi không hợp lệ.')
    if subject_of(q) not in SUBJECTS: raise ValueError('Môn học không hợp lệ.')
    required = ('grade', 'lesson', 'type') if q.get('type') == 'picture_missing_letters' else ('grade', 'lesson', 'prompt', 'type')
    for key in required:
        if not str(q.get(key,'')).strip():raise ValueError(f'Thiếu {key}.')
    if not 1<=int(q.get('difficulty',0))<=5:raise ValueError('Mức độ phải từ 1 đến 5.')
    if q['type'] not in ALLOWED_TYPES:raise ValueError('Dạng câu hỏi chưa được hỗ trợ trong Exam Mode.')
    if q['type'] in {'listening_choice','listening_fill'}:
        audio=str(q.get('audio','')).strip()
        if not audio or not Path(audio).is_file() or Path(audio).suffix.lower() not in {'.mp3','.ogg','.wav'}:
            raise MissingExamMedia('Câu hỏi nghe cần file MP3, OGG hoặc WAV đang tồn tại.')
    if q['type'] in {'picture_choice','picture_missing_letters'}:
        image=str(q.get('image','')).strip()
        if not image or not Path(image).is_file():raise MissingExamMedia('Câu nhìn hình cần ảnh hợp lệ trên máy này.')
    if q['type']=='listening_choice':
        image=str(q.get('image','')).strip()
        if image and not Path(image).is_file():raise MissingExamMedia('Ảnh minh họa của câu nghe không tồn tại trên máy này.')
    if q['type']=='image_multi_choice':
        opts=q.get('options',[])
        if not isinstance(opts,list) or not 2<=len(opts)<=4 or any(not isinstance(p,str) for p in opts):
            raise ValueError('Cần 2–4 file ảnh đáp án có tồn tại.')
        if any(not Path(p).is_file() for p in opts):
            raise MissingExamMedia('Cần 2–4 file ảnh đáp án có tồn tại.')
        if len(set(os.path.normcase(os.path.abspath(p)) for p in opts))!=len(opts):
            raise ValueError('Ảnh đáp án không được trùng nhau.')
        if q.get('answer') not in opts:raise ValueError('Ảnh đúng phải nằm trong các lựa chọn.')
    elif q['type'] in {'picture_missing_letters','listening_fill'}:
        if not str(q.get('answer','')).strip():raise ValueError('Cần đáp án chữ còn thiếu.')
    elif q['type'] in CHOICE_TYPES:
        opts=q.get('options',[])
        if not isinstance(opts,list) or not 2<=len(opts)<=4 or any(not str(x).strip() for x in opts):raise ValueError('Cần 2–4 đáp án không trống.')
        if len(set(str(x).strip().casefold() for x in opts))!=len(opts):raise ValueError('Đáp án trùng nhau.')
        if str(q.get('answer','')).strip() not in [str(x).strip() for x in opts]:raise ValueError('Đáp án đúng không thuộc lựa chọn.')
    elif q['type'] in {'sentence_gaps','conversation_gaps','passage_gaps'}:
        import re
        answers=q.get('gap_answers',[])
        if not isinstance(answers,list) or not 2<=len(answers)<=10 or any(not isinstance(a,str) or not a.strip() for a in answers):
            raise ValueError('Cần 2–10 đáp án chỗ trống, ngăn cách bằng |.')
        markers=[int(m) for m in re.findall(r'\{(\d+)\}',str(q['prompt']))]
        if sorted(markers)!=list(range(1,len(answers)+1)):
            raise ValueError('Nội dung phải có đủ các ô {1}, {2}, ... tương ứng, mỗi ô một lần.')
    elif q['type']=='matching':
        if q.get('matching_mode') != 'Chữ ↔ Chữ':
            raise ValueError('Matching hình ảnh sẽ được hỗ trợ trong Patch 05C; hiện chỉ lưu Chữ ↔ Chữ.')
        pairs=q.get('pairs',[])
        if not isinstance(pairs,list) or not 2<=len(pairs)<=5 or any(not isinstance(x,list) or len(x)!=2 or not all(str(v).strip() for v in x) for x in pairs):
            raise ValueError('Matching cần 2–5 cặp chữ hợp lệ.')
        if len(set(x[0].casefold() for x in pairs))!=len(pairs) or len(set(x[1].casefold() for x in pairs))!=len(pairs):
            raise ValueError('Mỗi vế của Matching phải không trùng nhau.')
    elif q['type']=='order':
        seq=q.get('sequence',[])
        if not isinstance(seq,list) or not 2<=len(seq)<=8 or any(not str(x).strip() for x in seq) or len(set(seq))!=len(seq):
            raise ValueError('Sắp xếp cần 2–8 từ/cụm từ khác nhau.')
    elif q['type']=='error':
        if not str(q.get('wrong','')).strip() or not str(q.get('corrected','')).strip():
            raise ValueError('Tìm lỗi cần từ sai và từ đúng.')
    else:
        if not str(q.get('answer','')).strip():raise ValueError('Thiếu đáp án đúng.')
    if q['type'] in {'listening_choice','listening_fill'} and not str(q.get('audio','')).strip():
        raise ValueError('Câu hỏi nghe cần file audio.')
    return q


def _read(path, default):
    if not path.exists():return default
    return json.loads(path.read_text(encoding='utf-8-sig'))


def _atomic(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.exam_',suffix='.tmp',dir=str(path.parent))
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:
            json.dump(value,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)


class ExamBank:
    def __init__(self,root):
        self.folder=Path(root)/'content_library'
        self.questions_path=self.folder/'exam_questions.json'
        self.config_path=self.folder/'exam_config.json'
        self.results_path=self.folder/'exam_results.json'
        self.readings_path=self.folder/'exam_reading_groups.json'
        self.media_folder=self.folder/'exam_media'

    def config(self):
        default=config_defaults(); stored=_read(self.config_path,{})
        if isinstance(stored,dict):
            default.update({k:v for k,v in stored.items() if k!='ratios'})
            if isinstance(stored.get('ratios'),dict):default['ratios'].update(stored['ratios'])
        return validate_config(default)

    def save_config(self,cfg):_atomic(self.config_path,validate_config(cfg))

    def _resolve_media(self, path):
        """Resolve managed relative assets for editor and exam without changing JSON."""
        value=str(path or '')
        if not value:return value
        candidate=Path(value)
        return str((self.folder/candidate).resolve()) if not candidate.is_absolute() else value

    def _expand_question(self, row):
        q=dict(row)
        for key in ('image','audio'):
            if q.get(key):q[key]=self._resolve_media(q[key])
        if q.get('type')=='image_multi_choice':
            q['options']=[self._resolve_media(x) for x in q.get('options',[])]
            if q.get('answer'):q['answer']=self._resolve_media(q['answer'])
        return q

    def _store_asset(self, value):
        """Copy user-selected media into the project; reuse identical bytes."""
        source=Path(self._resolve_media(value))
        if not source.is_file():raise ValueError('Không tìm thấy file tài nguyên: '+str(source))
        digest=hashlib.sha256()
        with source.open('rb') as stream:
            for chunk in iter(lambda:stream.read(1024*1024),b''):
                digest.update(chunk)
        suffix=source.suffix.lower()
        target=self.media_folder/(digest.hexdigest()[:24]+suffix)
        if source.resolve()!=target.resolve():
            self.media_folder.mkdir(parents=True,exist_ok=True)
            if not target.is_file():
                temp=target.with_name(target.name+'.tmp')
                try:
                    shutil.copyfile(source,temp)
                    os.replace(temp,target)
                finally:
                    if temp.exists():temp.unlink()
        return 'exam_media/'+target.name

    def _pack_question(self, row):
        q=dict(row)
        for key in ('image','audio'):
            if q.get(key):q[key]=self._store_asset(q[key])
        if q.get('type')=='image_multi_choice':
            old=list(q.get('options',[]))
            packed=[self._store_asset(x) for x in old]
            if q.get('answer') in old:q['answer']=packed[old.index(q['answer'])]
            q['options']=packed
        return q

    def questions(self):
        rows=_read(self.questions_path,[])
        if not isinstance(rows,list):raise ValueError('Ngân hàng câu hỏi phải là danh sách.')
        return [self._expand_question(q) for q in rows]

    def save_question(self,q):
        q=dict(validate_question(q));q['subject']=subject_of(q);q['id']=str(q.get('id') or uuid.uuid4().hex)
        stored=self._pack_question(q)
        rows=_read(self.questions_path,[])
        if not isinstance(rows,list):raise ValueError('Ngân hàng câu hỏi phải là danh sách.')
        rows=[r for r in rows if r.get('id')!=q['id']];rows.append(stored)
        _atomic(self.questions_path,rows)
        return q['id']

    def add_text_questions(self, questions):
        """Add a batch of text questions, preserving existing records by ID."""
        from tuhoc.storage.safe_storage import commit_json

        rows = _read(self.questions_path, [])
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ValueError('Ngân hàng câu hỏi phải là danh sách câu hỏi.')
        existing = {str(row.get('id', '')) for row in rows}
        incoming = set()
        additions = []
        for question in questions:
            validate_question(question)
            qid = question.get('id')
            if not isinstance(qid, str) or not qid.strip() or qid in incoming:
                raise ValueError('Bộ câu hỏi có mã trùng hoặc thiếu.')
            if question.get('image') or question.get('audio') or question['type'] == 'image_multi_choice':
                raise ValueError('Bộ nạp câu hỏi văn bản không nhận ảnh hoặc âm thanh.')
            incoming.add(qid)
            if qid not in existing:
                additions.append(dict(question, subject=subject_of(question)))
        if additions:
            commit_json({self.questions_path: [*rows, *additions]})
        return len(additions)

    def delete_question(self,question_id):
        rows=_read(self.questions_path,[])
        if not isinstance(rows,list):raise ValueError('Ngân hàng câu hỏi phải là danh sách.')
        remaining=[r for r in rows if r.get('id')!=question_id]
        if len(rows)==len(remaining):raise ValueError('Không tìm thấy câu hỏi.')
        _atomic(self.questions_path,remaining)


    def reading_groups(self):
        groups=_read(self.readings_path,[])
        if not isinstance(groups,list):raise ValueError('Dữ liệu bài đọc không hợp lệ.')
        return groups

    def save_reading(self,group):
        # Work on a deep copy: editor drafts must not be mutated on save or failure.
        group=copy.deepcopy(group)
        if 'layout' in group:
            from tuhoc.studio.question_layout_store import validate_layout
            group['layout'] = validate_layout(group['layout'])
        for field in ('subject','grade','lesson','title','passage'):
            if not str(group.get(field,'')).strip():raise ValueError('Bài đọc thiếu '+field)
        if group['subject'] not in SUBJECTS:raise ValueError('Môn học không hợp lệ.')
        children=group.get('questions',[])
        if not isinstance(children,list) or not 2<=len(children)<=10:
            raise ValueError('Mỗi bài đọc cần 2–10 câu hỏi con.')
        gid=str(group.get('id') or uuid.uuid4().hex)
        # Retain existing child IDs across edits, reordering and deletions.
        # Only newly added children receive a fresh ID. Reject duplicates.
        existing=next((g for g in self.reading_groups() if str(g.get('id'))==gid),None)
        previous={str(c.get('id')) for c in (existing or {}).get('questions',[]) if c.get('id')}
        used=set()
        for child in children:
            cid=str(child.get('id') or '')
            if cid and (cid not in previous or cid in used):
                raise ValueError('Mã câu hỏi con không hợp lệ hoặc bị trùng.')
            if not cid: cid=f'{gid}:{uuid.uuid4().hex[:12]}'
            child['id']=cid
            used.add(cid)
            validate_question(dict(child,subject=group['subject'],grade=group['grade'],lesson=group['lesson'],type='choice'))
        group['id']=gid
        groups=[g for g in self.reading_groups() if g.get('id')!=gid]
        groups.append(group);_atomic(self.readings_path,groups)
        return gid

    def delete_reading(self,gid):
        groups=self.reading_groups();remaining=[g for g in groups if g.get('id')!=gid]
        if len(groups)==len(remaining):raise ValueError('Không tìm thấy bài đọc.')
        _atomic(self.readings_path,remaining)

    def grades(self):
        """Show student grades even before the exam bank has any questions."""
        grades={str(i) for i in range(1,13)}
        for q in self.questions():
            if str(q.get('grade','')).strip(): grades.add(str(q['grade']).strip())
        db=self.folder.parent/'tu_hoc.sqlite3'
        if db.exists():
            try:
                with sqlite3.connect(str(db)) as conn:
                    grades.update(str(r[0]) for r in conn.execute('SELECT DISTINCT grade FROM students') if r[0] is not None)
            except (sqlite3.Error,OSError): pass
        return sorted(grades,key=lambda x:(not x.isdigit(),int(x) if x.isdigit() else x))

    def lessons(self,grade,subject='tieng_anh'):
        """Read real curriculum themes, not only topics with exam questions."""
        lessons=set()
        subjects=self.folder.parent/'mon_hoc'
        if subject not in SUBJECTS: return []
        if subjects.is_dir():
            for file in [subjects/subject/'content_library'/'themes.json']:
                try:
                    themes=_read(file,[])
                    if isinstance(themes,list):
                        for theme in themes:
                            if isinstance(theme,dict) and str(theme.get('code','')).strip():
                                lessons.add(str(theme['code']).strip())
                except (OSError,ValueError,UnicodeError): pass
        # Support projects that keep curriculum themes in the main content_library.
        for file in ([self.folder/'themes.json'] if subject=='tieng_anh' else []):
            try:
                for theme in _read(file,[]):
                    if isinstance(theme,dict) and str(theme.get('code','')).strip():lessons.add(str(theme['code']).strip())
            except (OSError,ValueError,TypeError):pass
        lessons.update(str(q['lesson']).strip() for q in self.questions()
                       if str(q.get('grade'))==str(grade) and subject_of(q)==subject and str(q.get('lesson','')).strip())
        lessons.update(str(g['lesson']) for g in self.reading_groups() if str(g.get('grade'))==str(grade) and g.get('subject')==subject)
        return sorted(lessons,key=str.casefold)

    def exam_courses(self, subject):
        from exam_content.grade2 import LESSON

        courses = {}
        for row in (*self.questions(), *self.reading_groups()):
            if subject_of(row) != subject:
                continue
            grade = str(row.get('grade', '')).strip()
            lesson = str(row.get('lesson', '')).strip()
            if grade and lesson:
                courses.setdefault(grade, set()).add(lesson)
        samples = {'tieng_anh': ('1', 'Family & Friends'), 'tieng_viet': ('2', LESSON)}
        if subject in samples:
            grade, lesson = samples[subject]
            courses.setdefault(grade, set()).add(lesson)
        return {grade: sorted(lessons, key=str.casefold)
                for grade, lessons in sorted(courses.items(), key=lambda item: (
                    not item[0].isdigit(), int(item[0]) if item[0].isdigit() else item[0]))}

    @staticmethod
    def _sample_questions(grade, lesson, subject):
        if (subject, str(grade), lesson) == ('tieng_anh', '1', 'Family & Friends'):
            from tools.fixtures.seed_family_grade1 import build_questions
            return build_questions(lesson)
        if subject == 'tieng_viet' and str(grade) == '2':
            from exam_content.grade2 import LESSON, build_questions
            if lesson == LESSON:
                return [q for q in build_questions() if q['subject'] == subject]
        return []

    def create_exam(self,grade,lesson,level,rng=None,subject='tieng_anh', *, include_samples=False):
        if subject not in SUBJECTS: raise ValueError('Môn học không hợp lệ.')
        cfg=self.config();level=int(level)
        if not 1<=level<=10:raise ValueError('Level phải từ 1 đến 10.')
        rng=rng or random.SystemRandom()
        n=cfg['question_count'];ratios=cfg['ratios'][str(level)]
        raw=[n*p/100 for p in ratios];counts=[math.floor(x) for x in raw]
        for i in sorted(range(5),key=lambda i:(-(raw[i]-counts[i]),i))[:n-sum(counts)]:counts[i]+=1
        eligible=[q for q in self.questions() if str(q.get('grade'))==str(grade) and str(q.get('lesson'))==str(lesson) and subject_of(q)==subject]
        if include_samples:
            existing_ids = {q.get('id') for q in eligible}
            eligible.extend(q for q in self._sample_questions(grade, lesson, subject) if q['id'] not in existing_ids)
        ids=set();buckets={i:[] for i in range(1,6)}
        skipped_media = 0
        for q in eligible:
            try:
                validate_question(q)
            except MissingExamMedia:
                skipped_media += 1
                continue
            qid=str(q.get('id',''))
            if not qid or qid in ids:raise ValueError('Mã câu hỏi trùng hoặc thiếu.')
            ids.add(qid);buckets[int(q['difficulty'])].append(q)
        # Reading groups are atomic: all children are selected together or not at all.
        groups=[]
        for group in self.reading_groups():
            if (str(group.get('grade'))!=str(grade) or str(group.get('lesson'))!=str(lesson)
                    or group.get('subject')!=subject):continue
            gid=str(group.get('id',''))
            children=[];vector=[0]*5
            for i,child in enumerate(group.get('questions',[])):
                q=dict(child,subject=subject,grade=str(grade),lesson=str(lesson),type='choice',
                       passage=group['passage'],reading_title=group['title'],reading_group=gid,
                       id=str(child.get('id') or f'{gid}:{i+1}'),reading_index=i+1,reading_total=len(group['questions']))
                if 'layout' in group:
                    q['reading_layout'] = group['layout']
                validate_question(q)
                if q['id'] in ids:raise ValueError('Mã câu hỏi bài đọc bị trùng.')
                ids.add(q['id']);children.append(q);vector[int(q['difficulty'])-1]+=1
            if children:groups.append((children,vector))
        rng.shuffle(groups)
        # Backtrack over grouped readings; fill remaining quotas with standalone questions.
        # Bound search to avoid stalls for very large teacher-created banks.
        chosen=[];selected_groups=[];budget=[20000]
        def fit(i,remain):
            budget[0]-=1
            if budget[0]<0:return False
            if i==len(groups):
                return all(len(buckets[j+1])>=remain[j] for j in range(5))
            children,vector=groups[i]
            if all(vector[j]<=remain[j] for j in range(5)):
                chosen.append(i)
                if fit(i+1,[remain[j]-vector[j] for j in range(5)]):return True
                chosen.pop()
            return fit(i+1,remain)
        if not fit(0,counts):
            available=[len(buckets[i]) for i in range(1,6)]
            raise ValueError('Ngân hàng chưa đủ câu theo tỷ lệ M1–M5. Câu hỏi bài đọc phải lấy trọn nhóm. '
                             +'Cần: '+str(counts)+'; câu đơn có: '+str(available)+'.'
                             +(f' Bỏ qua {skipped_media} câu thiếu tệp ảnh hoặc âm thanh.' if skipped_media else ''))
        remaining=counts[:]
        selected=[]
        for i in chosen:
            children,vector=groups[i];selected.extend(children)
            remaining=[remaining[j]-vector[j] for j in range(5)]
        for i,count in enumerate(remaining,1):selected.extend(rng.sample(buckets[i],count))
        # Shuffle blocks, not individual reading children, so passage questions stay together.
        blocks=[];seen_groups=set()
        for q in selected:
            gid=q.get('reading_group')
            if gid:
                if gid in seen_groups:continue
                seen_groups.add(gid)
                blocks.append([x for x in selected if x.get('reading_group')==gid])
            else:blocks.append([q])
        rng.shuffle(blocks)
        selected=[q for block in blocks for q in block]
        return {'id':uuid.uuid4().hex,'subject':subject,'grade':str(grade),'lesson':str(lesson),'level':level,
                'minutes':cfg['minutes'],'questions':selected,'counts':counts}

    def save_result(self,result):
        rows=_read(self.results_path,[])
        if not isinstance(rows,list):raise ValueError('Lịch sử kiểm tra không hợp lệ.')
        if any(x.get('id')==result.get('id') for x in rows):return
        rows.append(result);_atomic(self.results_path,rows)
