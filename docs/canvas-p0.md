# TuHoc Canvas P0 · Chuẩn hồi quy

Mốc gốc là `ba40df1`. Registry bài học và registry Pygame cùng có 26 dạng. Bộ thử chạy trên Linux với canvas 960×640, SDL dummy, DejaVu Sans và seed 2600.

## Kết quả

- **26/26 dạng** có ca đúng, sai và biên qua bộ chấm hiện tại. **104/104 lượt phát lại** trả về đúng giá trị, kiểu và thứ tự dự kiến. Mỗi lượt bấm Hoàn thành khi chưa trả lời, sau đó bấm tâm vùng tương tác và chọn, nối, sắp xếp hoặc nhập qua vòng lặp sự kiện của renderer.
- **25/26 dạng** nhận click vào vùng đáp án sau khi cuộn. `listening_image_choice` được bấm ở vị trí đang hiện cả trước lẫn sau sự kiện bánh xe. Renderer này chưa có nhánh cuộn.
- **104 dòng SQLite** qua luồng nộp bài thật, 26 dòng mỗi lượt. Trước khi nộp đủ câu, bảng `attempts` có 0 dòng cho người học thử. Gọi kết thúc lần nữa không ghi trùng. Kiểm tra riêng Exam Mode nộp 10 câu mẫu, chấm đúng 5 câu, lưu một bản ghi JSON và tạo 0 dòng `attempts`.
- **104 ảnh PNG của renderer** ghi khung bắt đầu và khung trước khi Hoàn thành của ca đúng ở hai bố cục. JSON bằng chứng lưu tâm click, hitbox, độ cuộn, đáp án trước tuần tự hóa và dòng SQLite. Ba PNG khác trong thư mục fixture là ảnh mẫu.
- **Xem trước trên Tk/Xvfb.** Mã gốc gọi chấm một lần nếu hiệu ứng phản hồi bật. Bản sửa ở `level_flow.py` và `pygame_exercises.py` bỏ qua phản hồi chấm điểm khi xem trước. Sau sửa, cả hai chế độ bật và tắt hiệu ứng đều có **0 lần gọi chấm, 0 lượt nộp và 0 bản ghi kết quả**. Dữ liệu đã lưu được đối chiếu theo byte.

## Ma trận 26 dạng

Các dòng dưới đây dùng callback của `session_quiz`, rồi `session_finish` → `LearningService.save_answer` → `Storage.record`. Giá trị thô được giữ đến lúc kết thúc bài và ghi vào `attempts.answer` kiểu SQLite `text`. Exam Mode có đường riêng qua `exam_grading.is_correct` → `ExamBank.save_result`. [Luồng bài học](../upgrade_v2.py) · [SQLite](../main.py) · [Luồng thi](../exam_pygame.py)

| Dạng | Renderer | Thao tác và kiểu trả về | Bộ chấm bài học |
| --- | --- | --- | --- |
| `choice` | `pygame_exercises` | Chọn ô → `str` | So đáp án được chấp nhận |
| `picture_choice` | `pygame_exercises` | Chọn ô có ảnh câu hỏi → `str` | So đáp án được chấp nhận |
| `true_false` | `pygame_exercises` | Chọn Đúng/Sai → `str` | So đáp án được chấp nhận |
| `listening_choice` | `pygame_exercises` | Chọn ô → `str` | So đáp án được chấp nhận |
| `fill` | `pygame_exercises` | Nhập ô → `str` | So đáp án được chấp nhận |
| `listening_fill` | `pygame_exercises` | Nhập ô → `str` | So đáp án được chấp nhận |
| `error` | `pygame_exercises` | Nhập từ sửa → `str` | So đáp án được chấp nhận |
| `order` | `pygame_exercises` | Chọn hết thẻ → `str` ghép theo thứ tự | Chuẩn hóa thứ tự thẻ |
| `matching` | `pygame_exercises` | Nối hết trái/phải → `dict[int, int]` | So số cặp và ánh xạ chỉ số gốc |
| `listening_image_choice` | `listening_image_choice` | Chọn ảnh → `str` tham chiếu | So đáp án được chấp nhận |
| `image_multi_choice` | `new_exercise_runtime` | Chọn ảnh → `str` tham chiếu | So tham chiếu ảnh |
| `picture_missing_letters` | `new_exercise_runtime` | Chọn ô, nhập chữ → `str` đã ghép | So không phân biệt hoa thường |
| `sentence_gaps` | `new_exercise_runtime` | Chọn ô và từ → `list[str]` theo ô | So từ ẩn theo thứ tự |
| `passage_gaps` | `new_exercise_runtime` | Chọn ô và từ → `list[str]` theo ô | So từ ẩn theo thứ tự |
| `conversation_gaps` | `new_exercise_runtime` | Chọn ô và từ → `list[str]` theo ô | So từ ẩn theo lượt thoại và ô |
| `image_multi_select` | `multi_select_extension` | Chọn nhiều → `list[str]` theo thứ tự hiển thị | So số lượng và tập đáp án |
| `text_multi_select` | `multi_select_extension` | Chọn nhiều → `list[str]` theo thứ tự hiển thị | So số lượng và tập đáp án |
| `audio_multi_select` | `multi_select_extension` | Chọn nhiều → `list[str]` theo thứ tự hiển thị | So số lượng và tập đáp án |
| `image_write_answer` | `image_write_extension` | Nhập ô → `str` | Chuẩn hóa Unicode, khoảng trắng, hoa thường |
| `image_underline_choice` | `underline_extension` | Chọn từ → `str` ở biến thể chọn một | So từ hoặc tập từ |
| `sentence_underline_words` | `underline_extension` | Chọn từ → `list[int]` theo chỉ số | So tập chỉ số |
| `dropdown_fill_blank` | `dropdown_extension` | Mở menu và chọn → `str` ở biến thể một ô | So chuỗi đã bỏ khoảng trắng hai đầu |
| `multi_fill_blanks` | `multi_fill_blanks_extension` | Bấm và nhập từng ô → `list[str]` | So đáp án từng ô |
| `image_sentence_fill` | `image_sentence_extension` | Bấm ô và thẻ từ → `list[str]` | So từng ô hoặc theo nhóm khai báo |
| `image_letter_pick` | `image_letter_pick_extension` → `image_sentence_extension` | Bấm ô và thẻ chữ → `list[str]` | So từng ô hoặc theo nhóm khai báo |
| `inline_dropdown_fill` | `inline_dropdown_extension` | Mở từng menu và chọn → `list[str]` | So đáp án từng ô |

