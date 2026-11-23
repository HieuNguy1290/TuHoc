"""Install an original Grade-12 English Level-10 sample inspired by 2025 THPT exam formats.

Dry run by default. --apply backs up and merges without overwriting teacher questions.
"""
import argparse
import json
import random
import shutil
from collections import Counter
from datetime import datetime
from pathlib import Path

from tuhoc.exams.exam_bank import ExamBank, validate_question

LESSON = 'Family & Friends - THPT 2025'
PREFIX = 'ff12l10_2025_'
# Each tuple: prompt, correct option, three distractors. All passages/questions are original.
ROWS = [
('The students ______ their revision plan before the mock examination.', 'had completed', 'complete', 'have completing', 'are complete'),
('By the time the teacher arrived, the class ______ the discussion.', 'had begun', 'begins', 'will begin', 'begin'),
('A healthy routine helps teenagers ______ academic pressure.', 'cope with', 'run into', 'put off', 'take over'),
('The word “reliable” is closest in meaning to ______.', 'trustworthy', 'temporary', 'expensive', 'uncertain'),
('She studies English every day ______ improve her reading speed.', 'in order to', 'despite', 'because of', 'instead of'),
('Choose the grammatically correct sentence.', 'Neither the teacher nor the students were late.', 'Neither the teacher nor the students was late.', 'Neither the teacher nor the students is late yesterday.', 'Neither the teacher nor the students be late.'),
('The school encouraged students to ______ part in a recycling campaign.', 'take', 'make', 'do', 'bring'),
('If he had checked the instructions, he ______ the mistake.', 'would have avoided', 'will avoid', 'avoids', 'had avoided'),
('The report, ______ was published yesterday, describes new farming methods.', 'which', 'who', 'whose', 'where'),
('Students are advised to avoid ______ information from unreliable sources.', 'sharing', 'to share', 'share', 'shared'),
('The more carefully we check a claim, ______ we are to be misled.', 'the less likely', 'less likely', 'the least likely', 'the likely'),
('“Accelerate” in the sentence “Digital tools accelerate decisions” means ______.', 'speed up', 'put aside', 'turn down', 'give away'),
('Which expression best completes: “The evidence is limited; ______, we should not draw a firm conclusion.”', 'therefore', 'otherwise', 'meanwhile', 'nevertheless'),
('The new irrigation system saves water, ______ makes it attractive to farmers.', 'which', 'what', 'that it', 'whose'),
('Choose the correct passive form: “Researchers are analysing the results.”', 'The results are being analysed by researchers.', 'The results have analysed by researchers.', 'The results are analysing by researchers.', 'The results were being analyse by researchers.'),
('A company cannot be considered sustainable ______ it measures its actual emissions.', 'unless', 'although', 'so that', 'as if'),
('The campaign aims to raise public ______ of misleading environmental claims.', 'awareness', 'aware', 'awaken', 'awarenesses'),
('Which sentence best expresses a contrast?', 'Although the label was green, the product was not eco-friendly.', 'The label was green because the product was not eco-friendly.', 'The label was green, so the product was not eco-friendly.', 'The label was green in order that the product was not eco-friendly.'),
('A student reads three sources before writing a summary. What skill is demonstrated?', 'Evaluating information', 'Memorising without checking', 'Avoiding comparison', 'Ignoring evidence'),
('The researcher suggested that more data ______ before a decision was made.', 'be collected', 'is collected', 'was collecting', 'has collecting'),
('Which option best combines: “The app tracks rainfall. Farmers can plan irrigation.”', 'By tracking rainfall, the app helps farmers plan irrigation.', 'Despite tracking rainfall, farmers cannot plan irrigation.', 'The app tracks rainfall although farmers planned irrigation.', 'Farmers plan irrigation unless the app tracks rainfall.'),
('A product advertises “zero impact” but provides no measurements. What is the strongest concern?', 'The claim lacks verifiable evidence.', 'The package uses too little colour.', 'The product is necessarily inexpensive.', 'The company has no customers.'),
('Which statement is an inference rather than a directly observed fact?', 'The reduced water bill may encourage other farms to adopt the system.', 'The farm installed two sensors.', 'The bill was issued in June.', 'The pump ran for four hours.'),
('The proposal was rejected, not because it lacked ambition, ______ because it lacked evidence.', 'but', 'nor', 'so', 'or'),
('Choose the best order for a short email: (a) Thank you for your time. (b) Dear Ms Lan, (c) I am writing to request the report. (d) Best regards, Minh.', 'b – c – a – d', 'c – b – d – a', 'b – a – c – d', 'a – b – c – d'),
('Choose the most coherent dialogue: (a) Sure, what time? (b) Would you like to join our study group? (c) At four, in the library.', 'b – a – c', 'a – b – c', 'c – a – b', 'b – c – a'),
('Choose the best order: (a) As a result, less water was wasted. (b) First, sensors measured soil moisture. (c) Finally, the farm recorded lower costs. (d) Then, irrigation was adjusted.', 'b – d – a – c', 'a – b – c – d', 'd – b – a – c', 'b – c – d – a'),
('Which sentence is most suitable as a concluding statement for a paragraph on media literacy?', 'Ultimately, checking evidence is essential to making informed choices.', 'For example, a website was launched on Monday.', 'A student borrowed a book yesterday.', 'The next section describes a different topic.'),
('Choose the best paraphrase: “The device reduced waste without lowering productivity.”', 'Waste fell while output remained stable.', 'Output fell because waste increased.', 'Both waste and output increased.', 'Productivity was reduced to avoid waste.'),
('A paragraph describes a claim, presents contradictory data, and evaluates the source. Its main purpose is to ______.', 'critically assess a claim', 'announce a timetable', 'describe a holiday', 'provide cooking instructions'),
('Which is the best topic sentence for a paragraph about responsible spending?', 'Planning purchases can help teenagers manage money more effectively.', 'Yesterday I bought a blue notebook.', 'The weather was pleasant on Sunday.', 'My cousin prefers swimming to running.'),
('“The plan is feasible provided that sufficient funding is secured.” What does “provided that” express?', 'a condition', 'a contrast', 'a result already achieved', 'a past habit'),
('Choose the sentence with correct inversion.', 'Not only did the scheme save energy, but it also reduced costs.', 'Not only the scheme did save energy, but also reduced costs.', 'Not only did save the scheme energy, but it also reduced costs.', 'Not only the scheme saved energy, but it also reduced costs.'),
('The findings were inconclusive; ______, the researchers called for further trials.', 'consequently', 'in contrast', 'for instance', 'similarly'),
('Which headline is the most neutral and evidence-based?', 'Independent Audit Finds a 12% Reduction in Water Use', 'Miracle Technology Solves Every Environmental Problem', 'All Companies Are Lying About Sustainability', 'The Greatest Invention in Human History'),
('An article cites only a company advertisement to support its environmental claims. Which source would most improve reliability?', 'An independent emissions audit', 'Another advertisement from the same company', 'An anonymous social-media slogan', 'A product photograph'),
('Which statement best explains why correlation alone does not prove causation?', 'Other variables may account for the observed relationship.', 'Two events cannot occur at the same time.', 'Every correlation must be accidental.', 'A larger sample always eliminates bias.'),
('Select the most precise revision: “A lot of people think the system is good.”', 'Survey responses indicate that 78% of users found the system effective.', 'Everyone knows the system is absolutely perfect.', 'The system is good in many ways and things.', 'Some people somewhere might like the system.'),
('Which question most directly tests the credibility of an environmental claim?', 'Can the reported emissions reduction be independently verified?', 'Is the company logo attractive?', 'Does the product come in several colours?', 'Was the advertisement shown on television?'),
('An author first describes a problem, then compares solutions, and ends with a recommendation. The structure is best described as ______.', 'problem–solution–evaluation', 'chronological biography', 'unrelated anecdotes', 'alphabetical listing'),
]

