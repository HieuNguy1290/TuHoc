# Kết quả Canvas v3

| Bước | Kết quả |
| --- | --- |
| 1 | Bổ sung lưu trữ v3, di trú có thể phục hồi và lớp chữ tĩnh trong bài học, xem trước và bài kiểm tra. |
| 2 | Studio tạo và sửa hộp văn bản, khung ảnh thật có ba chế độ đặt ảnh và tám tay nắm. Cập nhật mục đang kéo theo khung hình. |
| 3 | Registry bài học khớp 26 dạng. Exam Mode đọc vị trí câu dẫn, ảnh, vùng đáp án và các ô chọn ở trình chạy câu đơn. Bài đọc nhóm dùng hộp văn bản theo cột riêng. |
| 4 | Có phím tắt, đường gióng, di chuyển nhóm, căn chỉnh, menu ngữ cảnh, mẫu và lệnh áp dụng theo Lesson. Dán ảnh phụ thuộc clipboard của nền tảng. Kéo thả tệp từ desktop chưa có. |

[Nhật ký quyết định](canvas-auto-log.md) · [Ma trận từng dạng](canvas-matrix.md)

Trước cập nhật, kiểm kê cũ ghi nhận 17 dạng trong 10 mô-đun phần mở rộng và 9 dạng trong trình chạy chung. Registry hiện khai báo cả 26 dạng. Hồi quy v3 phát lại 104 thao tác trả lời đúng/sai và cuộn với dữ liệu thử. Đối chiếu 52 khung PNG của câu không có layout cho kết quả giống từng byte. Các trường bố cục được mở và các khoảng trống về hình học được liệt kê trong ma trận.

Trong Tk/Xvfb, đo 15 sự kiện kéo và thả liên tiếp sau khi đã chọn cùng một ô nhập. Phiên gốc tạo 315 mục, xóa toàn canvas 15 lần và mất 89.179 ms để xử lý chuỗi sự kiện. Phiên mới tạo 0 mục, xóa toàn canvas 0 lần, dịch nhóm mục một lần và mất 1.167 ms. Đây là thời gian xử lý thử nghiệm cho thao tác đã gộp trong một khung, đo một lần trên cùng máy.

## Commit và phạm vi

- 95f93be Support version 3 layouts and decorative text rendering
- cd9124b Add editable textboxes, image frames and incremental Studio dragging
- feec7e2 Register the 26 lesson layouts and verify v3 exercise interactions
- 1dddc6f Add Studio shortcuts, alignment and backed-up lesson templates

```text
 audit_layout_coverage.py       |  57 ++-
 check_extras_contract.py       |  72 ++++
 check_layout_matrix.py         |  39 ++
 check_studio_shortcuts.py      |  53 +++
 check_studio_v3.py             |  86 +++++
 docs/canvas-matrix.md          |  32 ++
 dropdown_extension.py          |   4 +-
 exam_pygame.py                 |  20 +-
 exercise_layout.py             |   5 +-
 extras_render.py               |  48 +++
 image_sentence_extension.py    |  17 +-
 image_write_extension.py       |  22 +-
 inline_dropdown_extension.py   |  15 +-
 layout_edit_geometry.py        |  54 +++
 layout_images.py               |  41 ++
 layout_migrate.py              |  16 +-
 layout_registry.py             |  53 +++
 layout_render.py               |   2 +-
 layout_scroll_extent.py        |  14 +-
 layout_templates.py            |  56 ++-
 level_flow.py                  |  61 ++-
 listening_image_choice.py      |  15 +-
 multi_fill_blanks_extension.py |  25 +-
 multi_select_extension.py      |   2 +-
 new_exercise_runtime.py        |  95 ++---
 pygame_exercises.py            |  51 ++-
 question_layout_editor.py      | 859 +++++++++++++++++++++++++++++++++--------
 question_layout_store.py       |  88 ++++-
 tests/canvas_p0.py             |  15 +-
 underline_extension.py         |   2 +-
 30 files changed, 1606 insertions(+), 313 deletions(-)
```

## Kết quả lệnh kiểm tra

Các tệp đầu vào kiểm tra nằm trong bản sao. Một kiểm tra cũ thiếu `full_runtime_03c39.json` ngay từ mốc gốc.

### VERIFY_PATCH03.py

