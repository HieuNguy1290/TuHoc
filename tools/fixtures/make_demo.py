from tuhoc.paths import PROJECT_ROOT
from pathlib import Path
import json
from tuhoc.lessons.level_flow import THEMES,export_levels
BASE=PROJECT_ROOT
DATA=BASE/'content_library'/'demo_levels';DATA.mkdir(parents=True,exist_ok=True)
sets={
'family':[('father','bố'),('mother','mẹ'),('grandfather','ông'),('grandmother','bà'),('brother','anh trai'),('sister','chị gái'),('baby','em bé'),('family','gia đình'),('parents','bố mẹ'),('home','ngôi nhà'),('uncle','chú'),('aunt','cô'),('cousin','anh chị em họ'),('love','yêu thương'),('help','giúp đỡ')],
'sports':[('football','bóng đá'),('basketball','bóng rổ'),('swimming','bơi lội'),('running','chạy bộ'),('cycling','đạp xe'),('badminton','cầu lông'),('tennis','quần vợt'),('volleyball','bóng chuyền'),('skating','trượt patin'),('jump','nhảy'),('team','đội'),('ball','quả bóng'),('coach','huấn luyện viên'),('win','chiến thắng'),('practice','luyện tập')],
'actions':[('walk','đi bộ'),('run','chạy'),('jump','nhảy'),('read','đọc'),('write','viết'),('eat','ăn'),('drink','uống'),('sleep','ngủ'),('sing','hát'),('dance','nhảy múa'),('listen','lắng nghe'),('draw','vẽ'),('play','chơi'),('open','mở'),('close','đóng')],
'animals':[('cat','con mèo'),('dog','con chó'),('bird','con chim'),('fish','con cá'),('lion','sư tử'),('tiger','hổ'),('elephant','voi'),('monkey','khỉ'),('rabbit','thỏ'),('duck','vịt'),('cow','bò'),('horse','ngựa'),('bear','gấu'),('frog','ếch'),('goat','dê')],
'fruits':[('apple','quả táo'),('banana','quả chuối'),('orange','quả cam'),('mango','quả xoài'),('grape','quả nho'),('watermelon','dưa hấu'),('pineapple','quả dứa'),('strawberry','dâu tây'),('peach','quả đào'),('pear','quả lê'),('lemon','quả chanh'),('papaya','đu đủ'),('coconut','dừa'),('guava','ổi'),('cherry','anh đào')]
}
lessons=[];questions=[];vocab=[]
for code,name,icon,color in THEMES:
    words=sets[code]
    for lvl in range(1,11):
        segment=[words[(lvl*2+i-2)%len(words)] for i in range(5)]
        lineup='\n'.join(f'{en} — {vi}' for en,vi in segment)
        context={'family':'Mọi thành viên trong gia đình yêu thương và giúp đỡ nhau.','sports':'Thể thao giúp cơ thể khỏe mạnh. Hãy vận động an toàn.','actions':'Mỗi ngày chúng ta thực hiện nhiều hành động khác nhau.','animals':'Các loài vật có đặc điểm và môi trường sống đa dạng.','fruits':'Trái cây có nhiều màu sắc và hương vị, giúp bổ sung dinh dưỡng.'}[code]
        content=(f'CHỦ ĐỀ {name.upper()} — LEVEL {lvl}\n\nTỪ KHÓA:\n{lineup}\n\nKIẾN THỨC:\n{context}\n\nVÍ DỤ:\n'+ '\n'.join(f'• {en}: {vi}.' for en,vi in segment)+'\n\nGHI NHỚ:\nHãy đọc, phát âm, chỉ vào hình minh họa và dùng mỗi từ đặt một câu ngắn.\n\n'+context)
        lessons.append(dict(theme=code,level=lvl,title=f'{name} — Bài {lvl}',instructions='Quan sát hình bên trái, đọc các từ và nội dung bên phải. Bôi đen từ mới rồi bấm Lưu. Sau khi học, chọn Bài tập hoặc Từ vựng cùng level.',content=content,image=''))
        for word,meaning in segment:vocab.append(dict(theme=code,level=lvl,word=word,meaning=meaning,image=''))
        for n in range(10):
            word,meaning=segment[n%5]
            typ=['choice','true_false','fill','matching','error','order','choice','fill','true_false','matching'][n]
            opts=[];answer=word;prompt=''
            if typ in ('choice','matching'):
                prompt=f'Từ tiếng Anh tương ứng với “{meaning}” là gì?'
                opts=[word]+[x[0] for x in segment if x[0]!=word][:3]
            elif typ=='true_false':
                prompt=f'“{word}” có nghĩa là “{meaning}”. Đúng hay sai?';answer='Đúng';opts=['Đúng','Sai']
            elif typ=='fill':prompt=f'Viết từ tiếng Anh của “{meaning}”.'
            elif typ=='error':prompt=f'Sửa từ viết hoa thành chữ thường: {word.upper()}'
            elif typ=='order':
                # one-word base form; creates unambiguous reorder of letters for learning
                prompt=f'Sắp xếp chữ cái để tạo từ có nghĩa “{meaning}”: '+' - '.join(reversed(list(word)))
            questions.append(dict(theme=code,level=lvl,id=f'{code}_{lvl}_{n+1}',type=typ,prompt=prompt,options=opts,answer=answer,accepted_answers=[answer]))
for name,rows in [('lessons',lessons),('questions',questions),('vocab',vocab)]:
    (DATA/(name+'.json')).write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
print('created',len(lessons),len(questions),len(vocab))
# export should take bundled demo data by default; user overrides stored separately
export_levels(BASE/'MAU_5_CHU_DE_10_LEVELS.xlsx',BASE/'_demo_user_data_empty')
