"""Check authoring filters, lossless undo and history range filtering."""
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tuhoc.exams.exam_bank_pygame import BankManager
from tuhoc.ui.quiz_history_ui import history_window
from tuhoc.studio.studio_list import copy_question, find_rows, remove_at


class StudioUI(unittest.TestCase):
    def test_filter_sort_keep_original_indices(self):
        rows=[
            dict(id='b',type='fill',prompt='Bé đi học',lesson=1),
            dict(id='a',type='fill',prompt='Đi học nào',lesson=1),
            dict(id='a2',type='choice',prompt='Đi học',lesson=1),
            dict(id='c',type='fill',prompt='Đi học muộn',lesson=2),
        ]
        found=find_rows(rows,'di học',sort_by='id',filters={'type':'fill','lesson':'1'})
        self.assertEqual([index for index,_ in found],[1,0])
        self.assertEqual(found[0][1],rows[1])

    def test_duplicate_and_undo_do_not_mutate_input(self):
        rows=[{'id':'x','answer':['one']},{'id':'y'}]
        duplicate=copy_question(rows[0])
        duplicate['answer'].append('two')
        self.assertNotEqual(duplicate['id'],rows[0]['id'])
        self.assertEqual(rows[0]['answer'],['one'])
        remaining,ticket=remove_at(rows,0)
        self.assertEqual(ticket.restore(remaining,unique_id=True),rows)
        with self.assertRaises(ValueError):
            ticket.restore(rows,unique_id=True)
        self.assertEqual(ticket.restore([*remaining,{'id':'z'}])[-1],{'id':'z'})

    def test_bank_edit_retains_layout_and_delete_can_be_undone(self):
        with TemporaryDirectory() as directory:
            editor=BankManager(Path(directory))
            editor.grade='1';editor.lesson='Family'
            layout=dict(version=3,desktop={},extras=[])
            row=dict(id='original',subject='tieng_anh',grade='1',lesson='Family',
                     type='choice',prompt='Question',answer='yes',options=['yes','no'],
                     difficulty=1,layout=layout)
            editor.bank.save_question(row)
            editor.duplicate(row)
            editor.save()
            questions=editor.bank.questions()
            self.assertEqual(len(questions),2)
            self.assertTrue(all(q['layout']==layout for q in questions))
            editor.request_remove(row)
            _,yes,_=editor.remove_buttons()
            editor.click_remove(yes.center)
            self.assertEqual(len(editor.bank.questions()),1)
            editor.undo_remove()
            self.assertEqual(editor.bank.questions(),questions)

    def test_history_period(self):
        now=datetime(2026,2,4,14)
        recent=('a','theme',1,(now-timedelta(days=6)).timestamp())
        old=('b','theme',1,(now-timedelta(days=8)).timestamp())
        future=('c','theme',1,(now+timedelta(days=1)).timestamp())
        unknown=('d','theme',1,None)
        self.assertEqual(history_window([recent,old,future,unknown],7,now),[recent])
        self.assertEqual(history_window([recent,old],None,now),[recent,old])


if __name__=='__main__':
    unittest.main(verbosity=2)