Biến thể một ô của `dropdown_fill_blank` và một đáp án của `image_underline_choice` là các fixture chính. Menu nhiều ô được thử ở renderer đích `inline_dropdown_fill`. Nhánh chuyển tiếp nhiều ô và biến thể gạch chân nhiều lựa chọn chưa được phát lại riêng.

## Nơi đọc bố cục

| Nơi đọc | Dữ liệu sử dụng |
| --- | --- |
| `question_layout_store.get_layout`, `question_layout_runtime.element` | Xác thực bố cục chuẩn hóa và đổi sang pixel. Nút Hoàn thành và bộ đếm là khóa không cho sửa. |
| `layout_scroll_extent.content_bottom` | Đọc phần tử hợp lệ để tìm cạnh dưới nội dung. |
| `level_flow.question_editor`, `question_layout_editor` | Nạp bố cục đã lưu, xác thực khi lưu và chuyển bố cục nháp đến renderer xem trước. |
| `pygame_exercises._run` | `answer_area`, `option_N` cho lựa chọn, sắp xếp và nối. Ô nhập đọc `answer_area`. Bài nghe đọc thêm `audio_player`. |
| `listening_image_choice._run` | `option_N`. Khi có tọa độ riêng, thẻ giữ thứ tự gốc. |
| `new_exercise_runtime.run` | `audio_player` cho lời đọc, `option_N` cho chọn ảnh, `answer_area` và `question_image` cho từ/chữ thiếu. |
| `multi_select_extension.run` | `option_N`. |
| `image_write_extension.run` | `question_text`, `question_image`, `answer_area` hoặc `input_area`. |
| `underline_extension.run` | `answer_area`, thêm `option_N` ở chọn từ bằng ảnh. |
| `dropdown_extension.run` | `answer_area`. Biến thể nhiều ô đi qua renderer menu nội tuyến. |
| `multi_fill_blanks_extension.run` | `question_text`, `question_image`, `audio_player`, `answer_area`. |
| `image_sentence_extension.run`, `image_letter_pick_extension.run` | `option_N`. Khi có tọa độ riêng, thẻ giữ thứ tự gốc. |
| `inline_dropdown_extension.run` | `dropdown_area` hoặc `answer_area`. |

`layout` trên khối bài đọc ở `level_flow`, `multi_block_editor` và `pygame_lesson_window` mô tả kiểu trình bày khối. Canvas câu hỏi dùng đối tượng hình học riêng.

## Hành vi gốc và giới hạn

Tâm nút Hoàn thành dịch lên 65 px sau một nấc cuộn trong `image_write_answer`, `image_underline_choice`, `sentence_underline_words`, `dropdown_fill_blank` và `inline_dropdown_fill`. Bộ đếm cũng cuộn theo nội dung trong các fixture này. P0 ghi nhận hình học gốc. Bản sửa ứng dụng giới hạn ở luồng xem trước.

`content_library.zip` có 115 câu Exam Mode thuộc `choice` và hai nhóm đọc gồm 10 câu con. Các câu và nhóm trong gói chưa có bố cục đã lưu. P0 dùng ảnh màu, WAV im lặng, văn bản và bố cục tự tạo. Checkout thiếu bộ bài học có đủ 26 dạng, media tương ứng, `questions_addon.json` và `demo_exam_questions_grade1_family.json`. Windows và thiết bị âm thanh thật chưa được xác minh.

## Chạy lại

Dùng Python có Pygame và Pillow từ thư mục gốc. `--output` nhận một thư mục mới. `--font` nhận đường dẫn font nếu chạy trên máy có cấu hình khác.

```bash
python -B tests/canvas_p0.py --output /tmp/tuhoc-p0-run
xvfb-run -a python -B tests/canvas_p0_preview.py
xvfb-run -a python -B tests/canvas_p0_preview.py --feedback
```

Trước và sau sửa, `VERIFY_PATCH03.py`, `VERIFY_PHASE4_PATCH07.py`, `check_coordinate_contracts.py`, `check_editor_drag_zoom_persistence.py`, `check_editor_reopen_persistence.py`, `check_integration_contracts.py`, `check_layout_json_consistency.py`, `check_layout_scroll.py`, `check_legacy_runtime_regression.py` và `audit_layout_coverage.py` đều thoát mã 0. `VERIFY_PATCH11.py` và `VERIFY_PATCH12.py` cùng giữ lỗi kiểm tra chuỗi mã nguồn cũ của bộ đếm. `VERIFY_PATCH12.py` còn kỳ vọng registry chỉ có năm dạng mở rộng. `run_reading_tests.py` có 0 bài do thiếu `test_reading_pipeline.py`.

File ứng dụng sửa là `level_flow.py` và `pygame_exercises.py`. Đáp án, hàm chấm, logic xáo, kiểm tra hợp lệ và schema lưu điểm giữ nguyên.
