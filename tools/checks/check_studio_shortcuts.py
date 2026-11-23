"""Studio geometry operations and copy-on-write lesson templates."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tuhoc.studio.layout_edit_geometry import arrange, bounds, constrain, snap_axis
from tuhoc.studio.layout_templates import apply_lesson_layout, read_template, save_template


class StudioShortcuts(unittest.TestCase):
    def test_movement_preserves_group_and_page_limits(self):
        a=dict(x=.14,y=.2,width=.2,height=.1)
        b=dict(x=.58,y=.4,width=.2,height=.2)
        group=bounds([a,b])
        dx,dy=constrain(group,1,5)
        self.assertAlmostEqual(dx,.22)
        self.assertAlmostEqual(dy,3.4)
        snapped,target,distance=snap_axis(a,'x',-.138,[],.01,(0,.5,1))
        self.assertAlmostEqual(snapped,-.14)
        self.assertEqual(target,0)
        self.assertAlmostEqual(distance,-.002)
        far,guide,_=snap_axis(a,'y',.18,[],.01,(0,.5,1))
        self.assertEqual((far,guide),(.18,None))

    def test_alignment_and_distribution(self):
        rects={k:dict(x=x,y=y,width=.1,height=.2)
               for k,x,y in [('a',.1,.2),('b',.2,.3),('c',.8,.4)]}
        aligned=arrange(rects,'y',0)
        self.assertTrue(all(r['y']==.2 for r in aligned.values()))
        evenly=arrange(rects,'x','space')
        self.assertAlmostEqual(evenly['b']['x'],.45)
        self.assertAlmostEqual(evenly['c']['x'],.8)

    def test_template_round_trip_only_updates_matching_questions(self):
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/'templates.json'
            layout={'version':3,'desktop':{'answer_area':{'x':65,'y':240}},'extras':[]}
            save_template(path,'fill',layout)
            self.assertEqual(read_template(path,'fill'),layout)
            self.assertIsNone(read_template(path,'choice'))
            row=dict(theme='sports',level=2,lesson=1,type='fill',answer='yes')
            unrelated={**row,'lesson':2}
            rows=[row,unrelated]
            updated,matches,changes=apply_lesson_layout(rows,('sports','2','1','fill'),layout)
            self.assertEqual((matches,changes),(1,1))
            self.assertNotIn('layout',row)
            self.assertEqual(updated[0]['answer'],row['answer'])
            self.assertEqual(updated[1],unrelated)
            self.assertEqual(apply_lesson_layout(updated,('sports','2','1','fill'),layout)[2],0)


if __name__=='__main__':
    unittest.main(verbosity=2)
