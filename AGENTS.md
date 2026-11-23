# Hướng dẫn làm việc với TuHoc

Cập nhật ngày **22/11/2026**.

TuHoc là ứng dụng học tập desktop chạy cục bộ. Mã ứng dụng chia theo chức năng dưới `tuhoc/`. Entry point chính là `python -B main.py`. Chạy lệnh từ thư mục gốc chứa `main.py`.

Khi bắt đầu, đọc hướng dẫn này và `docs/STATE.md` nếu tệp bàn giao đó đã có trong nhánh đang làm. Với nhiệm vụ Canvas, đọc thêm `docs/canvas-matrix.md`, `docs/canvas-auto-report.md` và hướng dẫn tại `agents/skills/tuhoc-canvas/`. Dùng checkout hiện có trong cloud. Mỗi task cloud đã có môi trường riêng. Chỉ tạo Git worktree khi người dùng yêu cầu.

## Công nghệ và phụ thuộc

| Thành phần | Công nghệ đang dùng |
| --- | --- |
| Nền tảng | Python **3.12**, Tkinter/ttk và Tcl/Tk cho cửa sổ chính, Studio và công cụ quản trị. |
| Bài tập và thi | Pygame **2.6.1** trên SDL. Khung bài tập thường là 960 × 640. Exam Mode dùng khung riêng 1100 × 720 và chuyển tọa độ chuột từ cửa sổ về khung logic. |
| Hình ảnh và âm thanh | Pillow **13.0.0** cho ảnh và clipboard, NumPy **2.4.3** cho xử lý mảng và dạng sóng, mutagen **1.47.0** cho metadata âm thanh. |
| Lưu trữ | `sqlite3` trong thư viện chuẩn cho hồ sơ, tiến độ học và lịch sử luyện tập. JSON UTF-8 cho học liệu, cấu hình và kết quả Exam Mode. |
| Kiểm thử | `unittest`, pytest dành cho phát triển, các script kiểm tra và bộ phát lại sự kiện Canvas. Xvfb cung cấp màn hình X11 ảo cho kiểm thử GUI trên Linux. |
| Tính năng tùy chọn | `openpyxl` cho Excel, `reportlab` cho PDF, `soundfile` cho một số đường đọc waveform, `soundcard`, `mss`, `opencv-python` (`cv2`) và `imageio-ffmpeg` cho thu âm/quay màn hình, `psutil` cho theo dõi tài nguyên. Một số đường phát/đọc chữ dùng API Windows hoặc `espeak`/`spd-say` trên Linux. Chỉ cài phần cần cho tác vụ. |

## Kiến trúc và luồng dữ liệu

- **Khởi động và điều hướng.** `main.App` là gốc Tk, ghép các mixin của `tuhoc/lessons/upgrade_v2.py`, `tuhoc/lessons/level_flow.py`, `tuhoc/lessons/lesson_flow.py` và các tính năng phụ. `main.Storage` mở SQLite. `tuhoc/app/profile_ui.py` chọn học viên, `tuhoc/app/subject_ui.py` chọn môn, `tuhoc/ui/ui_shell.py` dựng shell và điều hướng các màn.
- **Học và luyện tập.** `upgrade_v2.Curriculum` nạp học liệu, `LearningService` quản lý tiến độ. `LevelFlowMixin` và `LessonFlowMixin` đưa nội dung ra màn hình và mở bài. `GameAppMixin.session_quiz` giao câu hỏi cho `pygame_exercises.launch` và nhận câu trả lời qua callback. `session_finish` ghi tiến độ qua dịch vụ học tập. `tuhoc/storage/quiz_draft_store.py` lưu nháp bài luyện theo học viên, môn, chủ đề và Level.
- **Thi.** `tuhoc/exams/exam_editor.py` mở trình quản lý ngân hàng trong `tuhoc/exams/exam_bank_pygame.py`. `ExamBank` đọc, kiểm tra, lưu câu hỏi và chọn đề theo lớp, môn, bài, Level và hạn mức M1–M5. `exam_pygame.ExamUI` điều khiển phiên thi, dùng `exam_grading.is_correct` và lưu kết quả JSON qua `ExamBank.save_result`. `tuhoc/exams/exam_history_bridge.py` đọc kết quả theo học viên và bộ lọc môn cho `tuhoc/ui/quiz_history_ui.py`. Exam Mode có các mã môn `tieng_anh`, `tieng_viet` và `toan`. Luồng này có bộ chấm và nơi ghi riêng với bài luyện.
- **Soạn và xem trước.** Trình sửa câu hỏi trong `tuhoc/lessons/level_flow.py` gọi `question_layout_editor.edit_layout`. Studio chỉnh bản nháp và chỉ trả dữ liệu cho biểu mẫu khi lưu. Biểu mẫu xác thực rồi ghi JSON. Xem trước gọi cùng renderer Pygame với `allow_feedback=False` và callback ảnh khung hình. Khi kiểm tra xem trước, xác nhận không có lượt chấm, lượt nộp hay bản ghi kết quả.
- **Tk và SDL.** Tk sở hữu widget và vòng lặp chính. `tuhoc/exercises/pygame_exercises.py` quản lý worker SDL và chuyển kết quả về Tk bằng callback đã lên lịch. `tuhoc/exercises/pygame_session_guard.py` dành quyền sử dụng cửa sổ SDL độc lập cho một phiên. Giữ khởi tạo và dọn SDL trên luồng sở hữu phiên. Dùng API đóng phiên hiện có khi điều hướng hoặc thoát ứng dụng.

## Bản đồ tệp theo trách nhiệm

Mã ứng dụng nằm trong các package `tuhoc/app/`, `tuhoc/lessons/`, `tuhoc/exercises/`, `tuhoc/studio/`, `tuhoc/exams/`, `tuhoc/ui/` và `tuhoc/storage/`. Tài nguyên đi kèm nằm trong `assets/`. Lấy đường dẫn gốc bằng `tuhoc.paths.PROJECT_ROOT` khi cần mở tài nguyên hoặc dữ liệu đặt cạnh bản cài.

