# Kết quả UI/UX TuHoc

| Giai đoạn | Kết quả |
| --- | --- |
| UI-1 | Có token và cỡ chữ Nhỏ, Vừa, Lớn. Các màu chuyên biệt tiếp tục dùng giá trị gốc. |
| UI-2 | Nút có trạng thái chờ hoặc vô hiệu, hộp thoại dùng chung, thông báo nhanh, trình tải, tooltip và trạng thái rỗng. Đã chuyển các luồng người học đã chọn. |
| UI-3 | Hỗ trợ quay lại, trợ giúp, chọn trong lưới Level, vòng focus và Giảm chuyển động. 14 cặp màu kiểm thử đạt WCAG AA cho chữ thường. |
| UI-4 | Gom bước đo bố cục của bản đồ, giữ tối đa hai ảnh nền đã đổi kích thước và ghi log điều hướng ngoài luồng Tk. Điểm và tiến trình dùng cơ chế ghi hiện có. |
| UI-5 | Gom các nhãn dùng chung. Lỗi callback có mã tham chiếu. Hiện trạng thái lưu bản nháp, tải bài và biểu tượng đúng/sai trong luồng dự phòng Tk. Âm báo là tùy chọn. |
| UI-6 | Danh sách câu hỏi và block có tìm kiếm, sắp xếp, nhân bản và hoàn tác xóa. Lịch sử lọc theo thời gian. Trang kết quả và phân tích có đường dẫn vào ôn câu sai. Các biểu mẫu có nhắc kiểm tra trước khi lưu. |

[Nhật ký quyết định](ui-auto-log.md) · [Kiểm tra Canvas v3](canvas-auto-report.md)

## Commit và phạm vi

- 9b15f32 Centralize Tk colors and add a configurable interface text scale
- 23fada6 Add accessible shared dialogs, controls and learner feedback
- 66780bf Add keyboard navigation, focus indicators and reduced motion
- 67c6fd1 Reduce Tk layout work and queue navigation profiling off the UI thread
- e5c012a Unify learner strings, error references and quiz status feedback
- eb50cda Improve authoring lists, undo and learner history filters
- fd6c84f Apply v3 geometry within the Exam Mode question pane
- 6923dc8 Use the shared text scale throughout the learner pages

```text
 admin_editor.py           |   9 +-
 check_exam_v3.py          |  46 ++++++++
 check_extras_contract.py  |   3 +
 check_studio_ui.py        |  68 ++++++++++++
 check_studio_v3.py        |  32 ++++++
 check_ui_components.py    |  68 ++++++++++++
 check_ui_contrast.py      |  20 ++++
 check_ui_keys.py          |  22 ++++
 check_ui_strings.py       |  48 ++++++++
 check_ui_tokens.py        |  33 ++++++
 exam_bank_pygame.py       | 128 ++++++++++++++++++++--
 exam_pygame.py            | 179 ++++++++++++++++++++++--------
 extras_render.py          |   4 +-
 home_ui.py                |  23 ++--
 learning_analytics_ui.py  |   4 +-
 lesson_display_names.py   |  20 +++-
 lesson_map_ui.py          |  54 ++++++---
 level_flow.py             | 273 +++++++++++++++++++++++++++++-----------------
 main.py                   | 229 ++++++++++++++++++++------------------
 multi_block_editor.py     |  54 +++++++--
 navigation_profiler.py    |  37 ++++++-
 profile_ui.py             |  38 ++++---
 question_layout_store.py  |   6 +-
 quiz_history_ui.py        |  95 ++++++++++------
 strings_vi.py             |  31 ++++++
 studio_list.py            |  51 +++++++++
 subject_loading_screen.py |  71 +++++++-----
 theme_config.py           |  15 +--
 tools/analyze_nav_log.py  |  32 ++++++
 tools/audit_ui_tokens.py  |  38 +++++++
 tools/measure_ui_pages.py |  42 +++++++
 ui_components.py          | 241 ++++++++++++++++++++++++++++++++++++----
 ui_dialogs.py             |  52 +++++++++
 ui_errors.py              |  20 ++++
 ui_keys.py                |  60 ++++++++++
 ui_motion.py              |  13 ++-
 ui_results_dashboard.py   |  14 ++-
 ui_shell.py               |  32 ++++--
 ui_tokens.py              |  57 ++++++++++
 upgrade_v2.py             | 134 +++++++++++++++--------
 wrong_answers_ui.py       |   4 +-
 41 files changed, 1915 insertions(+), 485 deletions(-)
```


