"""Search and safe list edits shared by the content authoring screens."""
from copy import deepcopy
from dataclasses import dataclass
import unicodedata
from uuid import uuid4


def search_key(value):
    text=unicodedata.normalize('NFD',str(value).casefold()).replace('đ','d')
    return ''.join(char for char in text if not unicodedata.combining(char))


def find_rows(rows,query='',*,fields=('id','prompt','title'),sort_by=None,filters=None):
    terms=search_key(query).split()
    filters=filters or {}
    matches=[]
    for index,row in enumerate(rows):
        if any(str(row.get(key) or (1 if key=='lesson' else ''))!=str(value)
               for key,value in filters.items() if value is not None):
            continue
        if terms:
            text=search_key(' '.join(str(row.get(key,'')) for key in fields))
            if not all(term in text for term in terms):
                continue
        matches.append((index,row))
    if sort_by:
        matches.sort(key=lambda pair:search_key(pair[1].get(sort_by,'')))
    return matches


def copy_question(row):
    copy=deepcopy(row)
    copy['id']=str(row.get('id') or 'cau-hoi')+'-copy-'+uuid4().hex[:10]
    return copy


@dataclass(frozen=True)
class Removal:
    index: int
    row: dict

    def restore(self, rows, *, unique_id=False):
        row=deepcopy(self.row)
        if unique_id and any(item.get('id')==row.get('id') for item in rows):
            raise ValueError('Đã có mục dùng cùng mã. Không thể hoàn tác.')
        index=min(self.index,len(rows))
        return [*rows[:index],row,*rows[index:]]


def remove_at(rows,index):
    return [*rows[:index],*rows[index+1:]],Removal(index,deepcopy(rows[index]))