| Khu vực | Tệp và vai trò |
| --- | --- |
| Điểm vào và học liệu | `main.py` (launcher), `tuhoc/app/main.py` (ứng dụng, hồ sơ, SQLite), `tuhoc/lessons/upgrade_v2.py` (dịch vụ học và phiên luyện đang được app import), `tuhoc/lessons/unified_subjects.py` (khởi tạo thư viện từng môn, tìm media), `tuhoc/storage/content_manager.py` (quản lý học liệu), `tuhoc/storage/safe_storage.py` (ghi JSON có staging, backup, rollback), `tuhoc/storage/quiz_draft_store.py` (nháp bài luyện). |
| Điều hướng và hồ sơ | `tuhoc/ui/ui_shell.py`, `tuhoc/ui/home_ui.py`, `tuhoc/app/profile_ui.py`, `tuhoc/app/subject_ui.py`, `tuhoc/app/subject_loading_screen.py`, `assets/subject_loading_background.png`, `tuhoc/lessons/lesson_map_ui.py`, `tuhoc/app/navigation_profiler.py`. |
| UI dùng chung | `tuhoc/ui/ui_tokens.py`, `tuhoc/ui/theme_config.py` (token tương thích và catalog chủ đề), `tuhoc/ui/strings_vi.py`, `tuhoc/ui/ui_components.py`, `tuhoc/ui/ui_dialogs.py`, `tuhoc/ui/ui_errors.py`, `tuhoc/ui/ui_keys.py`, `tuhoc/ui/ui_grid.py`, `tuhoc/ui/ui_line_dot.py`, `tuhoc/ui/ui_motion.py`, `tuhoc/ui/panel_animations.py`, `tuhoc/ui/card_motion.py`, `tuhoc/ui/icon_animations.py`, `tuhoc/ui/drag_scroll.py`, `tuhoc/ui/wheel_scroll.py`, `tuhoc/ui/mouse_effects.py`. |
| Bài học, tập đọc, flashcard | `tuhoc/lessons/lesson_flow.py`, `tuhoc/lessons/level_flow.py`, `tuhoc/lessons/lesson_display_names.py`, `tuhoc/lessons/lesson_wrap_layout.py`, `tuhoc/lessons/pygame_lesson_window.py`, `tuhoc/lessons/pygame_embedded_reader.py`, `tuhoc/lessons/pygame_reading_studio.py`, `tuhoc/lessons/reading_pygame_transition.py`, `tuhoc/lessons/reading_editor.py`, `tuhoc/lessons/floating_vocabulary.py`, `tuhoc/lessons/vocab_sync.py`. |
| Quản trị và biểu mẫu | `tuhoc/studio/admin_editor.py`, `tuhoc/studio/multi_block_editor.py`, `tuhoc/studio/studio_list.py`, `tuhoc/studio/exercise_authoring_help.py`, `tuhoc/studio/new_exercise_editors.py`, `tuhoc/studio/token_picker.py`. |
| Studio bố cục | `tuhoc/studio/question_layout_editor.py` (Tk canvas), `tuhoc/studio/question_layout_store.py` (schema), `tuhoc/studio/question_layout_runtime.py` (tra geometry), `tuhoc/studio/layout_registry.py` (dạng bài và điều khiển editable), `tuhoc/studio/layout_render.py` (phép chiếu), `tuhoc/studio/layout_edit_geometry.py` (kéo/căn/chia), `tuhoc/studio/layout_images.py` (fit ảnh), `tuhoc/studio/layout_templates.py` (mẫu và áp dụng hàng loạt), `tuhoc/studio/layout_scroll_extent.py` (vùng cuộn), `layout_migrate.py` (di trú/khôi phục), `tuhoc/studio/extras_render.py` (hộp văn bản tĩnh). |
| Runtime bài tập | `tuhoc/exercises/pygame_exercises.py` (dispatch và các dạng cũ), `tuhoc/exercises/new_exercise_runtime.py` (các dạng mới), `tuhoc/exercises/exercise_buttons.py`, `tuhoc/exercises/exercise_focus_ui.py`, `tuhoc/exercises/exercise_gfx.py`, `tuhoc/exercises/exercise_image_zoom.py`, `tuhoc/exercises/exercise_layout.py`, `tuhoc/exercises/question_prompt.py`, `tuhoc/exercises/question_rich_text.py`, `tuhoc/exercises/matching_widget.py`, `tuhoc/exercises/dragon_feedback.py`. |
| Renderer theo dạng | `tuhoc/exercises/dropdown_extension.py`, `tuhoc/exercises/dropdown_inline_logic.py`, `tuhoc/exercises/inline_dropdown_extension.py`, `tuhoc/exercises/image_letter_pick_extension.py`, `tuhoc/exercises/image_sentence_extension.py`, `tuhoc/exercises/image_write_extension.py`, `tuhoc/exercises/listening_image_choice.py`, `tuhoc/exercises/listening_image_extension.py`, `tuhoc/exercises/multi_fill_blanks_extension.py`, `tuhoc/exercises/multi_select_extension.py`, `tuhoc/exercises/underline_extension.py`. Kiểm tra dispatch thực tế trước khi sửa một module có tên tương tự. |
| Cửa sổ và media SDL | `tuhoc/exercises/pygame_session_guard.py`, `tuhoc/exercises/pygame_window_utils.py`, `tuhoc/ui/pygame_exit_dialog.py`, `tuhoc/exercises/pygame_soak_monitor.py`, `tuhoc/exercises/pygame_media_support.py`, `tuhoc/exercises/pygame_waveform.py`. |
| Thi và ngân hàng đề | `tuhoc/exams/exam_bank.py`, `tuhoc/exams/exam_bank_pygame.py`, `tuhoc/exams/exam_editor.py`, `tuhoc/exams/exam_grading.py`, `tuhoc/exams/exam_history_bridge.py`, `exam_media_migrate.py`, `tuhoc/exams/exam_pygame.py`, `tools/fixtures/seed_family_grade1.py`. Seed Family lớp 1 vẫn có nơi gọi trong Exam Mode. |
| Học liệu kiểm tra lớp 2 | `exam_content/__init__.py`, `exam_content/grade2.py` (tạo câu theo mã ổn định và nạp vào hồ sơ), `exam_content/grade2_math.py` (câu Toán), `exam_content/grade2_vietnamese.py` (câu Tiếng Việt), `docs/exam-grade2.md` (hướng dẫn và ma trận độ khó). |
| Kết quả và ôn tập | `tuhoc/ui/quiz_history_ui.py`, `tuhoc/ui/wrong_answers_ui.py`, `tuhoc/ui/learning_analytics_ui.py`, `tuhoc/ui/ui_results_dashboard.py`, `tuhoc/exercises/pygame_review_panel.py`, `tuhoc/exercises/pygame_results.py`, `tuhoc/exercises/new_exercise_review.py`, `tuhoc/ui/result_insights.py`, `tuhoc/exercises/review_normalize.py`. |
| Âm thanh, ghi âm và trò chơi | `tuhoc/lessons/learning_audio.py`, `tuhoc/ui/waveform_player.py`, `tuhoc/ui/animated_media.py`, `tuhoc/storage/recording_tools.py`, `tools/audio/recorder_app.py`, `tuhoc/ui/floating_recorder.py`, `tuhoc/lessons/dictation_vi.py`, `tuhoc/lessons/minigames.py`, `tuhoc/lessons/modern_games.py`. |
| Script dữ liệu và chẩn đoán | `tools/fixtures/make_demo.py`, `tools/fixtures/install_family_grade12_level10.py`, `tools/fixtures/them_cau_hoi_ve2.py` có thể ghi dữ liệu. `tools/checks/audit_layout_coverage.py` xuất báo cáo bố cục. `tuhoc/app/freeze_diagnostics.py` là tệp rỗng ở mốc rà soát. Kiểm tra cả import động và điểm gọi trước khi dời script. |
| Bộ kiểm tra ở gốc | `tools/checks/check_coordinate_contracts.py`, `tools/checks/check_editor_drag_zoom_persistence.py`, `tools/checks/check_editor_reopen_persistence.py`, `tools/checks/check_exam_v3.py`, `tools/checks/check_extras_contract.py`, `tools/checks/check_integration_contracts.py`, `tools/checks/check_integration_failures_03c40.py`, `tools/checks/check_layout_json_consistency.py`, `tools/checks/check_layout_matrix.py`, `tools/checks/check_layout_scroll.py`, `tools/checks/check_legacy_runtime_regression.py`, `tools/checks/check_studio_shortcuts.py`, `tools/checks/check_studio_ui.py`, `tools/checks/check_studio_v3.py`, `tools/checks/check_ui_components.py`, `tools/checks/check_ui_contrast.py`, `tools/checks/check_ui_keys.py`, `tools/checks/check_ui_strings.py`, `tools/checks/check_ui_tokens.py`, `tools/checks/VERIFY_PATCH03.py`, `tools/checks/VERIFY_PATCH11.py`, `tools/checks/VERIFY_PATCH12.py`, `tools/checks/VERIFY_PHASE4_PATCH07.py`, `tools/checks/run_reading_tests.py`. |
| Bộ kiểm thử trong `tests/` | `tests/conftest.py` chọn checkout qua `TUHOC_ROOT`. `tests/test_canvas_layout.py` và `tests/test_canvas_studio.py` kiểm tra Canvas. `tests/canvas_p0.py` phát lại thao tác, `tests/canvas_p0_cases.py` cung cấp fixture, `tests/canvas_p0_preview.py` kiểm tra xem trước. `tests/test_exam_bank.py`, `tests/test_exam_grading.py`, `tests/test_exam_state.py` và `tests/test_exam_grade2.py` là pytest cho Exam Mode. |
| Công cụ phát triển | `tools/audit_ui_tokens.py` kiểm kê token, `tools/analyze_nav_log.py` tổng hợp log, `tools/measure_ui_pages.py` đo dựng màn hình trên checkout và hồ sơ thử riêng. `tools/reference/exam_logic_reference.py` và `tools/reference/exam_state_reference.py` là kịch bản rà soát lưu để tham chiếu. Dùng pytest trong `tests/` để xác minh Exam Mode. |
| Hướng dẫn và lịch sử | `AGENTS.md`, `HUONG_DAN.txt`, `docs/canvas-p0.md`, `docs/canvas-p6.md`, `docs/canvas-matrix.md`, `docs/canvas-auto-log.md`, `docs/canvas-auto-report.md`, `docs/ui-auto-log.md`, `docs/ui-auto-report.md`, `agents/skills/tuhoc-canvas/SKILL.md`, `agents/skills/tuhoc-canvas/references/build-plan.md`. |
| Tệp dữ liệu theo dõi bởi Git | `content_library` là tệp đánh dấu trong checkout. Các gói dữ liệu cũ và bytecode đã được gỡ khỏi checkout. Cài mới từ mã nguồn và chọn dữ liệu cần nhập vào thư mục riêng. |

