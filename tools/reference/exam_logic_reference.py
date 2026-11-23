"""THAM CHIẾU: kịch bản đã chạy thật ở bước rà soát. Codex chuyển thành pytest trong tests/ (không chạy trực tiếp như bản chính thức).
Đặt biến môi trường TUHOC_ROOT trỏ tới thư mục chứa exam_bank.py (mặc định: thư mục hiện tại)."""
import os as _os
import sys, json, random, tempfile, unicodedata, collections, time
from pathlib import Path
sys.path.insert(0,_os.environ.get('TUHOC_ROOT','.'))
from tuhoc.exams.exam_grading import is_correct
import tuhoc.exams.exam_bank as eb
from tuhoc.exams.exam_bank import ExamBank, validate_question

ok=fail=0
def check(name,cond,note=''):
    global ok,fail
    if cond: ok+=1; print('PASS',name)
    else: fail+=1; print('FAIL',name,note)

print('=== A. CHẤM ĐIỂM ===')
check('choice đúng',is_correct({'type':'choice','answer':'Dog'},'dog'))
check('choice sai',not is_correct({'type':'choice','answer':'Dog'},'cat'))
check('choice chưa trả lời',not is_correct({'type':'choice','answer':'Dog'},None))
check('fill thừa khoảng trắng đầu/cuối',is_correct({'type':'fill','answer':'ice cream'},'  Ice cream '))
check('fill 2 khoảng trắng giữa từ',is_correct({'type':'fill','answer':'ice cream'},'ice  cream'),'khoảng trắng kép giữa từ bị chấm sai')
nfc='bà ngoại'; nfd=unicodedata.normalize('NFD',nfc)
check('tiếng Việt NFC vs NFD',is_correct({'type':'fill','answer':nfc},nfd),'cùng chữ nhưng khác dạng Unicode bị chấm sai')
check('tiếng Việt hoa/thường có dấu',is_correct({'type':'fill','answer':'Bà Ngoại'},'bà ngoại'))
check('error dùng corrected',is_correct({'type':'error','wrong':'go','corrected':'goes'},'goes'))
check('error trả lời từ sai bị sai',not is_correct({'type':'error','wrong':'go','corrected':'goes'},'go'))
g={'type':'sentence_gaps','gap_answers':['is','a']}
check('gaps đúng',is_correct(g,['IS',' a ']))
check('gaps thiếu 1 ô',not is_correct(g,['is','']))
check('gaps sai độ dài',not is_correct(g,['is']))
check('gaps answer là chuỗi',not is_correct(g,'is a'))
m={'type':'matching','pairs':[['a','1'],['b','2']]}
check('matching đúng',is_correct(m,{'a':'1','b':'2'}))
check('matching thiếu cặp',not is_correct(m,{'a':'1'}))
check('matching đảo',not is_correct(m,{'a':'2','b':'1'}))
o={'type':'order','sequence':['I','am','here']}
check('order đúng',is_correct(o,'',['I','am','here']))
check('order sai',not is_correct(o,'',['am','I','here']))
check('order chưa chọn',not is_correct(o,'',None))
check('true_false',is_correct({'type':'true_false','answer':'True'},'true'))

print('\n=== B. VALIDATE CÂU HỎI ===')
base=dict(grade='3',lesson='L1',difficulty=1,subject='tieng_anh')
def v(**kw):
    q=dict(base);q.update(kw)
    try: validate_question(q);return None
    except Exception as e: return type(e).__name__+': '+str(e)