PASSAGES = [
    ('Digital Farming and Evidence', '''At Greenfield Cooperative, farmers share rainfall data, soil-moisture readings and crop records through a common platform. The system recommends when to irrigate, but it does not replace local judgement. During an unusually dry month, sensors indicated that two fields needed less water than expected because their soil retained moisture longer. Farmers followed the measurements and reduced pumping hours. An independent review later confirmed that water consumption had fallen while crop yields remained stable. The cooperative now plans to train new members to interpret data critically rather than accept every automated recommendation.''', [
        ('What is the main purpose of the platform?', 'To support informed farming decisions', 'To replace all farmers', 'To sell advertising space', 'To predict examination results'),
        ('Why did two fields require less irrigation?', 'Their soil retained moisture for longer', 'Their crops had already been harvested', 'The sensors stopped working', 'The farmers ignored the readings'),
        ('Which evidence most strongly supports the claim of improved efficiency?', 'An independent review found lower water use with stable yields', 'The platform had a colourful interface', 'The cooperative posted a slogan', 'Farmers bought new uniforms'),
        ('What can be inferred about the cooperative’s approach to technology?', 'Human judgement remains important alongside data', 'All recommendations are accepted without question', 'Local experience is considered useless', 'Training is no longer necessary'),
        ('Which title best captures the passage?', 'Using Shared Data Responsibly in Agriculture', 'How to Eliminate Farming Completely', 'The History of School Examinations', 'Why Irrigation Should Never Be Measured'),
    ]),
    ('Beyond the Green Label', '''A clothing brand introduced a collection labelled “planet friendly”. Its advertisements highlighted recyclable packaging, but offered no figures on manufacturing emissions. A student research team examined the company’s public reports and found that the new packaging accounted for only a small share of its environmental footprint. The team did not conclude that the brand had made no progress; instead, it asked for clearer targets, independent verification and regular updates. After the findings attracted attention, the company published a detailed emissions inventory and announced a measurable reduction plan. The case illustrates how constructive scrutiny can turn broad marketing language into more accountable commitments.''', [
        ('What did the original advertisements emphasise?', 'Recyclable packaging', 'Verified factory emissions', 'A published emissions inventory', 'A reduction in air travel'),
        ('Why was the student team dissatisfied with the original claim?', 'It lacked information about the larger manufacturing impact', 'The packaging was too colourful', 'The company sold clothing online', 'The advertisements were written in English'),
        ('Which statement best describes the team’s conclusion?', 'The brand needed clearer evidence, not an automatic rejection of all progress', 'The brand had never made any environmental improvement', 'Every green claim is necessarily fraudulent', 'Packaging can never be recycled'),
        ('What happened after the findings gained attention?', 'The company released an emissions inventory and reduction plan', 'The company stopped publishing reports', 'The team withdrew all questions', 'The brand abandoned all manufacturing'),
        ('Which broader lesson is supported by the passage?', 'Verifiable measurements make sustainability claims more accountable', 'Attractive labels are sufficient evidence', 'Only students can assess corporate claims', 'Companies should avoid public targets'),
    ]),
]