## Danh mục dạng bài và bố cục

### Khung chung của bài luyện

- Pygame dựng bài trên khung logic desktop **960 × 640**. Studio có thêm khung thiết kế **390 × 760** cho mobile. Khi mobile thiếu vị trí riêng, dùng phép chiếu từ desktop. Tọa độ và kích thước của layout v2/v3/v4 dùng pixel, đo từ góc trên bên trái vùng nội dung. Phần thiết kế cuộn dọc tối đa 4 trang. Zoom của Studio chỉ đổi cách nhìn. [Hệ tọa độ](tuhoc/studio/layout_render.py) · [Lưu và chiếu layout](tuhoc/studio/question_layout_store.py)
- Cột **Vùng Studio** liệt kê phần tử mà registry cho chỉnh. `question_text` là câu dẫn, `question_image` là khung ảnh câu hỏi, `audio_player` là khung nghe, `answer_area` là vùng chứa đáp án, `input_area` là ô nhập, `dropdown_area` là vùng menu và `word_bank` là ngân hàng từ. `option_N` dùng chỉ số từ 0, theo vị trí thẻ hoặc ô mà renderer quy định. Kiểm tra cách renderer ánh xạ chỉ số sang đáp án khi có xáo thẻ. [Registry](tuhoc/studio/layout_registry.py) · [Runtime layout](tuhoc/studio/question_layout_runtime.py)
- **Hoàn thành** và bộ đếm câu nằm ngoài phần bố cục được chỉnh. Hộp văn bản tự do trong `extras` v3 chỉ dùng để trình bày. Ảnh đã đặt khung có các chế độ `contain`, `cover` và `stretch` ở những renderer áp dụng `image_fit`. Tọa độ mặc định ở Studio và lệnh **Dùng mẫu** là điểm bắt đầu khi soạn. Với câu chưa lưu layout, renderer tính vị trí theo nội dung, chẳng hạn số dòng câu dẫn, kích thước ảnh, số đáp án và số dòng chữ trên thẻ. [Schema](tuhoc/studio/question_layout_store.py) · [Mẫu](tuhoc/studio/layout_templates.py) · [Phép đặt ảnh](tuhoc/studio/layout_images.py)

Mẫu desktop dựng sẵn trong `template_for` dùng các hình chữ nhật dưới đây theo thứ tự `(x, y, width, height)`. Bảng này mô tả mẫu khi người soạn áp dụng, còn vị trí gốc của từng renderer được mô tả ở danh mục bên dưới. [Mã mẫu](tuhoc/studio/layout_templates.py)

| Điều kiện trong registry | Khung mẫu desktop |
| --- | --- |
| Có câu dẫn chỉnh được | `question_text (58, 104, 844, 96)` |
| Có ô nhập | `input_area (72, 352, 816, 55)` |
| Có menu thả xuống | `dropdown_area (173, 304, 346, 48)` |
| Có ngân hàng từ | `answer_area (65, 265, 810, 165)` và `word_bank (65, 505, 825, 35)` |
| Có vùng đáp án thông thường | `answer_area (65, 240, 810, 170)` |

### 26 dạng bài luyện trong Lesson và Level

