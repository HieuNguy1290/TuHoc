# Hướng dẫn làm việc với TuHoc

TuHoc là ứng dụng học tập desktop chạy cục bộ. Nhánh hiện tại dùng kiến trúc mô-đun Python ở gốc dự án. Entry point chính là `python -B main.py`. Chạy lệnh từ thư mục chứa `main.py` và `exam_bank.py`.

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

- **Khởi động và điều hướng.** `main.App` là gốc Tk, ghép các mixin của `upgrade_v2.py`, `level_flow.py`, `lesson_flow.py` và các tính năng phụ. `main.Storage` mở SQLite. `profile_ui.py` chọn học viên, `subject_ui.py` chọn môn, `ui_shell.py` dựng shell và điều hướng các màn.
- **Học và luyện tập.** `upgrade_v2.Curriculum` nạp học liệu, `LearningService` quản lý tiến độ. `LevelFlowMixin` và `LessonFlowMixin` đưa nội dung ra màn hình và mở bài. `GameAppMixin.session_quiz` giao câu hỏi cho `pygame_exercises.launch` và nhận câu trả lời qua callback. `session_finish` ghi tiến độ qua dịch vụ học tập. `quiz_draft_store.py` lưu nháp bài luyện theo học viên, môn, chủ đề và Level.
- **Thi.** `exam_editor.py` mở trình quản lý ngân hàng trong `exam_bank_pygame.py`. `ExamBank` đọc, kiểm tra, lưu câu hỏi và chọn đề theo lớp, môn, bài, Level và hạn mức M1–M5. `exam_pygame.ExamUI` điều khiển phiên thi, dùng `exam_grading.is_correct` và lưu kết quả JSON qua `ExamBank.save_result`. `exam_history_bridge.py` đọc kết quả theo đúng học viên cho `quiz_history_ui.py`. Luồng này có bộ chấm và nơi ghi riêng với bài luyện.
- **Soạn và xem trước.** Trình sửa câu hỏi trong `level_flow.py` gọi `question_layout_editor.edit_layout`. Studio chỉnh bản nháp và chỉ trả dữ liệu cho biểu mẫu khi lưu. Biểu mẫu xác thực rồi ghi JSON. Xem trước gọi cùng renderer Pygame với `allow_feedback=False` và callback ảnh khung hình. Khi kiểm tra xem trước, xác nhận không có lượt chấm, lượt nộp hay bản ghi kết quả.
- **Tk và SDL.** Tk sở hữu widget và vòng lặp chính. `pygame_exercises.py` quản lý worker SDL và chuyển kết quả về Tk bằng callback đã lên lịch. `pygame_session_guard.py` dành quyền sử dụng cửa sổ SDL độc lập cho một phiên. Giữ khởi tạo và dọn SDL trên luồng sở hữu phiên. Dùng API đóng phiên hiện có khi điều hướng hoặc thoát ứng dụng.

## Bản đồ tệp theo trách nhiệm

