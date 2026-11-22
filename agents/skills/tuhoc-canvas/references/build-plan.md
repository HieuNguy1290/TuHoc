# TuHoc Studio — K? ho?ch build canvas

## Ki?n trúc

- Layout v2 luu pixel trên khung máy tính 960×640 và di?n tho?i 390×760. B? c?c di?n tho?i có th? suy ra t? máy tính r?i ch?nh riêng. Máy tính cu?n t?i da 2560 px. Xác minh gi?i h?n d?c c?a b?n di?n tho?i tru?c khi c? d?nh schema.
- Dùng chung hình h?c Pygame khi v? và nh?n thao tác. Editor dua Surface lên Tkinter qua ImageTk r?i thêm lu?i, vi?n ch?n, tay n?m và du?ng gióng. Ki?m tra Pillow và cách dóng gói Windows.
- Xác minh registry d? 26 d?ng t? runtime. Các nhóm g?m `free`, `container`, `token` và `inline`. `option_N` là v? trí hi?n th? sau khi xáo. Preview tái t?o th? t? ho?c ghi chú th? t? ng?u nhiên.

## P0 · Chu?n h?i quy

- [ ] Li?t kê m?i noi d?c layout. L?p ma tr?n 26 d?ng, du?ng ch?m, cách l?y `answer`, thao tác và noi ghi k?t qu?.
- [ ] Ch?y unit test dúng, sai và biên trên mã g?c. Thu `answer` t? runtime và k?t qu? t? SQLite t?m.
- [ ] Sinh ?nh Pygame headless và d? li?u hitbox v?i font, fixture và th? t? phuong án c? d?nh.
- [ ] Click tâm t?ng ô tru?c và sau cu?n. V?i d?ng cu chua cu?n du?c, l?y chu?n khi ph?n t? dang nhìn th?y. V?i d?ng n?i, x?p ho?c nh?p, hoàn t?t thao tác d? thu `answer`.
- [ ] Báo cáo fixture m?u và h?c li?u th?c t? còn thi?u.

## P1 · S?a editor cu

- [ ] Dùng khung 960×640. S?a quy d?i t?a d? khi zoom, cu?n và ki?m tra gi?i h?n `y + h`. Cho kéo xu?ng du?i `Y=640`.
- [ ] B? sung `input_area`, `dropdown_area`, `X/Y/W/H` và nhãn phuong án theo v? trí hi?n th?.
- [ ] Ki?m tra luu, m? l?i và thao tác runtime. Sai s? hình h?c t?i da 1 px ? cùng khung logic.

## P2 · Layout v2

- [ ] Thêm `layout_migrate.py`, `layout_render.py` và `layout_templates.py`. Ð?c layout cu và v2, gi? API công khai và ánh x? `input_area` n?u c?n.
- [ ] Ki?m tra round-trip trên `questions_addon.json`, `demo_exam_questions_grade1_family.json` và b?n sao h?c li?u th?t.
- [ ] Migrate ch? thay vùng byte c?a giá tr? `layout`. T?o `.bak`, xác minh `.tmp` tru?c `os.replace`, d?c l?i sau khi ghi, th? migrate l?p và rollback.
- [ ] So ?nh editor và runtime ? cùng c?nh và font. B? lu?i, vi?n ch?n và tay n?m kh?i phép so. Sai khác t?i da 1% pixel. Ki?m tra hitbox riêng.

## P3 · TokenPicker và d? r?ng

- [ ] Tích h?p `picture_missing_letters`, `sentence_gaps`, `passage_gaps` và `conversation_gaps`. Tách ch? d? b? c?c kh?i ch? d? ch?n ch? ho?c t? ?n. Ki?m tra du?ng `collect()`.
- [ ] Cho `letter_items()` nh?n d? r?ng, kích thu?c ô và chi?u cao hàng t? layout. Gi? thông s? g?c v?i câu cu. Kh?i t? t? giãn khi xu?ng dòng. Ki?m tra `word_bank` và câu có nhi?u lu?t tho?i.
- [ ] Cho `prompt` r?ng riêng v?i `picture_missing_letters`. Rà m?i noi d?c `prompt` và ki?m tra l?ch s?, ôn câu sai, k?t qu?. Gi? d? li?u r?ng và dùng nhãn d? phòng ? giao di?n.

## P4 · Studio ba c?t

- [ ] Tích h?p danh sách l?p, metadata và danh m?c bên trái, canvas ? gi?a và thu?c tính bên ph?i trong trình so?n hi?n t?i.
- [ ] Thêm ch?n m?u, khôi ph?c m?c d?nh, hoàn tác/làm l?i, zoom, snap, t? cu?n, tr?ng thái luu và c?nh báo khi dóng b?n nháp.
- [ ] M? preview Pygame v?i b?n chua luu. Ki?m tra chu?t, phím, ô s?, th? t? Tab, tuong ph?n t?i thi?u 4,5:1 và không phát sinh k?t qu?.

## P5 · Chuy?n runtime theo t?ng d?ng

- [ ] Th? d?u tiên v?i `image_write_answer`. Thêm cu?n cho `image_sentence_extension.py` và `listening_image_choice.py`. Thêm layout cho `image_letter_pick_extension.py`.
- [ ] Chuy?n t?ng d?ng còn l?i. V?i m?i d?ng, ki?m tra câu không layout, layout cu và layout v2. Ð?i chi?u `answer` tru?c và sau cu?n, ch?m di?m, xáo tr?n và ghi k?t qu?.

## P6 · Bàn giao

- [ ] Ch?y l?i toàn b? b? test. Ki?m tra t?ng d?ng b?ng GUI th?t trên Windows, g?m DPI, gõ d?u, audio, resize, cu?n và preview.
- [ ] Di?n t?p ph?c h?i `.bak` trên b?n sao. C?p nh?t `HUONG_DAN.txt`, danh sách file thay d?i, cách cài ho?c chép dè và checklist Windows.

## M?u báo cáo phase

- **Phase và tr?ng thái** · …
- **Ph?m vi, file d? ki?n và file dã d?i** · …
- **L?nh và k?t qu? test tru?c/sau** · …
- **S? d?ng dã xác minh** · … / 26
- **Ð?i chi?u ch?m, hitbox, `answer`, k?t qu? luu và byte ngoài layout** · …
- **B?ng ch?ng và m?c chua xác minh** · …
- **Quy?t d?nh chuy?n phase** · …