| Mã dạng và tên | Cách bố trí và thao tác mặc định | Vùng Studio | Renderer |
| --- | --- | --- | --- |
| `choice` · Đọc và chọn một đáp án | Câu dẫn tự xuống dòng ở trên. Các thẻ chữ A/B/C… xếp bên dưới. Bấm một thẻ rồi xác nhận. | `question_text`, `question_image`, `answer_area`, `option_N` | `tuhoc/exercises/pygame_exercises.py` |
| `picture_choice` · Nhìn hình và chọn một đáp án | Ảnh minh họa đặt giữa câu dẫn và cụm thẻ chữ theo luồng nội dung. Bấm icon để phóng ảnh và chọn một thẻ. | `question_text`, `question_image`, `answer_area`, `option_N` | `tuhoc/exercises/pygame_exercises.py` |
| `true_false` · Đúng hoặc sai | Câu khẳng định ở trên và hai thẻ bên dưới. Khi học liệu thiếu lựa chọn, renderer dùng Đúng/Sai mặc định. | `question_text`, `question_image`, `answer_area`, `option_N` | `tuhoc/exercises/pygame_exercises.py` |
| `fill` · Điền đáp án | Câu dẫn và ảnh nếu có ở trên. Một ô nhập rộng ở dưới, văn bản cuộn ngang trong ô khi quá dài. | `question_text`, `question_image`, `input_area` | `tuhoc/exercises/pygame_exercises.py` |
| `error` · Tìm và sửa lỗi | Câu dẫn chứa nội dung cần sửa, có thể kèm ảnh. Người học nhập phần sửa vào một ô văn bản. | `question_text`, `question_image`, `input_area` | `tuhoc/exercises/pygame_exercises.py` |
| `order` · Sắp xếp thẻ | Vùng kết quả hiện thứ tự đã chọn, tiếp theo là lưới thẻ nguồn. Mặc định 4 cột cho thẻ ngắn hoặc 2 cột khi có thẻ dài. Có nút xóa để làm lại. | `question_text`, `question_image`, `answer_area`, `answer_preview`, `option_N` | `tuhoc/exercises/pygame_exercises.py` |
| `matching` · Nối cặp | Hai cột thẻ chữ, ảnh hoặc hỗn hợp. Bấm một mục bên trái rồi bấm mục tương ứng bên phải. Đường nối và nút xóa cặp thuộc cùng bố cục câu. | `question_text`, `question_image`, `answer_area`, `option_N` | `tuhoc/exercises/pygame_exercises.py` |
| `listening_choice` · Nghe và chọn chữ | Trình phát hoặc waveform ở sau câu dẫn, ảnh minh họa tùy chọn bên dưới trình phát, rồi đến các thẻ chữ chọn một. | `question_text`, `question_image`, `audio_player`, `answer_area`, `option_N` | `tuhoc/exercises/pygame_exercises.py` |
| `listening_fill` · Nghe và điền | Cùng vùng nghe và ảnh tùy chọn như Nghe và chọn chữ. Phía dưới là một ô nhập thay cho các thẻ. | `question_text`, `question_image`, `audio_player`, `input_area` | `tuhoc/exercises/pygame_exercises.py` |
| `listening_image_choice` · Nghe và chọn ảnh | Thanh nghe ở trên, ảnh minh họa câu riêng nếu có. Lưới thẻ ảnh đáp án nằm bên dưới, tối đa 3 cột theo số thẻ. Cuộn vùng nội dung và bấm ảnh để chọn. Vùng nghe theo renderer. | `question_text`, `question_image`, `audio_player`, `option_N` | `tuhoc/exercises/listening_image_choice.py` |
| `image_multi_choice` · Chọn một ảnh | Câu dẫn ở trên, minh họa tùy chọn tách khỏi ảnh đáp án. Các thẻ ảnh A/B/C… mặc định theo lưới 3 cột. Icon phóng ảnh bám theo ảnh thực tế. Chọn một ảnh. | `question_text`, `question_image`, `audio_player`, `option_N` | `tuhoc/exercises/new_exercise_runtime.py` |
| `picture_missing_letters` · Nhìn hình và gõ chữ thiếu | Ảnh gợi ý trên hàng chữ. Chữ đã biết hiện trực tiếp, chữ ẩn hiện thành các ô có thể chọn và gõ. Hàng chữ xuống dòng theo bề rộng. `option_0` chỉnh kích thước ô chữ dùng chung. | `question_text`, `question_image`, `audio_player`, `answer_area`, `option_N`, `slot_N` | `tuhoc/exercises/new_exercise_runtime.py` |
| `sentence_gaps` · Ghép từ vào câu | Câu chạy theo dòng, các ô trống nằm đúng vị trí trong câu. Chọn ô rồi chọn thẻ từ ở ngân hàng phía dưới. Ngân hàng phân trang khi thiếu chỗ. | `question_text`, `answer_area`, `question_image`, `audio_player`, `word_bank`, `slot_N`, `word_N` | `tuhoc/exercises/new_exercise_runtime.py` |
| `passage_gaps` · Hoàn thành đoạn văn | Đoạn văn xuống dòng và cuộn trong vùng đọc. Ô trống xen giữa các từ, ngân hàng từ nằm dưới vùng cuộn. | `question_text`, `answer_area`, `question_image`, `audio_player`, `word_bank`, `slot_N`, `word_N` | `tuhoc/exercises/new_exercise_runtime.py` |
| `conversation_gaps` · Hoàn thành hội thoại | Mỗi lượt thoại có tên người nói trước nội dung. Ô trống theo thứ tự lượt thoại và dòng, ngân hàng từ dùng chung bên dưới. | `question_text`, `answer_area`, `question_image`, `audio_player`, `word_bank`, `slot_N`, `word_N` | `tuhoc/exercises/new_exercise_runtime.py` |
| `image_multi_select` · Nhìn hình và chọn nhiều | Một ảnh câu hỏi ở trên, các thẻ chữ có ô dấu ✓ ở dưới, mặc định 2 cột. Bấm lại cùng thẻ để bỏ chọn. Ảnh minh họa theo luồng trình bày cố định. | `question_text`, `question_image`, `answer_area`, `option_N` | `tuhoc/exercises/multi_select_extension.py` |
| `text_multi_select` · Đọc và chọn nhiều | Câu dẫn và đoạn đọc tùy chọn ở trên. Các thẻ chữ có ô dấu ✓, mặc định 2 cột phía dưới. Chiều cao hàng theo thẻ nhiều dòng nhất. | `question_text`, `question_image`, `answer_passage`, `answer_area`, `option_N` | `tuhoc/exercises/multi_select_extension.py` |
| `audio_multi_select` · Nghe và chọn nhiều | Nút **Nghe lại** trước lưới 2 cột. Thẻ chữ có ô dấu ✓ và cho bật/tắt từng mục. Vùng nghe theo renderer. | `question_text`, `question_image`, `audio_player`, `answer_area`, `option_N` | `tuhoc/exercises/multi_select_extension.py` |
| `image_write_answer` · Nhìn hình và ghi đáp án | Câu dẫn, ảnh có thể phóng to và một ô gõ đáp án xếp theo trục dọc. Khi cuộn, ô nhập đi cùng ảnh và nội dung câu. | `question_text`, `question_image`, `input_area` | `tuhoc/exercises/image_write_extension.py` |
| `image_underline_choice` · Nhìn hình và gạch chân từ | Ảnh minh họa phía trên. Từ hoặc cụm từ phía dưới là vùng bấm, hiện gạch chân khi được chọn. Học liệu có thể yêu cầu một hoặc nhiều từ. | `question_text`, `question_image`, `answer_area`, `option_N` | `tuhoc/exercises/underline_extension.py` |
| `sentence_underline_words` · Gạch chân từ trong câu | Câu được chia thành các từ bấm được, xếp theo thứ tự đọc và xuống dòng trong vùng đáp án. Đánh dấu ngay trên từ đã chọn. | `question_text`, `answer_area`, `option_N` | `tuhoc/exercises/underline_extension.py` |
| `dropdown_fill_blank` · Chọn từ danh sách thả xuống | Một ô chọn nằm dưới câu dẫn và ảnh tùy chọn. Bấm ô mở danh sách rồi chọn một mục. Bản nhiều ô chuyển sang renderer menu nội tuyến. | `question_text`, `question_image`, `dropdown_area`, `answer_menu`, `option_N` | `tuhoc/exercises/dropdown_extension.py` |
| `multi_fill_blanks` · Gõ vào nhiều ô | Câu dẫn, thanh nghe hoặc ảnh tùy nội dung. Các ô nhập nằm ngay trong câu, chữ và ô cùng xuống dòng. Bấm vào ô để nhập hoặc chuyển bằng Tab. | `question_text`, `question_image`, `audio_player`, `answer_area`, `slot_N` | `tuhoc/exercises/multi_fill_blanks_extension.py` |
| `image_sentence_fill` · Nhìn hình và bấm từ | Ảnh, phần nghe nếu có, câu có chỗ trống, rồi các thẻ từ ở dưới. Bấm ô để chọn chỗ điền và bấm thẻ để đưa từ vào ô. `option_N` là thẻ từ. | `question_text`, `answer_area`, `question_image`, `audio_player`, `option_N`, `slot_N` | `tuhoc/exercises/image_sentence_extension.py` |
| `image_letter_pick` · Nhìn hình và bấm chữ cái | Dùng cùng bố cục ảnh, chỗ trống và hàng thẻ như dạng điền từ. Thẻ là chữ cái, các đoạn thuộc cùng một từ được giữ gần nhau khi xuống dòng. | `question_text`, `answer_area`, `question_image`, `audio_player`, `option_N`, `slot_N` | `tuhoc/exercises/image_letter_pick_extension.py` gọi `tuhoc/exercises/image_sentence_extension.py` |
| `inline_dropdown_fill` · Chọn từ ngay trong câu | Câu dẫn và ảnh tùy chọn, rồi văn bản có các ô menu kèm theo. Mỗi ô mở danh sách riêng tại vị trí trong dòng. Các ô xuống dòng cùng phần văn bản. | `question_text`, `question_image`, `dropdown_area`, `answer_menu`, `slot_N` | `tuhoc/exercises/inline_dropdown_extension.py` |

