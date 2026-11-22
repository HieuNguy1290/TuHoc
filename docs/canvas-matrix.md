# Ma trận bố cục bài học

Các cột mô tả điều khiển được Studio mở và tín hiệu đọc layout trong mã runtime. Hồi quy tương tác chạy riêng bằng tests/canvas_p0.py.

| Dạng | Runtime | Thành phần | Đọc layout | Câu trong gói |
| --- | --- | --- | --- | ---: |
| `audio_multi_select` | `multi_select_extension` | `option_N` | Có | 0 |
| `choice` | `pygame_exercises` | `question_text`, `question_image`, `answer_area`, `option_N` | Có | 115 |
| `conversation_gaps` | `new_exercise_runtime` | `answer_area`, `question_image`, `audio_player`, `word_bank` | Có | 0 |
| `dropdown_fill_blank` | `dropdown_extension` | `dropdown_area`, `answer_area` | Có | 0 |
| `error` | `pygame_exercises` | `question_text`, `question_image`, `input_area`, `answer_area` | Có | 0 |
| `fill` | `pygame_exercises` | `question_text`, `question_image`, `input_area`, `answer_area` | Có | 0 |
| `image_letter_pick` | `image_sentence_extension` | `answer_area`, `question_image`, `option_N` | Có | 0 |
| `image_multi_choice` | `new_exercise_runtime` | `question_image`, `audio_player`, `option_N` | Có | 0 |
| `image_multi_select` | `multi_select_extension` | `option_N` | Có | 0 |
| `image_sentence_fill` | `image_sentence_extension` | `answer_area`, `question_image`, `option_N` | Có | 0 |
| `image_underline_choice` | `underline_extension` | `answer_area`, `option_N` | Có | 0 |
| `image_write_answer` | `image_write_extension` | `question_text`, `question_image`, `input_area`, `answer_area` | Có | 0 |
| `inline_dropdown_fill` | `inline_dropdown_extension` | `question_image`, `dropdown_area`, `answer_area` | Có | 0 |
| `listening_choice` | `pygame_exercises` | `question_text`, `question_image`, `audio_player`, `answer_area`, `option_N` | Có | 0 |
| `listening_fill` | `pygame_exercises` | `question_text`, `question_image`, `audio_player`, `input_area`, `answer_area` | Có | 0 |
| `listening_image_choice` | `listening_image_choice` | `question_image`, `option_N` | Có | 0 |
| `matching` | `pygame_exercises` | `question_text`, `question_image`, `answer_area`, `option_N` | Có | 0 |
| `multi_fill_blanks` | `multi_fill_blanks_extension` | `question_text`, `question_image`, `audio_player`, `answer_area` | Có | 0 |
| `order` | `pygame_exercises` | `question_text`, `question_image`, `answer_area`, `option_N` | Có | 0 |
| `passage_gaps` | `new_exercise_runtime` | `answer_area`, `question_image`, `audio_player`, `word_bank` | Có | 0 |
| `picture_choice` | `pygame_exercises` | `question_text`, `question_image`, `answer_area`, `option_N` | Có | 0 |
| `picture_missing_letters` | `new_exercise_runtime` | `question_image`, `audio_player`, `answer_area`, `option_N` | Có | 0 |
| `sentence_gaps` | `new_exercise_runtime` | `answer_area`, `question_image`, `audio_player`, `word_bank` | Có | 0 |
| `sentence_underline_words` | `underline_extension` | `answer_area` | Có | 0 |
| `text_multi_select` | `multi_select_extension` | `option_N` | Có | 0 |
| `true_false` | `pygame_exercises` | `question_text`, `question_image`, `answer_area`, `option_N` | Có | 0 |
