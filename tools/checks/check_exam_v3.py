"""Check authoring coordinates against actual Exam Mode frame and hit targets."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PIL import Image
import pygame

from tuhoc.exams.exam_pygame import ExamUI, VIRTUAL


class ExamV3(unittest.TestCase):
    def test_authored_options_use_the_rendered_scrolled_rect(self):
        with TemporaryDirectory() as directory:
            pygame.font.init()
            ui=ExamUI(directory)
            ui.font,ui.bold,ui.big,ui.small=ui._font(22),ui._font(24,True),ui._font(36,True),ui._font(18)
            ui.grade='1';ui.lesson='Family';ui.deadline=9999999999
            image=Path(directory)/'image.png'
            Image.new('RGB',(80,40),'red').save(image)
            record=dict(id='q',type='choice',image=str(image),prompt='Đi học',
                        options=['yes','no'],answer='yes')
            record['layout']=dict(version=3,desktop={
                'question_image':dict(x=80,y=100,width=170,height=100,image_fit='stretch'),
                'option_0':dict(x=180,y=950,width=220,height=65),
                'option_1':dict(x=180,y=1200,width=220,height=65),
            },extras=[])
            ui.exam={'questions':[record]}
            output=pygame.Surface(VIRTUAL)
            ui._draw_exam(output)
            self.assertEqual(output.get_at((68+65,260+120)),pygame.Color('red'))
            self.assertGreaterEqual(ui.scroll_limit,950+65-ui.read_area.height)
            ui.scroll=800
            ui.buttons.clear()
            ui._draw_exam(output)
            x=ui.read_area.x+round(180*ui.read_area.width/960)
            center=(x+40,ui.read_area.y+950-ui.scroll+30)
            targets=[action for rect,action in ui.buttons if rect.collidepoint(center)]
            self.assertEqual(len(targets),1)
            targets[0]()
            self.assertEqual(ui.answers,{'q':'yes'})
            self.assertTrue(any(rect.collidepoint((900,650)) for rect,_ in ui.buttons))


if __name__=='__main__':
    unittest.main(verbosity=2)