### Dạng câu trong Exam Mode

Exam Mode dùng khung logic **1100 × 720**. Đồng hồ và tiến độ ở trên, danh sách điều hướng ở bên phải, điều khiển chuyển nhóm và nộp bài ở dưới. Vùng câu hỏi cuộn nằm ở `(68, 260, 694, 331)`. Với câu đơn, layout desktop được chiếu theo khung nội dung `(694, 640)`, rồi cắt phần đang thấy vào vùng câu hỏi. Tọa độ trong bảng dưới đây tính theo vùng nội dung hoặc dàn trang riêng của Exam Mode. [Renderer thi](tuhoc/exams/exam_pygame.py) · [Dạng được ngân hàng chấp nhận](tuhoc/exams/exam_bank.py)

| Mã dạng | Bố cục trong Exam Mode |
| --- | --- |
| `choice` | Câu dẫn rồi các thẻ lựa chọn chữ xếp dọc. Đoạn đọc đơn lẻ nếu có nằm trên câu dẫn và cuộn cùng câu. |
| `true_false` | Cùng vùng thẻ chữ, hai lựa chọn theo thứ tự đã lưu trong câu. |
| `picture_choice` | Khối ảnh minh họa phía trên câu dẫn và các thẻ đáp án chữ xếp dọc. |
| `image_multi_choice` | Các thẻ đáp án ảnh xếp dọc, gắn nhãn A/B/C… với vùng bấm theo từng thẻ. |
| `listening_choice` | Nút phát lại trong vùng cuộn, tiếp theo là ảnh nếu có, câu dẫn và các lựa chọn chữ. |
| `fill` | Câu dẫn, dòng hướng dẫn và một ô nhập văn bản. Có thể dùng `input_area` của layout để dời ô. |
| `error` | Hiện từ hoặc cụm từ sai trước ô nhập, người học gõ phần sửa. |
| `picture_missing_letters` | Hiện câu dẫn và một ô nhập văn bản. Ảnh xuất hiện trong nhánh câu tương tác khi có cả tệp ảnh và cấu hình `question_image`. |
| `listening_fill` | Nút phát lại sau câu dẫn và một ô nhập ở dưới. |
| `sentence_gaps` | Câu dẫn chứa vị trí đánh số, các ô nhập đánh số xếp dọc. Bấm vào ô hoặc dùng Tab để chuyển ô. |
| `conversation_gaps` | Hội thoại nằm trong câu dẫn, mỗi chỗ trống có một ô nhập riêng bên dưới. |
| `passage_gaps` | Đoạn có chỗ trống nằm trong câu dẫn, các ô nhập theo thứ tự chỗ trống bên dưới. |
| `order` | Dòng kết quả đang ghép, lưới thẻ 4 cột và nút **Làm lại**. |
| `matching` | Hai cột chữ có thể bấm, hiển thị cặp đang chọn hoặc đã nối. Exam Mode hiện xác thực chế độ chữ ↔ chữ. |
| `reading_group` · Nhóm bài đọc | Bài đọc bên trái rộng 320 px, ngăn cách 12 px với cột câu hỏi bên phải. Hai bên cuộn độc lập. Nhóm gồm 2–10 câu con trắc nghiệm, giữ nguyên thứ tự và được đưa vào đề theo nhóm. Hộp văn bản v3 đi theo cột câu hỏi. |

Dạng `reading_group` là cấu trúc trong trình soạn và dữ liệu nhóm. Khi tạo đề, mỗi câu con là `choice` có mã nhóm. Các dạng điền từ của Exam Mode dùng ô gõ, còn phần luyện Lesson/Level dùng ngân hàng từ. [Trình soạn ngân hàng](tuhoc/exams/exam_bank_pygame.py) · [Cách ráp nhóm](tuhoc/exams/exam_bank.py)

### Định dạng và Chỉnh bố cục v4