## Số liệu đo

Kiểm kê AST dùng cùng nhóm chín mô-đun giao diện trước và sau. Cột chuỗi đếm giá trị trực tiếp trong đối số `text`, `title`, `label` và `message`. Cột messagebox đếm biểu thức cú pháp `messagebox.*`.

| Hạng mục | Trước | Sau |
| --- | ---: | ---: |
| Màu hex viết trực tiếp | 346 | 300 |
| Tên font Segoe UI | 146 | 18 |
| Chuỗi nhãn trực tiếp | 149 | 148 |
| Lời gọi messagebox | 96 | 54 |

Đo 7 lần dựng trang Tk/Xvfb với hồ sơ giả và seed 2600. Phép đo kết thúc khi Tk xử lý xong các tác vụ idle. Phần dựng nội dung trì hoãn của trang chủ nằm ngoài cửa sổ đo.

| Trang | Trung vị trước (ms) | Trung vị phát hành (ms) |
| --- | ---: | ---: |
| home | 11.209 | 11.693 |
| journey_page | 59.764 | 53.017 |
| quiz_history_page | 20.538 | 20.119 |

Checkout không có log điều hướng sản xuất. Bảng sau lấy từ log của hai lần đo trên cùng máy.

| Giai đoạn | Trung vị trước (ms) | Lớn nhất trước (ms) | Trung vị sau (ms) | Lớn nhất sau (ms) |
| --- | ---: | ---: | ---: | ---: |
| layout | 11.09 | 130.12 | 11.51 | 130.49 |
| clear | 1.69 | 11.62 | 1.90 | 11.60 |
| destroy_widgets | 1.56 | 11.44 | 1.81 | 11.52 |
| _remove_page_fade | 0.00 | 0.00 | 0.00 | 0.00 |
| stop_audio | 0.00 | 0.01 | 0.00 | 0.01 |


## Kết quả tự động

Toàn bộ `check_*.py` và `VERIFY_*.py` có dữ liệu đầu vào đã chạy thành công. `check_integration_failures_03c40.py` báo thiếu `full_runtime_03c39.json` từ mốc gốc. Thiết lập dùng Python 3.12.14, Tkinter, SDL/Pygame và Xvfb. Lệnh cài lặp lại trả về `No broken requirements found.`