check('choice hợp lệ',v(type='choice',prompt='p',options=['a','b'],answer='a') is None)
check('choice đáp án ngoài lựa chọn bị chặn',v(type='choice',prompt='p',options=['a','b'],answer='c') is not None)
check('choice trùng đáp án (khác hoa/thường) bị chặn',v(type='choice',prompt='p',options=['a','A'],answer='a') is not None)
check('choice 5 lựa chọn bị chặn',v(type='choice',prompt='p',options=list('abcde'),answer='a') is not None)
check('difficulty=6 bị chặn',v(type='choice',prompt='p',options=['a','b'],answer='a',difficulty=6) is not None)
r=v(type='choice',prompt='p',options=['a','b'],answer='a',difficulty='abc')
print('   difficulty="abc" ->',r)
r=v(type='choice',prompt='p',options=['a','b'],answer='a',difficulty=None)
print('   difficulty=None  ->',r)
r=v(type='choice',prompt='p',options=['a','b'],answer='a',difficulty=2.7)
print('   difficulty=2.7   ->',r,'(2.7 -> int=2, chấp nhận ngầm)')
check('gaps marker khớp',v(type='sentence_gaps',prompt='A {1} B {2}',gap_answers=['x','y']) is None)
check('gaps marker lệch bị chặn',v(type='sentence_gaps',prompt='A {1} B {3}',gap_answers=['x','y']) is not None)
check('order trùng từ bị chặn',v(type='order',prompt='p',sequence=['a','a']) is not None)
check('order trùng khác khoảng trắng',v(type='order',prompt='p',sequence=['a','a ']) is not None,'"a" và "a " được coi là khác nhau -> hai nút giống hệt trên màn hình')
check('matching sai mode bị chặn',v(type='matching',prompt='p',pairs=[['a','1'],['b','2']],matching_mode='Chữ - Chữ') is not None)
check('matching 1 cặp bị chặn',v(type='matching',prompt='p',pairs=[['a','1']],matching_mode='Chữ ↔ Chữ') is not None)
check('listening thiếu file bị chặn',v(type='listening_choice',prompt='p',options=['a','b'],answer='a',audio='/nope.mp3') is not None)
check('type lạ bị chặn',v(type='dropdown',prompt='p',answer='a') is not None)

print('\n=== C. TẠO ĐỀ ===')
root=Path(tempfile.mkdtemp())
bank=ExamBank(root)
def mk(i,d,**kw):
    q=dict(type='choice',grade='3',lesson='L1',difficulty=d,prompt=f'q{i}',options=['a','b'],answer='a',subject='tieng_anh');q.update(kw);return q
ids=[]
n=0
for d in range(1,6):
    for k in range(60):
        n+=1;ids.append(bank.save_question(mk(n,d)))
cfg=bank.config();cfg['question_count']=20;bank.save_config(cfg)
for lvl in (1,5,10):
    ex=bank.create_exam('3','L1',lvl,rng=random.Random(lvl))
    cnt=collections.Counter(int(q['difficulty']) for q in ex['questions'])
    check(f'level {lvl}: đủ 20 câu',len(ex['questions'])==20,len(ex['questions']))
    check(f'level {lvl}: khớp counts {ex["counts"]}',[cnt.get(i,0) for i in range(1,6)]==ex['counts'],dict(cnt))
    check(f'level {lvl}: không trùng id',len({q['id'] for q in ex['questions']})==20)
# tỷ lệ làm tròn
cfg=bank.config()
for nq in (1,7,13,33,50):
    cfg['question_count']=nq;bank.save_config(cfg)
    for lvl in range(1,11):
        try:
            ex=bank.create_exam('3','L1',lvl,rng=random.Random(1))
            assert len(ex['questions'])==nq and sum(ex['counts'])==nq
        except Exception as e:
            fail+=1;print('FAIL tạo đề n=%d level=%d: %s'%(nq,lvl,e));break
    else: ok+=1;print('PASS n=%d mọi level đều đủ câu'%nq)
# ngân hàng thiếu câu
small=ExamBank(Path(tempfile.mkdtemp()))
for i in range(5):small.save_question(mk(i,1))
c=small.config();c['question_count']=10;small.save_config(c)
try: small.create_exam('3','L1',1);check('thiếu câu -> báo lỗi',False)
except ValueError as e: check('thiếu câu -> báo lỗi rõ ràng',True);print('   ',str(e)[:120])
# lọc môn / lớp
cfg=bank.config();cfg['question_count']=20;bank.save_config(cfg)
check('đề lọc đúng lớp',all(q['grade']=='3' for q in bank.create_exam('3','L1',1,rng=random.Random(1))['questions']))
try: bank.create_exam('4','L1',1);check('lớp khác không có câu',False)
except ValueError: check('lớp khác không có câu -> lỗi',True)

