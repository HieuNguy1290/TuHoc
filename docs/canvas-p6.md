# Bàn giao TuHoc Canvas P1–P6

Mốc P0 là `ba40df1` cộng bộ thử và bản sửa xem trước được ghi trong [báo cáo P0](canvas-p0.md). Các pha sau hoàn thành phần triển khai và kiểm thử Linux. Nghiệm thu trên Windows và học liệu sản xuất đang chờ môi trường/dữ liệu tương ứng.

| Phase | Triển khai | Bằng chứng kiểm thử |
| --- | --- | --- |
| P1 | Đồng nhất hệ tọa độ 960×640, vùng nội dung tối đa 2560 px. Thêm X/Y/W/H, ô nhập, menu và nhãn vị trí đáp án. | Hồi quy P0 104 lượt. Kiểm thử Tk kéo với zoom 110% và gốc đã cuộn, sai số tối đa 1 px khi đối chiếu runtime. Lưu và mở lại ở Y > 640. |
| P2 | Schema v2 pixel trên desktop 960×640, mobile 390×760. Mobile có thể kế thừa desktop và ghi đè riêng. Cả hai giới hạn bốn trang. Thêm template và di trú từng giá trị layout bằng sao lưu, tệp tạm và thay nguyên tử. | Hồi quy P0 104 lượt. Di trú mẫu giữ nguyên byte ngoài layout, chạy lần hai không thay đổi và phục hồi từ .bak. Cố ý làm sai lần xác nhận sau thay file để thử tự động phục hồi. |
| P3 | TokenPicker dùng trong bốn trình soạn, kích thước ô chữ theo bố cục, ngân hàng từ phân trang. Chỉ `picture_missing_letters` được để câu dẫn trống. | Hồi quy P0 104 lượt. Bốn luồng `collect()` qua Tk, bố cục ô chữ hẹp, hội thoại ba người và điều kiện câu dẫn trống qua Curriculum/ExamBank. |
| P4 | Studio ba cột. Thuộc tính pixel, hai khung soạn, mẫu, khôi phục, hoàn tác/làm lại, bám lưới, tự cuộn khi kéo và cảnh báo bản nháp. Khung đầu của renderer Pygame được chuyển về canvas Tk qua ImageTk. | Hồi quy P0 104 lượt. Tk thử chuyển khung, lưu, mở lại, khôi phục trạng thái bằng hoàn tác/làm lại và nhận ảnh. Xem trước qua worker SDL xác minh một khung RGB 960×640, 0 lần chấm, 0 lượt nộp khi bật hoặc tắt phản hồi. |
| P5 | Bổ sung cuộn cho dạng nghe chọn ảnh. Dạng ghép câu/chọn chữ dùng vùng đáp án và thẻ tùy chỉnh. Neo bộ đếm và nút Hoàn thành khi cuộn ở năm dạng P0 ghi nhận. | 26/26 dạng chạy với mặc định, chuẩn hóa cũ, v2 di trú và v2 soạn mới. Bộ v2 soạn mới bấm hitbox sau cuộn ở 26/26 dạng. |
| P6 | Chạy lại bộ hồi quy. Sửa các kiểm tra cũ từng giả định mã bộ đếm đặt trong renderer riêng và registry chỉ có năm dạng mở rộng. Chuẩn bị mã nguồn, bằng chứng và checklist Windows. | Cửa sổ Linux X11/Xvfb thêm 104 lượt. 11 bài kiểm thử mới qua trên Linux. Hai lượt xem trước qua. Diễn tập phục hồi .bak trên bản sao qua. |

## Đối chiếu dữ liệu và hình ảnh

- Ba bộ SDL dummy chạy 104 lượt mỗi bộ. Mỗi bộ gồm lượt đúng và sai trước/sau cuộn trên 26 dạng. Giá trị, kiểu, thứ tự đáp án và 104 dòng `attempts` của mỗi bộ khớp mốc P0. Exam Mode vẫn cho 5/10 câu đúng trên mẫu, một bản ghi JSON và 0 dòng `attempts`.
- 104 ảnh renderer giữa bố cục cũ và v2 di trú giống từng pixel trong bộ chạy cùng font, seed và kích thước. Khung Tk lấy RGB từ chính phiên xem trước trên desktop. Các đường viền thao tác và lưới là lớp hướng dẫn.
- Việc ghi học liệu trên disk chỉ được thử trên bản sao. `content_library.zip` được dùng để kiểm tra hai tệp JSON thực có sẵn, đều thiếu bố cục để di trú. `questions_addon.json`, `demo_exam_questions_grade1_family.json` và bộ lesson/media sản xuất đủ 26 dạng chưa có trong checkout.
- Hai bộ kiểm tra cũ `VERIFY_PATCH11.py` và `VERIFY_PATCH12.py` đã được cập nhật theo bộ đếm dùng chung và registry hiện tại. `run_reading_tests.py` tìm thấy 0 bài vì thiếu `test_reading_pipeline.py`. `check_integration_failures_03c40.py` thiếu đầu vào `full_runtime_03c39.json`.
- Windows DPI, bộ gõ thật, resize bằng người dùng và âm thanh vật lý chưa chạy. Linux X11 dùng sự kiện phát lại và thiết bị âm thanh dummy. Khung mobile được kiểm tra khi soạn và phân giải tọa độ. Cửa sổ học Pygame của ứng dụng chạy desktop.

## Cách chạy lại trên Linux

```bash
python -B tests/canvas_p0.py --layout legacy --output /tmp/tuhoc-legacy
python -B tests/canvas_p0.py --layout migrated --output /tmp/tuhoc-migrated
python -B tests/canvas_p0.py --layout authored --output /tmp/tuhoc-authored
SDL_VIDEODRIVER=x11 xvfb-run -a python -B tests/canvas_p0.py --layout authored --output /tmp/tuhoc-x11
xvfb-run -a python -B -m unittest discover -s tests -p 'test_canvas_*.py' -v
xvfb-run -a python -B tests/canvas_p0_preview.py
xvfb-run -a python -B tests/canvas_p0_preview.py --feedback
python -B VERIFY_PATCH11.py
python -B VERIFY_PATCH12.py
```

Dùng thư mục đầu ra mới cho mỗi lượt. Hai đường kiểm tra độc lập là luồng bài học ghi SQLite và luồng thi ghi JSON, với dữ liệu thử trong thư mục tạm.

## Tệp bàn giao

- Schema và di trú gồm `layout_render.py`, `layout_templates.py`, `layout_migrate.py`, `question_layout_store.py`, `question_layout_runtime.py` và `layout_scroll_extent.py`.
- Soạn và xem trước gồm `question_layout_editor.py`, `level_flow.py`, `token_picker.py`, `new_exercise_editors.py`, `pygame_exercises.py`, `exercise_layout.py` và `exercise_gfx.py`.
- Trình chạy được cập nhật gồm `new_exercise_runtime.py`, `listening_image_choice.py` và các module ảnh, menu, nhập, gạch chân hoặc chọn nhiều trong manifest của gói.
- Câu dẫn và hiển thị kết quả gồm `question_prompt.py`, `upgrade_v2.py`, `exam_bank.py`, `exam_pygame.py`, `pygame_review_panel.py`, `quiz_history_ui.py` và `wrong_answers_ui.py`.
- Bộ thử nằm trong `tests/` và hai script `VERIFY_PATCH11.py`, `VERIFY_PATCH12.py`. Hướng dẫn áp dụng và xác nhận trên Windows nằm trong [HUONG_DAN.txt](../HUONG_DAN.txt).