```text
Compiled 148 Python files
Opened home
Opened journey_page
Opened quiz_history_page
Opened wrong_answers_page
Opened learning_analytics_page
Opened report_page
Opened question_editor
Opened display_settings
Opened choose_language
Opened lesson block editor
Rendered the Exam Bank question list with fixture data
test_blank_prompt_is_only_valid_for_missing_letters (test_canvas_layout.LayoutTests.test_blank_prompt_is_only_valid_for_missing_letters) ... ok
test_coordinates_at_boundary (test_canvas_layout.LayoutTests.test_coordinates_at_boundary) ... ok
test_letter_wrap_uses_cell_width_and_row_height (test_canvas_layout.LayoutTests.test_letter_wrap_uses_cell_width_and_row_height) ... ok
test_mobile_override_and_template (test_canvas_layout.LayoutTests.test_mobile_override_and_template) ... ok
test_post_replace_failure_restores_backup (test_canvas_layout.LayoutTests.test_post_replace_failure_restores_backup) ... ok
test_real_archive_copy (test_canvas_layout.LayoutTests.test_real_archive_copy) ... ok
test_round_trip_preserves_unrelated_bytes (test_canvas_layout.LayoutTests.test_round_trip_preserves_unrelated_bytes) ... ok
test_word_bank_pages_with_three_speakers (test_canvas_layout.LayoutTests.test_word_bank_pages_with_three_speakers) ... ok
test_drag_at_zoom_with_scrolled_origin (test_canvas_studio.StudioTests.test_drag_at_zoom_with_scrolled_origin) ... ok
test_four_token_collectors (test_canvas_studio.StudioTests.test_four_token_collectors) ... ok
test_pixel_edits_mobile_undo_and_preview (test_canvas_studio.StudioTests.test_pixel_edits_mobile_undo_and_preview) ... ok

----------------------------------------------------------------------
Ran 11 tests in 4.452s

OK
Preview feedback=False, answer=cat, grading calls=0, submissions=0, result rows=0, fixture bytes unchanged
Preview feedback=True, answer=cat, grading calls=0, submissions=0, result rows=0, fixture bytes unchanged
choice: default/right=ok, default/wrong=ok, scroll/right=ok, scroll/wrong=ok
picture_choice: default/right=ok, default/wrong=ok, scroll/right=ok, scroll/wrong=ok
true_false: default/right=ok, default/wrong=ok, scroll/right=ok, scroll/wrong=ok
listening_choice: default/right=ok, default/wrong=ok, scroll/right=ok, scroll/wrong=ok
fill: default/right=ok, default/wrong=ok, scroll/right=ok, scroll/wrong=ok
listening_fill: default/right=ok, default/wrong=ok, scroll/right=ok, scroll/wrong=ok
error: default/right=ok, default/wrong=ok, scroll/right=ok, scroll/wrong=ok
order: default/right=ok, default/wrong=ok, scroll/right=ok, scroll/wrong=ok
matching: default/right=ok, default/wrong=ok, scroll/right=ok, scroll/wrong=ok
listening_image_choice: default/right=ok, default/wrong=ok, scroll/right=ok, scroll/wrong=ok
image_multi_choice: default/right=ok, default/wrong=ok, scroll/right=ok, scroll/wrong=ok
picture_missing_letters: default/right=ok, default/wrong=ok, scroll/right=ok, scroll/wrong=ok
sentence_gaps: default/right=ok, default/wrong=ok, scroll/right=ok, scroll/wrong=ok
passage_gaps: default/right=ok, default/wrong=ok, scroll/right=ok, scroll/wrong=ok
conversation_gaps: default/right=ok, default/wrong=ok, scroll/right=ok, scroll/wrong=ok
image_multi_select: default/right=ok, default/wrong=ok, scroll/right=ok, scroll/wrong=ok
text_multi_select: default/right=ok, default/wrong=ok, scroll/right=ok, scroll/wrong=ok
audio_multi_select: default/right=ok, default/wrong=ok, scroll/right=ok, scroll/wrong=ok
image_write_answer: default/right=ok, default/wrong=ok, scroll/right=ok, scroll/wrong=ok
image_underline_choice: default/right=ok, default/wrong=ok, scroll/right=ok, scroll/wrong=ok
sentence_underline_words: default/right=ok, default/wrong=ok, scroll/right=ok, scroll/wrong=ok
dropdown_fill_blank: default/right=ok, default/wrong=ok, scroll/right=ok, scroll/wrong=ok
multi_fill_blanks: default/right=ok, default/wrong=ok, scroll/right=ok, scroll/wrong=ok
image_sentence_fill: default/right=ok, default/wrong=ok, scroll/right=ok, scroll/wrong=ok
image_letter_pick: default/right=ok, default/wrong=ok, scroll/right=ok, scroll/wrong=ok
inline_dropdown_fill: default/right=ok, default/wrong=ok, scroll/right=ok, scroll/wrong=ok
```

### VERIFY_PATCH03.py

