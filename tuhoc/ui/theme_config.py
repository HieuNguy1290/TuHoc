"""Per-subject editable theme catalog. Codes are stable identifiers; titles can change."""
import json
import shutil
import datetime
from pathlib import Path

DEFAULTS = {
    'en': [
        {'code':'Family & Friends','title':'Family & Friends','icon':'⌂','color':'#E8F3FF','max_level':10},
        {'code':'sports','title':'Sports','icon':'★','color':'#FFF2DF','max_level':10},
        {'code':'actions','title':'Actions','icon':'➤','color':'#F1E9FF','max_level':10},
        {'code':'animals','title':'Animals','icon':'♣','color':'#E8F7E8','max_level':10},
        {'code':'fruits','title':'Fruits','icon':'●','color':'#FFF0EF','max_level':10},
    ],
    'vi': [
        {'code':'Family & Friends','title':'Gia đình và bạn bè','icon':'⌂','color':'#E8F3FF','max_level':10},
        {'code':'sports','title':'Thể thao','icon':'★','color':'#FFF2DF','max_level':10},
        {'code':'actions','title':'Hành động','icon':'➤','color':'#F1E9FF','max_level':10},
        {'code':'animals','title':'Con vật','icon':'♣','color':'#E8F7E8','max_level':10},
        {'code':'fruits','title':'Trái cây','icon':'●','color':'#FFF0EF','max_level':10},
    ],
}

def language(data_dir):
    return 'vi' if Path(data_dir).name in ('tieng_viet','vi') else 'en'

def path_for(data_dir):
    return Path(data_dir)/'content_library'/'themes.json'

def validate(rows):
    if not isinstance(rows,list) or not rows:raise ValueError('Cần ít nhất một chủ đề.')
    codes=set()
    for r in rows:
        if not isinstance(r,dict):raise ValueError('Mỗi chủ đề phải là một object.')
        code=str(r.get('code','')).strip();title=str(r.get('title','')).strip()
        if not code or not title:raise ValueError('Mã và tên chủ đề không được trống.')
        if code in codes:raise ValueError('Mã chủ đề trùng: '+code)
        codes.add(code)
        if not 1<=int(r.get('max_level',10))<=200:raise ValueError('Số level phải từ 1 đến 200.')
        counts=r.get('lesson_counts',{})
        if not isinstance(counts,dict) or any(not str(k).isdigit() or not 1<=int(k)<=200 or not 1<=int(v)<=200 for k,v in counts.items()):
            raise ValueError('Số Lesson theo Level phải từ 1 đến 200.')
    return rows

def load(data_dir):
    path=path_for(data_dir)
    if not path.exists():return [dict(x) for x in DEFAULTS[language(data_dir)]]
    return validate(json.loads(path.read_text(encoding='utf-8-sig')))

_SHARED={}
def _shared(data_dir):
    """Read-only catalog cached by file mtime/size. Hot paths (per-row / per-level
    lookups) used to re-read and re-validate themes.json on every call. Callers must
    not mutate the result; use load() when a private copy is needed."""
    path=path_for(data_dir)
    try:st=path.stat();stamp=(st.st_mtime_ns,st.st_size)
    except OSError:stamp=None
    key=str(path)
    hit=_SHARED.get(key)
    if hit is not None and hit[0]==stamp:return hit[1]
    rows=load(data_dir)   # raises on invalid data exactly as before; failures are not cached
    _SHARED[key]=(stamp,rows)
    return rows

def save(data_dir,rows):
    validate(rows);path=path_for(data_dir);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        backup=path.with_name('themes_backup_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.json')
        shutil.copy2(path,backup)
    temporary=path.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    temporary.replace(path)
    _SHARED.pop(str(path),None)

def tuples(data_dir):
    return [(r['code'],r['title'],r.get('icon','📘'),r.get('color','#E8F3FF')) for r in _shared(data_dir)]

def max_level(data_dir,code):
    return next((int(r.get('max_level',10)) for r in _shared(data_dir) if r['code']==code),0)

def normalize_code(code,data_dir):
    code=str(code).strip()
    # Legacy data stored 'family', while the original app used 'Family & Friends'.
    if code in ('family','Family') and any(r['code']=='Family & Friends' for r in _shared(data_dir)):
        return 'Family & Friends'
    return code


def icon_file(data_dir, entry):
    """Resolve per-subject icon paths without allowing path traversal."""
    relative=str(entry.get('icon_image','')).strip()
    if not relative:return None
    if Path(relative).suffix.lower() not in ('.png','.webp','.gif'):return None
    base=Path(data_dir).resolve()
    target=(base/relative).resolve()
    if target.is_file() and target.is_relative_to(base):return target
    return None

# Compatibility names used by the existing UI.
from tuhoc.ui.ui_tokens import COLORS as UI_COLORS, LegacyFonts, SPACING

UI_FONTS = LegacyFonts()
UI_SPACING = (*SPACING[:4],20,*SPACING[4:])

def lesson_count(data_dir,code,level):
    row=next((r for r in _shared(data_dir) if r['code']==code),{})
    return int(row.get('lesson_counts',{}).get(str(level),row.get('default_lessons',10)))
