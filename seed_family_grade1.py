"""Optional demo installer: original Grade 1 Family English questions (not THPT exam questions)."""
import argparse
from pathlib import Path
from exam_bank import ExamBank,validate_question

# Each item: (prompt, correct answer, three plausible distractors).
M1=[
('Who is your mother?','Mom',['Dad','Brother','Grandpa']),
('Who is your father?','Dad',['Sister','Grandma','Baby']),
('Who is your sister?','A girl in my family',['A boy in my family','My teacher','My dog']),
('Who is your brother?','A boy in my family',['My mother','My aunt','My cat']),
('Who is your grandmother?','Grandma',['Dad','Brother','Uncle']),
('Who is your grandfather?','Grandpa',['Sister','Mom','Baby']),
('What do you call your mother?','Mom',['Grandpa','Brother','Uncle']),
('What do you call your father?','Dad',['Grandma','Sister','Aunt']),
('What do you call your mother’s mother?','Grandma',['Brother','Dad','Sister']),
('What do you call your father’s father?','Grandpa',['Mom','Sister','Brother']),
('Which word means a female parent?','Mother',['Father','Brother','Grandfather']),
('Which word means a male parent?','Father',['Sister','Grandmother','Aunt']),
('Which word means a female sibling?','Sister',['Brother','Father','Grandpa']),
('Which word means a male sibling?','Brother',['Sister','Mother','Grandma']),
('Choose the word for a baby boy.','Boy',['Girl','Mother','Grandmother']),
('Choose the word for a baby girl.','Girl',['Boy','Father','Grandfather']),
('Complete: This is my ___. She is my mom.','mother',['father','brother','grandfather']),
('Complete: This is my ___. He is my dad.','father',['sister','mother','grandmother']),
('Complete: My ___ is a girl.','sister',['brother','dad','grandpa']),
('Complete: My ___ is a boy.','brother',['sister','mom','grandma']),
('Complete: My ___ is my mom’s dad.','grandfather',['sister','brother','mother']),
('Complete: My ___ is my dad’s mom.','grandmother',['father','brother','sister']),
('Which one is a family word?','Mother',['Table','Pencil','Window']),
('Which one is a family word?','Brother',['Apple','School','Chair']),
('Which one is a family word?','Sister',['Book','Tree','Ball']),
('Which one is a family word?','Father',['Fish','Door','Pen']),
('Which one is a family word?','Grandma',['Bus','Bag','Sun']),
('Which one is a family word?','Grandpa',['Cup','Hat','Rain']),
('Which one is NOT a family member?','Pencil',['Mother','Father','Sister']),
('Which one is NOT a family member?','Window',['Brother','Grandma','Dad']),
('How do you say “mẹ” in English?','Mother',['Father','Brother','Grandpa']),
('How do you say “bố” in English?','Father',['Sister','Grandma','Mother']),
('How do you say “chị/em gái” in English?','Sister',['Brother','Father','Grandpa']),
('How do you say “anh/em trai” in English?','Brother',['Sister','Mother','Grandma']),
('How do you say “bà” in English?','Grandmother',['Grandfather','Father','Brother']),
('How do you say “ông” in English?','Grandfather',['Grandmother','Sister','Mother']),
('Choose the correct spelling.','Mother',['Mothre','Moter','Mothar']),
('Choose the correct spelling.','Father',['Fathre','Fater','Fathar']),
('Choose the correct spelling.','Sister',['Sistre','Siter','Sistar']),
('Choose the correct spelling.','Brother',['Broter','Brothre','Brothar']),
('Choose the correct spelling.','Family',['Famly','Famlly','Familiy']),
('Which word begins with M?','Mother',['Father','Brother','Sister']),
('Which word begins with F?','Father',['Mother','Sister','Brother']),
('Which word begins with S?','Sister',['Father','Mother','Brother']),
('Which word begins with B?','Brother',['Mother','Father','Sister']),
]
M2=[
('Tom is my dad. Tom is my ___.','father',['sister','mother','grandmother']),
('Anna is my mom. Anna is my ___.','mother',['brother','father','grandfather']),
('Ben and I have the same parents. Ben is a boy. He is my ___.','brother',['mother','sister','grandma']),
('Lily and I have the same parents. Lily is a girl. She is my ___.','sister',['father','brother','grandpa']),
('My mother has a mother. She is my ___.','grandmother',['sister','brother','father']),
('My father has a father. He is my ___.','grandfather',['mother','sister','brother']),
('Choose the correct sentence.','This is my mother.',['This my mother is.','Is mother this my.','Mother is this my.']),
('Choose the correct sentence.','He is my father.',['He my is father.','Is he father my.','My he father is.']),
('Choose the correct sentence.','She is my sister.',['She my sister is.','Sister she is my.','My she is sister.']),
('Choose the correct sentence.','I love my family.',['Love I my family.','My love I family.','Family my I love.']),
('Complete: ___ is my dad.','He',['She','They','We']),
('Complete: ___ is my mom.','She',['He','They','We']),
('Complete: My sister ___ happy.','is',['are','am','be']),
('Complete: I ___ a brother.','have',['has','is','are']),
('Complete: This is ___ family.','my',['I','me','he']),
('Complete: My father ___ tall.','is',['am','are','be']),
('Complete: My mother ___ kind.','is',['am','are','be']),
('Choose the answer: “Who is she?”','She is my mother.',['He is my father.','I am seven.','It is a pencil.']),
('Choose the answer: “Who is he?”','He is my brother.',['She is my sister.','It is a chair.','I like apples.']),
('Choose the answer: “How many sisters do you have?”','I have two sisters.',['I am fine.','It is red.','She is tall.']),
]
M3=[
('Read: “My name is Mai. Lan is my mother. Nam is my father.” Who is Mai’s father?','Nam',['Lan','Mai','Tom']),
('Read: “I am Ben. I have one sister. Her name is Amy.” Who is Amy?','Ben’s sister',['Ben’s mother','Ben’s father','Ben’s grandpa']),
('Read: “Tom is my father. Anna is my mother.” How many parents are named?','Two',['One','Three','Four']),
('Read: “My family has Dad, Mom, my brother and me.” How many people are there?','Four',['Two','Three','Five']),
('Read: “My grandmother is 60. My sister is 8.” Who is older?','Grandmother',['Sister','They are the same age','We cannot tell']),
('Read: “Lucy is my mother’s daughter. She is not me.” Who is Lucy?','My sister',['My father','My grandfather','My brother']),
('Read: “My dad’s dad is Mr. Minh.” Who is Mr. Minh?','My grandfather',['My brother','My sister','My mother']),
('Read: “My mom’s mom is Mrs. Hoa.” Who is Mrs. Hoa?','My grandmother',['My father','My uncle','My brother']),
('Read: “I have two brothers and one sister.” How many siblings do I have?','Three',['One','Two','Four']),
('Read: “Dad is cooking. Mom is reading. My sister is drawing.” Who is drawing?','My sister',['Dad','Mom','Grandpa']),
]