```text
PASS: 8 checks (filter, totals, date range, student isolation, empty data, read-only)
```

### VERIFY_PATCH11.py

```text
Checked 140 Python files
PASS: syntax, required modules and question-counter contract
NOTE: This is NOT a Windows GUI/SDL runtime test.
```

### VERIFY_PATCH12.py

```text
test_all_sources_parse (__main__.Phase3Regression.test_all_sources_parse) ... ok
test_extended_grading (__main__.Phase3Regression.test_extended_grading) ... ok
test_extended_types_coverage (__main__.Phase3Regression.test_extended_types_coverage) ... ok
test_gap_index_safety (__main__.Phase3Regression.test_gap_index_safety) ... ok
test_lifecycle_guard_present (__main__.Phase3Regression.test_lifecycle_guard_present) ... ok
test_question_counter_contract (__main__.Phase3Regression.test_question_counter_contract) ... ok
test_sequential_progress_guard (__main__.Phase3Regression.test_sequential_progress_guard) ... ok

----------------------------------------------------------------------
Ran 7 tests in 0.380s

OK

NOTE: Headless checks only; verify the native SDL window on Windows manually.
```

### VERIFY_PHASE4_PATCH07.py

```text
test_01_draft_resumes_and_isolated_by_student (__main__.Phase4Regression.test_01_draft_resumes_and_isolated_by_student) ... ok
test_02_invalid_draft_rejected (__main__.Phase4Regression.test_02_invalid_draft_rejected) ... ok
test_03_history_pagination_and_student_filter (__main__.Phase4Regression.test_03_history_pagination_and_student_filter) ... ok
test_04_analytics_aggregates_only_active_student (__main__.Phase4Regression.test_04_analytics_aggregates_only_active_student) ... ok
test_05_wrong_answers_latest_attempt_only (__main__.Phase4Regression.test_05_wrong_answers_latest_attempt_only) ... ok
test_06_insights_grouping_does_not_mutate_answers (__main__.Phase4Regression.test_06_insights_grouping_does_not_mutate_answers) ... ok
test_07_source_integration_contracts (__main__.Phase4Regression.test_07_source_integration_contracts) ... ok

----------------------------------------------------------------------
Ran 7 tests in 0.087s

OK
Phase 4 regression suite — in-memory database, no GUI, no changes to user data
```

### check_coordinate_contracts.py

```text
Build 03C.34: 31/31 checks passed
Report: coordinate_contracts_03c34.json
```

### check_editor_drag_zoom_persistence.py

```text
Build 03C.36: {'passed': 4, 'failed': 0}
Report: /tmp/tuhoc-source.a8yMTS/editor_drag_zoom_03c36.json
```

### check_editor_reopen_persistence.py

```text
PASS  Editor save/reopen source contract: Editor entrypoint, save, zoom and scroll-aware drag handlers present
PASS  JSON save, reopen, cancel and reset: Two save/reopen cycles, cancellation, reset and answer data preservation verified
PASS  Zoom and scroll coordinate invariance: Drag coordinates invariant across 5 zoom levels and 3 scroll positions
PASS  Fixed controls remain locked: Locked controls rejected by storage validator
Summary: 4/4 passed; report: editor_reopen_03c38.json
```

### check_exam_v3.py

```text
test_authored_options_use_the_rendered_scrolled_rect (__main__.ExamV3.test_authored_options_use_the_rendered_scrolled_rect) ... ok

----------------------------------------------------------------------
Ran 1 test in 0.030s

OK
```

### check_extras_contract.py

```text
test_invalid_values (__main__.ExtrasContract.test_invalid_values) ... ok
test_migration_is_idempotent_and_reversible (__main__.ExtrasContract.test_migration_is_idempotent_and_reversible) ... ok
test_pixels_clipping_z_order_and_legacy (__main__.ExtrasContract.test_pixels_clipping_z_order_and_legacy) ... ok
test_round_trip_and_projection (__main__.ExtrasContract.test_round_trip_and_projection) ... ok

----------------------------------------------------------------------
Ran 4 tests in 0.036s

OK
```