- Chọn một phần tử chữ để đặt phông, cỡ chữ, đậm, nghiêng và gạch chân. Câu dẫn và đoạn đọc có thêm căn lề và giãn dòng. Dùng **Định dạng đoạn chữ…** và bôi đen chữ trong câu dẫn, đoạn đọc hoặc hộp văn bản. Nút **B/I/U**, phông và cỡ chữ áp dụng ngay trên đoạn đang chọn. Dùng **Ctrl+B/I/U**, **Ctrl+Z/Y** hoặc lưu để thấy định dạng ngay trên Canvas. Dấu **đậm** của câu hỏi cũ vẫn được hỗ trợ. Chữ gạch chân do người soạn đặt và dấu gạch đánh dấu đáp án là hai lớp hiển thị. [Đo và vẽ chữ](tuhoc/studio/layout_typography.py) · [Studio](tuhoc/studio/question_layout_editor.py)
- `slot_N` bám theo ô trống trong nội dung. `word_N` là vị trí của thẻ trong thứ tự hiển thị. `answer_preview` là khung câu đã xếp, `answer_menu` là khung danh sách thả xuống, `answer_passage` là vùng đọc và `answer_panel` là khung câu hỏi con. **Tự động bố trí** xóa phần tọa độ và kích thước đặt riêng của thành phần. [Danh sách điều khiển](tuhoc/studio/layout_registry.py)
- Trong trình sửa Ngân hàng kiểm tra, dùng **Chỉnh bố cục** cho từng dạng hoặc cho hai khung của bài đọc. Dùng **Bố cục câu con** để sửa câu được chọn. **Xem trước Pygame** dựng một khung từ bản nháp bằng renderer của màn hình thi. Chọn **Lưu câu hỏi** hoặc **Lưu bài đọc** để ghi vào ngân hàng. [Ngân hàng](tuhoc/exams/exam_bank_pygame.py) · [Pygame](tuhoc/exams/exam_pygame.py)
- Thanh **Định dạng chữ** ở trên canvas chứa phông, cỡ chữ và các nút **B/I/U**. Khi đổi cỡ bằng tay nắm, Studio cập nhật viền và hình ngay trong lúc kéo rồi đồng bộ với khung hình mới từ Pygame.
- Kéo trên phần nội dung tĩnh để cuộn trang chính. Thanh cuộn Pygame nhận kéo đến hai đầu, kể cả khi chuột đi ra ngoài rãnh. Kéo bằng nút giữa để di chuyển trong canvas Studio. [Cuộn Tk](tuhoc/ui/drag_scroll.py) · [Thanh cuộn Pygame](tuhoc/exercises/pygame_scroll.py)
- Trên **Máy tính**, Studio dựng hình bài thật trong một tiến trình Pygame riêng, nhận tọa độ từ chính renderer, rồi dùng tọa độ đó cho khung kéo. **Thử làm bài** gửi thao tác tới bản nháp và không ghi tiến trình. Dùng **Chỉnh bố cục** để trở về chế độ kéo. Khung **Điện thoại** vẫn dùng canvas thiết kế. [Mô phỏng trực tiếp](tuhoc/studio/studio_live_preview.py) · [Studio](tuhoc/studio/question_layout_editor.py)
- Kiểm tra v4 bằng `tests/test_canvas_v4.py`, các ca Studio liên quan và `tests/canvas_p0.py --layout v4`. Kết quả phát lại kiểm tra luồng làm bài và chấm cho 26 dạng. Kiểm tra mức bao phủ từng thuộc tính cần các ca thay đổi riêng giá trị của thuộc tính đó.

### Đường hiển thị Tk cũ

Nội dung cũ qua `exercise_focus_ui.exercise` vẫn nhận `picture` (ảnh và ô trả lời), `dictation` (thanh nghe, tốc độ, âm lượng và ô trả lời), `reading` (câu dẫn và ô trả lời), cùng `matching` và `error` dưới dạng ô văn bản có gợi ý nếu có. Luồng `LessonFlowMixin.quiz_question` dùng nút chọn dọc cho `choice`, `true_false`, `matching` có phương án, và dùng ô nhập cho các câu còn lại. Các đường Tk này bố trí bằng widget và không tra khóa Studio. Chính tả chuyên biệt, flashcard và trò chơi có màn riêng. [Bài tập Tk](tuhoc/exercises/exercise_focus_ui.py) · [Quiz cũ](tuhoc/lessons/lesson_flow.py)

## Quy ước khi sửa code

1. Giữ phạm vi đúng theo yêu cầu. Dùng helper và lớp đã có. Ưu tiên logic thuần có thể kiểm thử ngoài Tk/SDL. Giữ nguyên API, kiểu trả về và callback mà các màn hiện tại đang gọi, trừ hành vi được yêu cầu đổi.
2. Với thay đổi UI, dùng `tuhoc/ui/ui_tokens.py`, thành phần chung và `tuhoc/ui/strings_vi.py` khi phù hợp. Giữ phím gõ cho Entry/Text/Combobox, giữ điều hướng bàn phím và tùy chọn giảm chuyển động. Dùng `after` cho cập nhật Tk từ kết quả nền, hủy tác vụ đã lên lịch khi trang hoặc widget bị đóng.
3. Với câu hỏi, giữ ID, nội dung, đáp án, thứ tự và kiểu giá trị trả về. Chỉ sửa chấm, tiến trình hoặc điểm thưởng khi yêu cầu nêu rõ. Nếu thay đổi chấm thi, chạy các test Exam Mode và giữ ca bảo vệ cho câu hỏi cũ.
4. Với Canvas, giữ hỗ trợ layout cũ chuẩn hóa, v2 pixel, v3 có `extras`, v4 có thuộc tính định dạng và câu không có layout. Đọc geometry qua `question_layout_runtime.element` và registry hiện tại. Tính hitbox từ cùng hình chữ nhật dùng để vẽ. Áp phép cuộn đúng một lần. Khung mobile là 390 × 760, phạm vi thiết kế tối đa 4 trang. Nút **Hoàn thành** và bộ đếm câu là phần tử khóa. Hộp văn bản là nội dung trang trí.
5. Với dữ liệu, dùng bản sao hoặc fixture tạm. Giữ nguyên dữ liệu người dùng hiện có. Dùng cơ chế lưu đã có của miền tương ứng. Dùng `safe_storage.commit_json` cho thao tác ghi JSON nhiều tệp. Các lệnh sửa dữ liệu hàng loạt cần có bản sao lưu và đường khôi phục. Không bổ sung dịch vụ mạng hay phụ thuộc runtime chỉ để chạy kiểm thử.
6. Dùng UTF-8 cho tệp mới và giữ tiếng Việt có dấu trong nhãn, fixture và thông báo. Ưu tiên tên mô tả và xử lý ngoại lệ cụ thể ở biên UI/I/O. Tránh đổi định dạng hàng loạt. Khi dọn mã, xác minh điểm gọi tĩnh, động và các script khởi chạy. Lưu hiện vật cần giữ trong `_archive/` theo quy trình dọn dẹp đã chọn.
7. Báo cáo lệnh đã chạy cùng số ca đạt, lỗi, bỏ qua và `xfail`. Khi sửa một lỗi có `xfail(strict=True)`, cập nhật đánh dấu tương ứng sau khi ca kiểm thử đạt. Chuyển sang kiểm thử đồ họa thực trên Windows nếu thay đổi chạm DPI, IME, thiết bị âm thanh hoặc quản lý cửa sổ.

## Cài đặt và chạy từ mã nguồn

### Windows

Dùng Python 3.12 có Tcl/Tk. Chạy trong PowerShell ở gốc dự án.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install pygame==2.6.1 Pillow==13.0.0 numpy==2.4.3 mutagen==1.47.0
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -B main.py
```

### Linux

Dùng Python 3.12 có Tkinter và một phiên đồ họa đang hoạt động để dùng tương tác. Nếu cần kiểm thử tự động, cài Xvfb và xauth qua trình quản lý gói của môi trường.

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install pygame==2.6.1 Pillow==13.0.0 numpy==2.4.3 mutagen==1.47.0
python -m pip check
python -B main.py
```

Trong workspace cloud đã chuẩn bị, có thể dùng `/workspace/.tuhoc/venv` và thêm `/workspace/.tuhoc/xvfb/usr/bin` vào `PATH` nếu các đường dẫn này tồn tại. Kiểm tra ứng dụng bằng việc cửa sổ chọn hồ sơ tiếng Việt hiển thị.

### Dữ liệu và triển khai

