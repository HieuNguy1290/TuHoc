---
name: tuhoc-canvas
description: Build, debug, and verify TuHoc Studio's Tkinter/Pygame question canvas, layout v2 migration, TokenPicker, preview, and exercise adapters. Use for TuHoc question layout, hitboxes, scrolling, or phases P0–P6.
---

# TuHoc Canvas

Ð?c [k? ho?ch P0–P6](references/build-plan.md). Xác minh mã ngu?n và tr?ng thái ki?m th? th?c t?. B?t d?u ? phase ngu?i dùng yêu c?u ho?c phase s?m nh?t chua du?c xác minh trong ph?m vi công vi?c.

Tru?c m?i phase, nêu file d? ki?n s?a và ch?y b? h?i quy P0. Sau m?i phase, ch?y l?i b? h?i quy và báo cáo file dã d?i, l?nh test, k?t qu? và ph?n chua xác minh. N?u m?t ki?m tra b?t bu?c th?t b?i, x? lý trong phase hi?n t?i r?i ch?y l?i. Khi ngu?i dùng yêu c?u m?t phase duy nh?t, d?ng sau báo cáo phase dó.

## Khóa b?t bu?c

- Gi? nguyên `exam_grading.is_correct`, m?i `is_correct` và `normalize` trong `new_exercise_runtime.py` và các `*_extension.py`, `Database.record()` và schema `attempts`. Xác minh du?ng ghi th?c t? ? P0.
- Gi? nguyên cách ch?m, xáo tr?n, luu k?t qu? và validate hi?n có, ngo?i tr? di?u ki?n d? r?ng du?c nêu bên du?i.
- Khi ch?nh canvas ho?c migrate, gi? nguyên `id`, `type`, `answer`, `options`, `distractors`, `pairs`, `sequence` và `gap_answers`.
- L?p chu?n dúng, sai và biên cho c? 26 d?ng t? runtime g?c. Phát l?i thao tác tru?c và sau cu?n. So sánh giá tr?, ki?u và th? t? c?a `answer`, k?t qu? ch?m và b?n ghi th?c t?.
- Xem th? dùng b?n nháp, b? qua ch?m di?m và t?o 0 lu?t n?p, 0 b?n ghi k?t qu?.
- Migrate ch? thay giá tr? `layout` dã có. Gi? t?ng byte bên ngoài các giá tr? dó. Dùng copy-on-write, t?o `.bak`, xác minh `.tmp`, r?i thay file b?ng `os.replace`. N?u ki?m tra sau thay file th?t b?i, ph?c h?i t? `.bak` và xác minh l?i.
- TokenPicker c?p nh?t `hidden_indices` qua `collect()` hi?n có khi giáo viên ch? d?ng ch?n ch? ho?c t? ?n và luu. Thao tác b? c?c gi? nguyên giá tr? này.
- Ch? cho phép `prompt` r?ng v?i `picture_missing_letters`. Rà m?i noi d?c `prompt`, g?m l?ch s?, ôn câu sai và k?t qu?. Dùng nhãn d? phòng ? ph?n hi?n th? khi c?n.
- Gi? cách hi?n th? cu cho câu chua có layout và gi? các API công khai dang du?c g?i. Nút Hoàn thành và b? d?m câu luôn c? d?nh.
- Dùng Tkinter và Pygame trên Windows, v?i giao di?n ti?ng Vi?t. Báo cáo k?t qu? GUI trên Windows riêng v?i k?t qu? headless. Ghi rõ fixture nào dùng d? li?u m?u và ph?n nào còn thi?u h?c li?u th?c t?.