### check_integration_contracts.py

```text
Build 03C.33 integration contract checks: {'pass': 16, 'fail': 0, 'missing': 0, 'blocked': 0, 'review': 0}
Report: /tmp/tuhoc-source.a8yMTS/integration_contracts_03c33.json
```

### check_integration_failures_03c40.py

```text
ERROR: full_runtime_03c39.json not found next to this script.
```

### check_layout_json_consistency.py

```text
Build 03C.35: {'pass': 11, 'fail': 0}
Report: /tmp/tuhoc-source.a8yMTS/layout_json_consistency_03c35.json
```

### check_layout_matrix.py

```text
test_no_layout_v2_v3_mobile_and_deep_scroll (__main__.LayoutMatrix.test_no_layout_v2_v3_mobile_and_deep_scroll) ... ok
test_registry_matches_dispatch_and_templates (__main__.LayoutMatrix.test_registry_matches_dispatch_and_templates) ... ok

----------------------------------------------------------------------
Ran 2 tests in 0.004s

OK
```

### check_layout_scroll.py

```text
PASS: source syntax, layout geometry, extended scroll extent, locked controls
NOTE: This does not test Pygame mouse interaction or Windows UI.
```

### check_legacy_runtime_regression.py

```text
{
  "build": "03C.31",
  "file": "pygame_exercises.py",
  "checks": [
    {
      "name": "Python syntax",
      "ok": true
    },
    {
      "name": "Legacy runtime _run exists",
      "ok": true
    },
    {
      "name": "All 9 legacy kinds declared",
      "ok": true
    },
    {
      "name": "Layout geometry lookup",
      "ok": true
    },
    {
      "name": "Answer area geometry",
      "ok": true
    },
    {
      "name": "Individual option geometry",
      "ok": true
    },
    {
      "name": "Scroll bounds",
      "ok": true
    },
    {
      "name": "Wheel scroll",
      "ok": true
    },
    {
      "name": "PageUp/PageDown",
      "ok": true
    },
    {
      "name": "Viewport hitbox translated",
      "ok": true
    },
    {
      "name": "Choice fixed submit",
      "ok": true
    },
    {
      "name": "Text fixed submit",
      "ok": true
    },
    {
      "name": "Sequence fixed submit",
      "ok": true
    },
    {
      "name": "Matching completion guard",
      "ok": true
    },
    {
      "name": "Order completion guard",
      "ok": true
    },
    {
      "name": "Header/footer click guard",
      "ok": true
    },
    {
      "name": "Matching reset control",
      "ok": true
    }
  ],
  "warnings": [
    "Static checks only; actual mouse/keyboard/audio behavior is unverified."
  ],
  "manual_qa": [
    "For each of the 9 kinds, test with and without saved layout.",
    "Scroll to bottom; ensure fixed submit is visible and clickable.",
    "Click an answer behind header/footer: it must not be selected.",
    "For matching, reset/relink pairs and submit only when complete.",
    "For order, select all tokens in sequence, reset and submit.",
    "For text inputs, type long text and submit without losing content.",
    "Verify scoring and audio playback on Windows."
  ],
  "passed": 17,
  "total": 17
}
Report: /tmp/tuhoc-source.a8yMTS/legacy_regression_03c31.json
```

### check_studio_shortcuts.py

```text
test_alignment_and_distribution (__main__.StudioShortcuts.test_alignment_and_distribution) ... ok
test_movement_preserves_group_and_page_limits (__main__.StudioShortcuts.test_movement_preserves_group_and_page_limits) ... ok
test_template_round_trip_only_updates_matching_questions (__main__.StudioShortcuts.test_template_round_trip_only_updates_matching_questions) ... ok

----------------------------------------------------------------------
Ran 3 tests in 0.006s

OK
```

### check_studio_ui.py

