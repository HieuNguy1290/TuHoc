"""Count literal palette entries, fonts, UI strings and native dialog calls."""
import argparse
import ast
import json
from pathlib import Path
import re

MODULES = ('ui_components','ui_shell','home_ui','lesson_map_ui','profile_ui',
           'quiz_history_ui','level_flow','main','wrong_answers_ui')
HEX = re.compile(r'#[0-9a-fA-F]{6}')
UI_OPTIONS = {'text','title','label','message'}


def count(path):
    tree=ast.parse(path.read_text(encoding='utf-8-sig'),filename=str(path))
    nodes=list(ast.walk(tree))
    return {
        'hex':sum(isinstance(n,ast.Constant) and isinstance(n.value,str) and
                  bool(HEX.fullmatch(n.value)) for n in nodes),
        'font':sum(isinstance(n,ast.Constant) and n.value=='Segoe UI' for n in nodes),
        'literal_ui':sum(isinstance(n,ast.keyword) and n.arg in UI_OPTIONS and
                         isinstance(n.value,(ast.Constant,ast.JoinedStr)) for n in nodes),
        'messagebox':sum(isinstance(n,ast.Attribute) and isinstance(n.value,ast.Name)
                         and n.value.id=='messagebox' for n in nodes),
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root',type=Path,nargs='?',default=Path(__file__).resolve().parents[1])
    args=parser.parse_args()
    counts={mod:count(args.root/(mod+'.py')) for mod in MODULES}
    total={key:sum(row[key] for row in counts.values()) for key in next(iter(counts.values()))}
    print(json.dumps({'modules':counts,'total':total},indent=2))


if __name__=='__main__':
    main()