def build_items():
    # Level 10, 50 questions: 5 M2, 10 M3, 18 M4, 17 M5.
    levels = [2]*5 + [3]*10 + [4]*13 + [5]*12
    assert len(ROWS) == 40 and len(levels) == 40
    questions = []
    for i, (prompt, correct, *wrong) in enumerate(ROWS, 1):
        opts = [correct] + wrong
        random.Random(202500 + i).shuffle(opts)
        q = {'id': f'{PREFIX}q{i:02}', 'subject': 'tieng_anh', 'grade': '12',
             'lesson': LESSON, 'difficulty': levels[i-1], 'type': 'choice',
             'prompt': prompt, 'options': opts, 'answer': correct}
        validate_question(q)
        questions.append(q)
    groups = []
    for gi, (title, passage, entries) in enumerate(PASSAGES, 1):
        gid = f'{PREFIX}reading{gi}'
        children = []
        for j, (prompt, correct, *wrong) in enumerate(entries, 1):
            opts = [correct] + wrong
            random.Random(202550 + gi*10 + j).shuffle(opts)
            child = {'id': f'{gid}:q{j}', 'difficulty': 4 if gi == 1 else 5,
                     'prompt': prompt, 'options': opts, 'answer': correct}
            validate_question(dict(child, subject='tieng_anh', grade='12', lesson=LESSON, type='choice'))
            children.append(child)
        groups.append({'id': gid, 'subject': 'tieng_anh', 'grade': '12', 'lesson': LESSON,
                       'title': title, 'passage': passage, 'questions': children})
    counts = Counter(q['difficulty'] for q in questions)
    for group in groups:
        counts.update(q['difficulty'] for q in group['questions'])
    assert counts == {2: 5, 3: 10, 4: 18, 5: 17}, counts
    return questions, groups


def install(root, apply=False):
    bank = ExamBank(root)
    questions, groups = build_items()
    existing_questions = bank.questions_path
    existing_groups = bank.readings_path
    raw_questions = json.loads(existing_questions.read_text(encoding='utf-8-sig')) if existing_questions.exists() else []
    raw_groups = json.loads(existing_groups.read_text(encoding='utf-8-sig')) if existing_groups.exists() else []
    if not isinstance(raw_questions, list) or not isinstance(raw_groups, list):
        raise ValueError('Dữ liệu ngân hàng không đúng định dạng danh sách. Không ghi đè.')
    old_q = {q['id']: q for q in raw_questions if isinstance(q, dict) and q.get('id')}
    old_g = {g['id']: g for g in raw_groups if isinstance(g, dict) and g.get('id')}
    conflicts = [q['id'] for q in questions if q['id'] in old_q and old_q[q['id']] != q]
    conflicts += [g['id'] for g in groups if g['id'] in old_g and old_g[g['id']] != g]
    if conflicts:
        raise ValueError('Phát hiện ID mẫu đã được chỉnh sửa; không ghi đè: ' + ', '.join(conflicts[:5]))
    add_q = [q for q in questions if q['id'] not in old_q]
    add_g = [g for g in groups if g['id'] not in old_g]
    print(f'Lesson: {LESSON}; câu đơn mới: {len(add_q)}; nhóm bài đọc mới: {len(add_g)}; tổng câu mẫu: 50')
    if not apply:
        print('DRY RUN: chưa thay đổi dữ liệu. Thêm --apply để cài đặt.')
        return
    if not add_q and not add_g:
        print('Bộ mẫu đã có đầy đủ, không cần ghi dữ liệu hoặc tạo bản sao lưu.')
        return
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    for path in (existing_questions, existing_groups):
        if path.exists():
            backup = path.with_name(f'{path.stem}.backup_{stamp}{path.suffix}')
            shutil.copy2(path, backup)
            print('Sao lưu:', backup)
    from tuhoc.exams.exam_bank import _atomic
    _atomic(existing_questions, raw_questions + add_q)
    _atomic(existing_groups, raw_groups + add_g)
    print('Đã cài mẫu. Không thay đổi exam_config.json hoặc dữ liệu học sinh.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default='.', help='Thư mục chứa main.py')
    parser.add_argument('--apply', action='store_true', help='Sao lưu và nhập mẫu')
    args = parser.parse_args()
    install(Path(args.root).resolve(), apply=args.apply)

if __name__ == '__main__':
    main()