```text
PASS: 8 checks (filter, totals, date range, student isolation, empty data, read-only)
```

### VERIFY_PATCH11.py

```text
Checked 127 Python files
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
Ran 7 tests in 0.449s

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
Ran 7 tests in 0.070s

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
Report: /tmp/tuhoc-source.msDAkf/editor_drag_zoom_03c36.json
```

### check_editor_reopen_persistence.py

```text
PASS  Editor save/reopen source contract: Editor entrypoint, save, zoom and scroll-aware drag handlers present
PASS  JSON save, reopen, cancel and reset: Two save/reopen cycles, cancellation, reset and answer data preservation verified
PASS  Zoom and scroll coordinate invariance: Drag coordinates invariant across 5 zoom levels and 3 scroll positions
PASS  Fixed controls remain locked: Locked controls rejected by storage validator
Summary: 4/4 passed; report: editor_reopen_03c38.json
```

### check_extras_contract.py

```text
test_invalid_values (__main__.ExtrasContract.test_invalid_values) ... ok
test_migration_is_idempotent_and_reversible (__main__.ExtrasContract.test_migration_is_idempotent_and_reversible) ... ok
test_pixels_clipping_z_order_and_legacy (__main__.ExtrasContract.test_pixels_clipping_z_order_and_legacy) ... ok
test_round_trip_and_projection (__main__.ExtrasContract.test_round_trip_and_projection) ... ok

----------------------------------------------------------------------
Ran 4 tests in 0.035s

OK
```

### check_integration_contracts.py

```text
Build 03C.33 integration contract checks: {'pass': 16, 'fail': 0, 'missing': 0, 'blocked': 0, 'review': 0}
Report: /tmp/tuhoc-source.msDAkf/integration_contracts_03c33.json
```

### check_integration_failures_03c40.py

```text
ERROR: full_runtime_03c39.json not found next to this script.
```

### check_layout_json_consistency.py

```text
Build 03C.35: {'pass': 11, 'fail': 0}
Report: /tmp/tuhoc-source.msDAkf/layout_json_consistency_03c35.json
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
Report: /tmp/tuhoc-source.msDAkf/legacy_regression_03c31.json
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

### check_studio_v3.py

```text
test_create_style_undo_and_reopen (__main__.StudioV3.test_create_style_undo_and_reopen) ... ok
test_fitted_image_and_resize (__main__.StudioV3.test_fitted_image_and_resize) ... ok

----------------------------------------------------------------------
Ran 2 tests in 0.264s

OK
```

### tests/canvas_p0.py --layout v3

```text
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


## Kiểm tra bổ sung trước khi phát hành

- Commit `fd6c84f` nối hình học v3 với vùng cuộn của Exam Mode và giữ khung điều khiển bên ngoài. Phép so sánh 28 khung và danh sách hitbox của câu thi không có layout trùng với mốc gốc ở hai vị trí cuộn.
- Bản ghi kiểm thử cho thấy khung ảnh mới được vẽ và nhấp đúng vào đáp án đã dời sau khi cuộn. Mẫu bài đọc nhóm xác định hệ tọa độ theo desktop.
- Kiểm tra dán ảnh trong Tk dùng ảnh clipboard mô phỏng, hoàn tác và làm lại, sau đó đối chiếu đúng PNG đã xuất.
- Bốn lượt chạy với dữ liệu giả, mỗi lượt gồm 104 thao tác cho các kiểu legacy, migrated, authored và v3. Có hai lượt xem trước với hiệu ứng phản hồi bật và tắt.

```text
test_authored_options_use_the_rendered_scrolled_rect (__main__.ExamV3.test_authored_options_use_the_rendered_scrolled_rect) ... ok

----------------------------------------------------------------------
Ran 1 test in 0.030s

OK
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

## Cần kiểm tay trên Windows

- DPI 100%, 125% và 150%, kéo hoặc đổi cỡ sau khi phóng và cuộn.
- Nhập tiếng Việt bằng bộ gõ đang sử dụng và thử dán ảnh vào Studio.
- Kiểm tra nút phóng ảnh và phát âm thanh bằng thiết bị thật.
- Di trú và phục hồi trên bản sao học liệu thật. Checkout có gói đề thi và thiếu bộ đầy đủ bài học sản xuất.