print('\n=== D. MỘT CÂU HỎNG CÓ CHẶN CẢ ĐỀ? ===')
b2=ExamBank(Path(tempfile.mkdtemp()))
audio=Path(tempfile.mkdtemp())/'a.mp3';audio.write_bytes(b'x'*10)
for i in range(1,31): b2.save_question(mk(i,1))
b2.save_question(mk(99,1,type='listening_choice',audio=str(audio)))
c=b2.config();c['question_count']=5;c['ratios']['1']=[100,0,0,0,0];b2.save_config(c)
check('đề tạo được khi đủ media',len(b2.create_exam('3','L1',1,rng=random.Random(1))['questions'])==5)
# giả lập chuyển máy: xoá file audio
pack=b2.media_folder
for f in pack.glob('*'):f.unlink()
try:
    b2.create_exam('3','L1',1,rng=random.Random(1));check('1 câu mất file audio không chặn cả đề',True)
except ValueError as e:
    check('1 câu mất file audio không chặn cả đề',False,'-> '+str(e))

print('\n=== E. BÀI ĐỌC (nhóm) ===')
b3=ExamBank(Path(tempfile.mkdtemp()))
for i in range(1,61):b3.save_question(mk(i,1+i%3))
kids=[dict(prompt=f'k{j}',options=['a','b'],answer='a',difficulty=1+j) for j in range(3)]
b3.save_reading(dict(subject='tieng_anh',grade='3',lesson='L1',title='T',passage='P',questions=kids))
c=b3.config();c['question_count']=8;c['ratios']['3']=[50,25,25,0,0];b3.save_config(c)
okg=True
for s in range(200):
    ex=b3.create_exam('3','L1',3,rng=random.Random(s))
    qs=ex['questions'];grp=[i for i,q in enumerate(qs) if q.get('reading_group')]
    if grp and grp!=list(range(grp[0],grp[0]+len(grp))): okg=False;break
    if len(qs)!=8: okg=False;break
check('200 đề: nhóm bài đọc luôn liền nhau và đủ 8 câu',okg)
# sửa bài đọc giữ id con
gid=b3.reading_groups()[0]['id']
g=b3.reading_groups()[0];before=[c['id'] for c in g['questions']]
g['questions'][0]['prompt']='edited';b3.save_reading(g)
after=[c['id'] for c in b3.reading_groups()[0]['questions']]
check('sửa bài đọc giữ nguyên id câu con',before==after)
bad=b3.reading_groups()[0];bad['questions'][0]['id']='hack'
try:b3.save_reading(bad);check('id câu con lạ bị chặn',False)
except ValueError:check('id câu con lạ bị chặn',True)

print('\n=== F. LƯU/ĐỌC & KẾT QUẢ ===')
b4=ExamBank(Path(tempfile.mkdtemp()))
qid=b4.save_question(mk(1,1,prompt='Xin chào đây là tiếng Việt'))
check('lưu/đọc tiếng Việt',b4.questions()[0]['prompt']=='Xin chào đây là tiếng Việt')
qid2=b4.save_question(dict(b4.questions()[0],prompt='sửa'))
check('sửa câu không nhân bản',len(b4.questions())==1)
b4.delete_question(qid)
check('xoá câu',len(b4.questions())==0)
try:b4.delete_question('x');check('xoá id không tồn tại -> lỗi',False)
except ValueError:check('xoá id không tồn tại -> lỗi',True)
b4.save_result({'id':'r1','correct':1});b4.save_result({'id':'r1','correct':9})
rs=json.loads(b4.results_path.read_text(encoding='utf-8'))
check('save_result chống ghi trùng id',len(rs)==1 and rs[0]['correct']==1)
b4.questions_path.write_text('{broken',encoding='utf-8')
try:b4.questions();check('JSON hỏng -> lỗi dễ hiểu',False)
except Exception as e:print('   JSON hỏng ->',type(e).__name__,str(e)[:60]);check('JSON hỏng -> lỗi dễ hiểu',isinstance(e,ValueError),'ném %s thay vì ValueError nên UI không bắt được'%type(e).__name__)

print('\nTỔNG: %d PASS, %d FAIL'%(ok,fail))