| Khu vực | Tệp và vai trò |
| --- | --- |
| Điểm vào và học liệu | `main.py` (ứng dụng, hồ sơ, SQLite), `upgrade_v2.py` (dịch vụ học và phiên luyện đang được app import), `unified_subjects.py` (khởi tạo thư viện từng môn, tìm media), `content_manager.py` (quản lý học liệu), `safe_storage.py` (ghi JSON có staging, backup, rollback), `quiz_draft_store.py` (nháp bài luyện). |
| Điều hướng và hồ sơ | `ui_shell.py`, `home_ui.py`, `profile_ui.py`, `subject_ui.py`, `subject_loading_screen.py`, `subject_loading_background.png`, `lesson_map_ui.py`, `navigation_profiler.py`. |
| UI dùng chung | `ui_tokens.py`, `theme_config.py` (token tương thích và catalog chủ đề), `strings_vi.py`, `ui_components.py`, `ui_dialogs.py`, `ui_errors.py`, `ui_keys.py`, `ui_grid.py`, `ui_line_dot.py`, `ui_motion.py`, `panel_animations.py`, `card_motion.py`, `icon_animations.py`, `drag_scroll.py`, `wheel_scroll.py`, `mouse_effects.py`. |
| Bài học, tập đọc, flashcard | `lesson_flow.py`, `level_flow.py`, `lesson_display_names.py`, `lesson_wrap_layout.py`, `pygame_lesson_window.py`, `pygame_embedded_reader.py`, `pygame_reading_studio.py`, `reading_pygame_transition.py`, `reading_editor.py`, `floating_vocabulary.py`, `vocab_sync.py`. |
| Quản trị và biểu mẫu | `admin_editor.py`, `multi_block_editor.py`, `studio_list.py`, `exercise_authoring_help.py`, `new_exercise_editors.py`, `token_picker.py`. |
| Studio bố cục | `question_layout_editor.py` (Tk canvas), `question_layout_store.py` (schema), `question_layout_runtime.py` (tra geometry), `layout_registry.py` (dạng bài và điều khiển editable), `layout_render.py` (phép chiếu), `layout_edit_geometry.py` (kéo/căn/chia), `layout_images.py` (fit ảnh), `layout_templates.py` (mẫu và áp dụng hàng loạt), `layout_scroll_extent.py` (vùng cuộn), `layout_migrate.py` (di trú/khôi phục), `extras_render.py` (hộp văn bản tĩnh). |
| Runtime bài tập | `pygame_exercises.py` (dispatch và các dạng cũ), `new_exercise_runtime.py` (các dạng mới), `exercise_buttons.py`, `exercise_focus_ui.py`, `exercise_gfx.py`, `exercise_image_zoom.py`, `exercise_layout.py`, `question_prompt.py`, `question_rich_text.py`, `matching_widget.py`, `dragon_feedback.py`. |
| Renderer theo dạng | `dropdown_extension.py`, `dropdown_inline_logic.py`, `inline_dropdown_extension.py`, `image_letter_pick_extension.py`, `image_sentence_extension.py`, `image_write_extension.py`, `listening_image_choice.py`, `listening_image_extension.py`, `multi_fill_blanks_extension.py`, `multi_select_extension.py`, `underline_extension.py`. Kiểm tra dispatch thực tế trước khi sửa một module có tên tương tự. |
| Cửa sổ và media SDL | `pygame_session_guard.py`, `pygame_window_utils.py`, `pygame_exit_dialog.py`, `pygame_soak_monitor.py`, `pygame_media_support.py`, `pygame_waveform.py`. |
| Thi và ngân hàng đề | `exam_bank.py`, `exam_bank_pygame.py`, `exam_editor.py`, `exam_grading.py`, `exam_history_bridge.py`, `exam_media_migrate.py`, `exam_pygame.py`, `seed_family_grade1.py`. Seed Family lớp 1 vẫn có nơi gọi trong Exam Mode. |
| Kết quả và ôn tập | `quiz_history_ui.py`, `wrong_answers_ui.py`, `learning_analytics_ui.py`, `ui_results_dashboard.py`, `pygame_review_panel.py`, `pygame_results.py`, `new_exercise_review.py`, `result_insights.py`, `review_normalize.py`. |
| Âm thanh, ghi âm và trò chơi | `learning_audio.py`, `waveform_player.py`, `animated_media.py`, `recording_tools.py`, `recorder_app.py`, `floating_recorder.py`, `dictation_vi.py`, `minigames.py`, `modern_games.py`. |
| Script dữ liệu và chẩn đoán | `make_demo.py`, `install_family_grade12_level10.py`, `them_cau_hoi_ve2.py` có thể ghi dữ liệu. `audit_layout_coverage.py` xuất báo cáo bố cục. `freeze_diagnostics.py` là tệp rỗng ở mốc rà soát. Kiểm tra cả import động và điểm gọi trước khi dời script. |
| Bộ kiểm tra ở gốc | `check_coordinate_contracts.py`, `check_editor_drag_zoom_persistence.py`, `check_editor_reopen_persistence.py`, `check_exam_v3.py`, `check_extras_contract.py`, `check_integration_contracts.py`, `check_integration_failures_03c40.py`, `check_layout_json_consistency.py`, `check_layout_matrix.py`, `check_layout_scroll.py`, `check_legacy_runtime_regression.py`, `check_studio_shortcuts.py`, `check_studio_ui.py`, `check_studio_v3.py`, `check_ui_components.py`, `check_ui_contrast.py`, `check_ui_keys.py`, `check_ui_strings.py`, `check_ui_tokens.py`, `VERIFY_PATCH03.py`, `VERIFY_PATCH11.py`, `VERIFY_PATCH12.py`, `VERIFY_PHASE4_PATCH07.py`, `run_reading_tests.py`. |
| Bộ kiểm thử trong `tests/` | `tests/conftest.py` chọn checkout qua `TUHOC_ROOT`. `tests/test_canvas_layout.py` và `tests/test_canvas_studio.py` kiểm tra Canvas. `canvas_p0.py` phát lại thao tác, `tests/canvas_p0_cases.py` cung cấp fixture, `canvas_p0_preview.py` kiểm tra xem trước. `tests/test_exam_bank.py`, `tests/test_exam_grading.py`, `tests/test_exam_state.py` là pytest cho Exam Mode. |
| Công cụ phát triển | `tools/audit_ui_tokens.py` kiểm kê token, `tools/analyze_nav_log.py` tổng hợp log, `tools/measure_ui_pages.py` đo dựng màn hình trên checkout và hồ sơ thử riêng. `tools/reference/exam_logic_reference.py` và `tools/reference/exam_state_reference.py` là kịch bản rà soát lưu để tham chiếu. Dùng pytest trong `tests/` để xác minh Exam Mode. |
| Hướng dẫn và lịch sử | `HUONG_DAN.txt`, `docs/canvas-p0.md`, `docs/canvas-p6.md`, `docs/canvas-matrix.md`, `docs/canvas-auto-log.md`, `docs/canvas-auto-report.md`, `docs/ui-auto-log.md`, `docs/ui-auto-report.md`, `agents/skills/tuhoc-canvas/SKILL.md`, `agents/skills/tuhoc-canvas/references/build-plan.md`. |
| Tệp dữ liệu theo dõi bởi Git | `content_library` là tệp đánh dấu trong checkout. `content_library.zip` chứa dữ liệu đề thi, nhóm bài đọc, bản sao và tệp kết quả. `__pycache__.zip` là bytecode lưu trữ. Cài mới từ mã nguồn và chọn dữ liệu cần nhập vào thư mục riêng. |