- Hồ sơ mặc định ở `%LOCALAPPDATA%/TuHocBeta/`, hoặc `~/AppData/Local/TuHocBeta/` nếu biến `LOCALAPPDATA` chưa được đặt. SQLite ở `tu_hoc.sqlite3`. Exam Mode dùng `content_library/exam_questions.json`, `exam_reading_groups.json`, `exam_config.json`, `exam_results.json` và `exam_media/` dưới hồ sơ.
- `tuhoc/lessons/unified_subjects.py` khởi tạo `mon_hoc/tieng_anh/` hoặc `mon_hoc/tieng_viet/` bên cạnh mã nguồn. Mỗi môn có `content_library/level_*.json` và thư mục ảnh. Thiết lập hiển thị ở `mon_hoc/hien_thi.json`. Khi thử khởi động hay thử một luồng ghi, dùng bản sao mã nguồn và thư mục `LOCALAPPDATA` tạm. Thiết lập `LOCALAPPDATA` tách hồ sơ, còn bản sao mã nguồn tách học liệu từng môn.
- Khi nâng bản cài đang dùng, sao lưu thư mục hồ sơ và `mon_hoc/`, đóng app, cập nhật mã nguồn rồi mở app và kiểm tra hồ sơ, bài học, thi và lịch sử. Chỉ nhập các tệp học liệu thực sự cần. Giữ kết quả thi và hồ sơ tách biệt với fixture. Trên bản sao JSON có layout, `python -B layout_migrate.py ban_sao.json --version 3` nâng lên v3 và tạo `.bak`. `python -B layout_migrate.py ban_sao.json --restore` khôi phục nội dung từ `.bak`. Mặc định di trú là v2.
- Quy trình phát hành được kiểm chứng ở checkout này là chạy từ mã nguồn. Checkout có nhánh xử lý runtime đóng gói, nhưng hiện thiếu recipe PyInstaller, tệp `.spec` và cấu hình CI phát hành. Với yêu cầu phát hành `.exe`, xác minh recipe, tài nguyên và phụ thuộc trong một tác vụ đóng gói riêng rồi nghiệm thu trên Windows.
- Với cloud, giữ script cài đặt và hướng dẫn khởi động trong cấu hình môi trường khi có cấu hình đó. Quy trình **Publish** trong Environment Settings dùng cho các máy cloud sau. Một cửa sổ Tk/SDL cần được khởi động lại trong mỗi phiên.

### Bộ câu hỏi kiểm tra lớp 2

- Mở **Ngân hàng kiểm tra → Danh sách câu hỏi → Nạp bộ lớp 2** để thêm 100 câu Toán và 100 câu Tiếng Việt. Trong **Kiểm tra**, chọn môn → **Lớp 2 → Ôn tập lớp 2** rồi chọn Level. Giáo viên có thể chỉnh đoạn văn kèm câu trắc nghiệm qua **Sửa đoạn đọc**.
- `ExamBank.add_text_questions` xác thực cả lô trước khi ghi, giữ câu đã có theo ID và sao lưu ngân hàng hiện có dưới `content_library/backups/` khi có câu mới. Khi sửa nguồn học liệu, giữ ID đã phát hành và kiểm tra số câu theo từng môn và mức. Phân bổ hiện tại của mỗi môn là **35 / 15 / 15 / 18 / 17** từ M1 đến M5 để đáp ứng cấu hình mặc định của đủ 10 Level với đề tối đa 50 câu.
- Soạn câu dẫn bằng tiếng Việt tự nhiên ở miền Nam và dùng chính tả chuẩn cho đáp án. Để nạp từ dòng lệnh, đóng ứng dụng và chạy `python -B -m exam_content.grade2 --root "/duong/dan/den/TuHocBeta"` từ gốc dự án. Khi kiểm thử, trỏ `--root` về thư mục tạm. Xem [hướng dẫn bộ lớp 2](docs/exam-grade2.md) để tra các dạng bài và ma trận nội dung.

## Làm việc tiết kiệm usage

### Đọc ít

- Với tệp lớn như `main.py`, `tuhoc/exercises/pygame_exercises.py`, `tuhoc/lessons/level_flow.py` và `tuhoc/lessons/upgrade_v2.py`, dùng `rg -n "tên_hàm_hoặc_lớp"` rồi đọc đúng khoảng dòng cần thiết.
- Không đọc lại tệp đã đọc trong cùng phiên, trừ khi chính bạn vừa sửa tệp đó.
- Chỉ đọc `docs/STATE.md` và tài liệu liên quan đến tác vụ. Với Canvas, xem mục lục trước rồi đọc mục cần thiết. Chỉ đọc log lịch sử `docs/canvas-auto-log.md` và `docs/ui-auto-log.md` khi được yêu cầu.
- Không quét, liệt kê hay mở `content_library.zip`, `__pycache__.zip`, `_archive/`, `mon_hoc/`, ảnh, JSON học liệu lớn, log điều hướng và `.venv/`.

### Tác vụ → tệp cần đọc → kiểm thử tối thiểu

| Tác vụ | Đọc trước | Kiểm thử tối thiểu |
| --- | --- | --- |
| Chấm thi, chọn đề | `tuhoc/exams/exam_grading.py`, `tuhoc/exams/exam_bank.py` | `tests/test_exam_grading.py` hoặc `tests/test_exam_bank.py` bằng pytest |
| Trạng thái phiên thi | `tuhoc/exams/exam_pygame.py` | `tests/test_exam_state.py` bằng pytest |
| Bộ câu hỏi lớp 2 | `exam_content/grade2*.py`, `docs/exam-grade2.md` | `tests/test_exam_grade2.py` bằng pytest |
| Kéo/căn/chia trong Studio | `tuhoc/studio/layout_edit_geometry.py` | `tools/checks/check_editor_drag_zoom_persistence.py`, `tools/checks/check_studio_shortcuts.py` |
| Schema/geometry layout | `tuhoc/studio/question_layout_store.py`, `tuhoc/studio/question_layout_runtime.py` | `tools/checks/check_layout_json_consistency.py`, `tools/checks/check_coordinate_contracts.py` |
| Cuộn trong Studio | `tuhoc/studio/layout_scroll_extent.py` | `tools/checks/check_layout_scroll.py` |
| Chuỗi giao diện | `tuhoc/ui/strings_vi.py` | `tools/checks/check_ui_strings.py` |
| Token, màu, tương phản | `tuhoc/ui/ui_tokens.py`, `tuhoc/ui/theme_config.py` | `tools/checks/check_ui_tokens.py`, `tools/checks/check_ui_contrast.py` |
| Phím tắt UI | `tuhoc/ui/ui_keys.py` | `tools/checks/check_ui_keys.py` |
| Renderer một dạng bài | Xác định module từ dispatch trong `tuhoc/exercises/pygame_exercises.py`, rồi đọc module tương ứng | `tools/checks/check_legacy_runtime_regression.py` và phát lại riêng dạng đó bằng `tests/canvas_p0.py` |
| Lưu JSON, sao lưu | `tuhoc/storage/safe_storage.py` | pytest hoặc check liên quan miền đó |

Nếu tác vụ không khớp dòng nào, dùng `rg` để tìm đúng tệp rồi mới đọc.