def build_questions(lesson='Family & Friends'):
    questions=[]
    for difficulty,rows in ((1,M1),(2,M2),(3,M3)):
        for i,(prompt,answer,distractors) in enumerate(rows,1):
            options=[answer]+distractors
            # Deterministic varied answer locations; correct answer is retained by value.
            offset=(i*3+difficulty)%4
            options=options[offset:]+options[:offset]
            q={'id':f'DEMO_EN_G1_FAMILY_M{difficulty}_{i:03d}',
               'subject':'tieng_anh','grade':'1','lesson':lesson,'difficulty':difficulty,
               'type':'choice','prompt':prompt,'options':options,'answer':answer,
               'source':'original_grade1_demo_based_on_exam_format'}
            if difficulty==3 and i in (1,2,3,4):
                passages={
                    1:'My name is Mai. I am six years old. My mother is Lan. My father is Nam. We like reading books together.',
                    2:'My name is Ben. I am seven years old. I have one sister. Her name is Amy. We play together after school.',
                    3:'Tom is my father. Anna is my mother. We are a happy family. We eat dinner together every evening.',
                    4:'There are four people in my family: Dad, Mom, my brother and me. We love each other.'}
                q['passage']=passages[i]
                q['prompt']={1:'Who is Mai’s father?',2:'Who is Amy?',3:'How many parents are named?',4:'How many people are in the family?'}[i]
            validate_question(q);questions.append(q)
    return questions


def install(root,lesson=None):
    bank=ExamBank(root)
    if lesson is None:
        found=[name for name in bank.lessons('1','tieng_anh') if 'family' in name.casefold()]
        lesson=found[0] if found else 'Family & Friends'
    existing=bank.questions();generated=build_questions(lesson)
    # Replace only our demo IDs; preserve all teacher questions and other subjects.
    prefix='DEMO_EN_G1_FAMILY_'
    rows=[q for q in existing if not str(q.get('id','')).startswith(prefix)]
    rows.extend(generated)
    from exam_bank import _atomic
    _atomic(bank.questions_path,rows)
    return lesson,len(generated)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',default=str(Path(__file__).resolve().parent));p.add_argument('--lesson',default=None)
    args=p.parse_args();lesson,count=install(args.root,args.lesson)
    print(f'Installed {count} original demo questions: Tiếng Anh / Lớp 1 / {lesson}.')
