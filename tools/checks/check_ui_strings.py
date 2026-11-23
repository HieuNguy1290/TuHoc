"""Validate every literal UI translation key and interpolation input."""
import ast
from pathlib import Path
from tools.checks.paths import ROOT, source_file
from string import Formatter
from tempfile import TemporaryDirectory
import unittest

from tuhoc.ui.strings_vi import STRINGS, t
from tuhoc.ui.ui_errors import record_error


class UIStrings(unittest.TestCase):
    def test_keys_and_format_fields(self):
        root=ROOT
        seen=set()
        for name in ('tuhoc/app/main','ui_shell','home_ui','level_flow','wrong_answers_ui','quiz_history_ui','upgrade_v2'):
            nodes=ast.walk(ast.parse(source_file(name+'.py', root).read_text(encoding='utf-8')))
            for node in nodes:
                if not (isinstance(node,ast.Call) and isinstance(node.func,ast.Name)
                        and node.func.id=='t' and node.args):
                    continue
                key=node.args[0]
                choices=[key.body,key.orelse] if isinstance(key,ast.IfExp) else [key]
                for choice in choices:
                    self.assertIsInstance(choice,ast.Constant,name)
                    self.assertIn(choice.value,STRINGS)
                    seen.add(choice.value)
                    fields={field for _,field,_,_ in Formatter().parse(STRINGS[choice.value]) if field}
                    self.assertEqual(fields,{kw.arg for kw in node.keywords},(name,choice.value))
        self.assertEqual(set(STRINGS),seen)
        self.assertEqual(t('quiz_completed',completed=2,total=4),'Đã trả lời 2/4 câu')

    def test_reference_is_logged_with_technical_details(self):
        with TemporaryDirectory() as directory:
            path=Path(directory)/'errors.log'
            try:
                raise ValueError('Chi tiết kỹ thuật')
            except ValueError as error:
                code=record_error(path,(ValueError,error,error.__traceback__))
            self.assertIn(code,path.read_text(encoding='utf-8'))
            self.assertIn('Chi tiết kỹ thuật',path.read_text(encoding='utf-8'))
            message=t('unexpected_error',code=code)
            self.assertIn(code,message)
            self.assertNotIn('ValueError',message)


if __name__=='__main__':
    unittest.main(verbosity=2)