### Thang kiểm thử

Chạy từ gốc dự án. Chạy một script kiểm tra bằng `python -B -m tools.checks.check_layout_matrix` hoặc thay tên module theo tác vụ. Báo cáo tạo tại `tools/checks/reports/`. Các script `VERIFY_PATCH*` là kiểm tra lịch sử theo từng bản, còn bảng tác vụ ở trên chỉ các kiểm tra dùng cho mã hiện hành. Đi theo các tầng liên quan từ nhẹ đến nặng. Dừng khi đủ bằng chứng và xử lý lỗi ở tầng hiện tại trước khi chạy tầng cao hơn.

1. Một ca hoặc một tệp pytest bằng `python -B -m pytest -p no:cacheprovider -x -q --tb=short <tệp>`.
2. Các script `check_*.py` bảo vệ hợp đồng vừa sửa.
3. Canvas unittest và xem trước trên Xvfb khi sửa Studio, layout hoặc preview.
4. Phát lại 26 dạng bài bằng `tests/canvas_p0.py` khi sửa runtime bài tập hoặc geometry dùng chung.

Lệnh cho tầng 3 và 4 khi cần chạy:

```bash
xvfb-run -a python -B -m unittest discover -s tests -p 'test_canvas_*.py' -v
SDL_AUDIODRIVER=dummy xvfb-run -a python -B tests/canvas_p0_preview.py
SDL_AUDIODRIVER=dummy xvfb-run -a python -B tests/canvas_p0_preview.py --feedback

tuhoc_run_dir=$(mktemp -d)
SDL_VIDEODRIVER=x11 xvfb-run -a python -B tests/canvas_p0.py --layout v3 --output "$tuhoc_run_dir/v3"
```

Dùng `--type <mã_dạng>` để phát lại riêng một dạng. Dùng `--layout legacy`, `--layout migrated`, `--layout authored` hoặc `--layout v4` khi cần kiểm tra tương thích Canvas. Với script ghi JSON hoặc log cạnh mã nguồn, dùng bản sao checkout và hồ sơ tạm. Đặt `TU_HOC_PROFILE=0` để tắt ghi log điều hướng khi kiểm thử.

### Giới hạn đầu ra

- Với lệnh có đầu ra dài, dùng `| tail -n 40` và bật `pipefail` trong Bash để giữ mã lỗi của lệnh kiểm thử. Dùng `-q --tb=short` với pytest. Chỉ trích dòng lỗi liên quan khi báo cáo.
- Chạy tuần tự các phiên Xvfb và các ca mở cửa sổ Tk/SDL để tránh tranh display.

### Baseline đã biết

Mốc 22/11/2026 có **64 ca pytest đạt và 9 ca `xfail`** trong Exam Mode. Tra bảng này khi cần và tránh chạy lại chỉ để tái hiện baseline.

| Tệp | Ca `xfail` | Lý do |
| --- | --- | --- |
| `tests/test_exam_grading.py` | `test_fill_accepts_repeated_spaces` | Chấm đáp án điền chưa chuẩn hóa khoảng trắng lặp ở giữa câu. |
| `tests/test_exam_grading.py` | `test_fill_accepts_canonically_equivalent_vietnamese` | Chấm đáp án điền chưa chuẩn hóa Unicode tiếng Việt tương đương. |
| `tests/test_exam_state.py` | `test_gap_returns_to_unanswered_when_last_value_is_erased` | Danh sách ô đã xóa hết vẫn được tính là đã trả lời. |
| `tests/test_exam_state.py` | `test_matching_requires_all_pairs` | Nối chưa đủ cặp vẫn được tính là đã trả lời. |
| `tests/test_exam_state.py` | `test_whitespace_only_fill_is_unanswered` | Đáp án chỉ có khoảng trắng vẫn được tính là đã trả lời. |
| `tests/test_exam_state.py` | `test_progress_excludes_empty_and_incomplete_answers` | Thanh tiến độ đếm cả câu trả lời rỗng hoặc chưa hoàn tất. |
| `tests/test_exam_bank.py` | `test_invalid_question` với `difficulty=None` | Dữ liệu thiếu độ khó làm phát sinh `TypeError`. |
| `tests/test_exam_bank.py` | `test_invalid_question` với `difficulty=2.7` | Độ khó thập phân bị cắt thành số nguyên. |
| `tests/test_exam_bank.py` | `test_invalid_question` với `sequence=["a", "a "]` | Từ trùng trong bài sắp xếp lọt qua xác thực khi có khoảng trắng thừa. |

- Bộ lớp 2 đã dựng đủ 200 câu, tạo được 1.000 tổ hợp môn, Level và số lượng câu, và nộp thử đề ở cả hai môn trên Linux/Xvfb.
- Checkout thiếu `full_runtime_03c39.json` cho `tools/checks/check_integration_failures_03c40.py` và `test_reading_pipeline.py` cho `tools/checks/run_reading_tests.py`. Bỏ qua hai script này và giữ nguyên mã.
- Trên Linux, ghi **chưa kiểm** đối với các mục cần Windows như DPI 100/125/150%, IME Telex/VNI, thiết bị âm thanh, clipboard và luồng phát hành `.exe`.

### Môi trường

- Nếu có `/workspace/.tuhoc/venv`, dùng `/workspace/.tuhoc/venv/bin/python` để tránh tạo lại môi trường hoặc cài lại gói. Kiểm tra phụ thuộc khi cần bằng `python -B -c "import pygame, PIL, numpy, mutagen"` với Python đã chọn.
- Tk thiếu `DISPLAY` thì chạy bằng `xvfb-run -a`. Nếu thiếu `xauth`, thêm `/workspace/.tuhoc/xvfb/usr/bin` vào `PATH`.
- Khi SDL báo lỗi thiết bị âm thanh, đặt `SDL_AUDIODRIVER=dummy`.
- Khi pytest không tìm thấy checkout, đặt `TUHOC_ROOT` về thư mục gốc dự án. Giá trị mặc định là thư mục hiện hành.

### Điều kiện dừng

- Nếu kiểm thử vẫn lỗi sau hai lần sửa, dừng và hỏi người dùng, kèm lỗi còn lại và nguyên nhân nghi ngờ.
- Hỏi trước khi đổi cách chấm thi, định dạng dữ liệu hoặc schema, đóng gói `.exe`, hoặc ghi vào dữ liệu người dùng thật.
- Giữ thay đổi trong phạm vi yêu cầu. Không refactor, đổi tên, định dạng lại hay dọn mã ngoài phạm vi. Với vấn đề ngoài phạm vi, ghi một dòng trong báo cáo.

### Báo cáo cuối

Giữ khoảng 10 dòng trở xuống. Nêu các tệp đã sửa và mục đích từng tệp, lệnh kiểm thử đã chạy với số ca đạt, lỗi, bỏ qua và `xfail`, phần chưa kiểm được và việc còn lại hoặc câu hỏi nếu có.

### Ghi `docs/STATE.md`

Ghi đè thay vì nối thêm lịch sử. Giữ tối đa ba mục ngắn **Đang làm**, **Quyết định đã chốt** và **Việc còn lại**. Xóa mục đã hoàn tất.
