"""Safe import of Vietnamese vocabulary with unique stable IDs."""
import json, shutil, datetime
from pathlib import Path
from tuhoc.lessons.level_flow import library_file
from tuhoc.ui.theme_config import tuples as theme_tuples, max_level as theme_max, normalize_code

def import_vietnamese_vocab(source, data_dir):
    rows=json.loads(Path(source).read_text(encoding='utf-8-sig'))
    if not isinstance(rows,list):raise ValueError('JSON phải là một danh sách từ vựng.')
    seen=set();clean=[]
    for line, item in enumerate(rows,1):
        if not isinstance(item,dict):raise ValueError(f'Dòng {line}: Phải là object.')
        theme=normalize_code(item.get('theme',''),data_dir)
        try:level=int(item.get('level'))
        except (TypeError, ValueError):raise ValueError(f'Dòng {line}: Level không hợp lệ.')
        if theme not in {t[0] for t in theme_tuples(data_dir)} or not 1<=level<=theme_max(data_dir,theme):
            raise ValueError(f'Dòng {line}: Chủ đề / level không hợp lệ.')
        if not str(item.get('word','')).strip():raise ValueError(f'Dòng {line}: Thiếu từ.')
        item=dict(item,theme=theme,level=level)
        unique=str(item.get('id') or f'vi.word.{theme}.{level}.{line}')
        if unique in seen:raise ValueError(f'Dòng {line}: ID trùng {unique}. Hãy sửa ID rồi nhập lại.')
        item['id']=unique;item.setdefault('meaning','');item.setdefault('schema_version','2.1')
        seen.add(unique);clean.append(item)
    target=library_file(data_dir,'vocab');target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():
        backup=target.with_name('level_vocab_backup_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.json')
        shutil.copy2(target,backup)
    temp=target.with_suffix('.json.tmp')
    temp.write_text(json.dumps(clean,ensure_ascii=False,indent=2),encoding='utf-8')
    temp.replace(target)
    return len(clean), str(target)