```text
test_bank_edit_retains_layout_and_delete_can_be_undone (__main__.StudioUI.test_bank_edit_retains_layout_and_delete_can_be_undone) ... ok
test_duplicate_and_undo_do_not_mutate_input (__main__.StudioUI.test_duplicate_and_undo_do_not_mutate_input) ... ok
test_filter_sort_keep_original_indices (__main__.StudioUI.test_filter_sort_keep_original_indices) ... ok
test_history_period (__main__.StudioUI.test_history_period) ... ok

----------------------------------------------------------------------
Ran 4 tests in 0.010s

OK
```

### check_studio_v3.py

```text
test_clipboard_image_can_be_undone_before_saving (__main__.StudioV3.test_clipboard_image_can_be_undone_before_saving) ... ok
test_create_style_undo_and_reopen (__main__.StudioV3.test_create_style_undo_and_reopen) ... invalid command name "139863847279424maximize_work_area"
    while executing
"139863847279424maximize_work_area"
    ("after" script)
ok
test_fitted_image_and_resize (__main__.StudioV3.test_fitted_image_and_resize) ... ok

----------------------------------------------------------------------
Ran 3 tests in 0.400s

OK
```

### check_ui_components.py

```text
test_button_states_and_focus (__main__.Components.test_button_states_and_focus) ... ok
test_create_and_dispose_feedback (__main__.Components.test_create_and_dispose_feedback) ... ok
test_dialog_keyboard_and_compatibility (__main__.Components.test_dialog_keyboard_and_compatibility) ... ok

----------------------------------------------------------------------
Ran 3 tests in 0.282s

OK
```

### check_ui_contrast.py

```text
test_pairs (__main__.UIContrast.test_pairs) ... ok

----------------------------------------------------------------------
Ran 1 test in 0.000s

OK
text on surface: 12.36
muted on surface: 5.65
primary on surface: 5.22
error on surface: 7.00
warning on surface: 7.80
info on surface: 7.19
focus on surface: 7.19
text on background: 11.77
muted on background: 5.38
text on tint: 10.78
primary on tint: 4.55
disabled_text on disabled: 5.27
surface on primary: 5.22
surface on primary_dark: 8.13
```

### check_ui_keys.py

```text
test_application_keys (__main__.UIKeys.test_application_keys) ... ok
test_text_fields_keep_keyboard_input (__main__.UIKeys.test_text_fields_keep_keyboard_input) ... ok

----------------------------------------------------------------------
Ran 2 tests in 0.000s

OK
```

### check_ui_strings.py

```text
test_keys_and_format_fields (__main__.UIStrings.test_keys_and_format_fields) ... ok
test_reference_is_logged_with_technical_details (__main__.UIStrings.test_reference_is_logged_with_technical_details) ... ok

----------------------------------------------------------------------
Ran 2 tests in 0.142s

OK
```

### check_ui_tokens.py

```text
test_palette_and_metrics (__main__.Tokens.test_palette_and_metrics) ... ok
test_scaling_is_applied_to_new_fonts (__main__.Tokens.test_scaling_is_applied_to_new_fonts) ... ok

----------------------------------------------------------------------
Ran 2 tests in 0.000s

OK
```


## Cần kiểm tay trên Windows

- DPI 100%, 125% và 150%, cửa sổ nhỏ, các lựa chọn cỡ chữ, tương phản trên màn hình thật và chuyển động ở cả hai chế độ.
- Bộ gõ tiếng Việt trong biểu mẫu học sinh và giáo viên, dán ảnh từ clipboard thật, focus khi đổi cửa sổ, âm báo và phát âm thanh.
- Học liệu sản xuất và các thao tác nhập hoặc xuất của giáo viên cần dữ liệu tương ứng. Bài đọc nhóm trong Exam Mode hỗ trợ lớp hộp văn bản và giữ dàn trang điều hướng theo cột. Studio chưa hỗ trợ kéo thả tệp từ desktop.