## Quy ước khi sửa code

1. Giữ phạm vi đúng theo yêu cầu. Dùng helper và lớp đã có. Ưu tiên logic thuần có thể kiểm thử ngoài Tk/SDL. Giữ nguyên API, kiểu trả về và callback mà các màn hiện tại đang gọi, trừ hành vi được yêu cầu đổi.
2. Với thay đổi UI, dùng `ui_tokens.py`, thành phần chung và `strings_vi.py` khi phù hợp. Giữ phím gõ cho Entry/Text/Combobox, giữ điều hướng bàn phím và tùy chọn giảm chuyển động. Dùng `after` cho cập nhật Tk từ kết quả nền, hủy tác vụ đã lên lịch khi trang hoặc widget bị đóng.
3. Với câu hỏi, giữ ID, nội dung, đáp án, thứ tự và kiểu giá trị trả về. Chỉ sửa chấm, tiến trình hoặc điểm thưởng khi yêu cầu nêu rõ. Nếu thay đổi chấm thi, chạy các test Exam Mode và giữ ca bảo vệ cho câu hỏi cũ.
4. Với Canvas, giữ hỗ trợ layout cũ chuẩn hóa, v2 pixel, v3 có `extras` và câu không có layout. Đọc geometry qua `question_layout_runtime.element` và registry hiện tại. Tính hitbox từ cùng hình chữ nhật dùng để vẽ. Áp phép cuộn đúng một lần. Khung mobile là 390 × 760, phạm vi thiết kế tối đa 4 trang. Nút **Hoàn thành** và bộ đếm câu là phần tử khóa. Hộp văn bản là nội dung trang trí.
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
- `unified_subjects.py` khởi tạo `mon_hoc/tieng_anh/` hoặc `mon_hoc/tieng_viet/` bên cạnh mã nguồn. Mỗi môn có `content_library/level_*.json` và thư mục ảnh. Thiết lập hiển thị ở `mon_hoc/hien_thi.json`. Khi thử khởi động hay thử một luồng ghi, dùng bản sao mã nguồn và thư mục `LOCALAPPDATA` tạm. Thiết lập `LOCALAPPDATA` tách hồ sơ, còn bản sao mã nguồn tách học liệu từng môn.
- Khi nâng bản cài đang dùng, sao lưu thư mục hồ sơ và `mon_hoc/`, đóng app, cập nhật mã nguồn rồi mở app và kiểm tra hồ sơ, bài học, thi và lịch sử. Chỉ nhập các tệp học liệu thực sự cần. Giữ kết quả thi và hồ sơ tách biệt với fixture. Trên bản sao JSON có layout, `python -B layout_migrate.py ban_sao.json --version 3` nâng lên v3 và tạo `.bak`. `python -B layout_migrate.py ban_sao.json --restore` khôi phục nội dung từ `.bak`. Mặc định di trú là v2.
- Quy trình phát hành được kiểm chứng ở checkout này là chạy từ mã nguồn. Checkout có nhánh xử lý runtime đóng gói, nhưng hiện thiếu recipe PyInstaller, tệp `.spec` và cấu hình CI phát hành. Với yêu cầu phát hành `.exe`, xác minh recipe, tài nguyên và phụ thuộc trong một tác vụ đóng gói riêng rồi nghiệm thu trên Windows.
- Với cloud, giữ script cài đặt và hướng dẫn khởi động trong cấu hình môi trường khi có cấu hình đó. Quy trình **Publish** trong Environment Settings dùng cho các máy cloud sau. Một cửa sổ Tk/SDL cần được khởi động lại trong mỗi phiên.

## Chọn lệnh kiểm thử

Chạy từ gốc dự án, bằng Python trong môi trường ảo. Khi chạy smoke hoặc script ghi JSON/log cạnh mã nguồn, chạy trên bản sao checkout và hồ sơ tạm. Trên Linux có thể đặt `SDL_AUDIODRIVER=dummy` và `TU_HOC_PROFILE=0` để thử không có thiết bị âm thanh và không tạo log điều hướng.

```bash
# Exam Mode không cần cửa sổ. Chỉ cài pytest trong môi trường phát triển.
python -m pip install pytest
python -B -m pytest -p no:cacheprovider -q tests/test_exam_*.py

# Canvas Tk và xem trước Pygame trên Linux/X11.
xvfb-run -a python -B -m unittest discover -s tests -p 'test_canvas_*.py' -v
SDL_AUDIODRIVER=dummy xvfb-run -a python -B tests/canvas_p0_preview.py
SDL_AUDIODRIVER=dummy xvfb-run -a python -B tests/canvas_p0_preview.py --feedback

# Phát lại 26 dạng bài. --output nhận thư mục kết quả mới.
tuhoc_run_dir=$(mktemp -d)
SDL_VIDEODRIVER=x11 xvfb-run -a python -B tests/canvas_p0.py --layout v3 --output "$tuhoc_run_dir/v3"
```

`TUHOC_ROOT` mặc định là thư mục đang chạy pytest. Khi chạy kiểm thử Exam Mode từ nơi khác, đặt biến này về checkout cần kiểm tra. Dùng `--layout legacy`, `--layout migrated` hoặc `--layout authored` khi kiểm tra tương thích Canvas. Chạy các script `check_*.py` và `VERIFY_*.py` liên quan nếu thay đổi hợp đồng mà chúng bảo vệ.

Tại mốc rà soát `9484b24`, Exam Mode có 54 ca pytest đạt và 10 `xfail` cho lỗi đã biết. `check_integration_failures_03c40.py` cần `full_runtime_03c39.json`. `run_reading_tests.py` cần `test_reading_pipeline.py`. Hai đầu vào này vắng trong checkout. Cần kiểm tay trên Windows cho DPI 100/125/150%, IME Telex/VNI, âm thanh vật lý, clipboard, tương tác khi cuộn/zoom, và các luồng phát hành `.exe`.
