# Bộ câu hỏi Kiểm tra lớp 2

Bộ câu hỏi gồm 100 câu Toán và 100 câu Tiếng Việt. Câu dẫn dùng tiếng Việt miền Nam trong ngữ cảnh quen thuộc như đi chợ, rửa chén, tưới bông và chia trái cây. Đáp án chính tả dùng tiếng Việt viết chuẩn.

## Nạp, sửa và tạo đề

1. Trong ứng dụng, mở **Ngân hàng kiểm tra → Danh sách câu hỏi → Nạp bộ lớp 2**. Ngân hàng mở bài **Ôn tập lớp 2** để giáo viên xem, lọc M1–M5 và sửa. Với câu đọc hiểu, dùng **Sửa đoạn đọc** trong biểu mẫu câu trắc nghiệm.
2. Khi mở **Kiểm tra**, chọn **Toán** hoặc **Tiếng Việt** → **Lớp 2** → **Ôn tập lớp 2**, rồi chọn Level. Để tự chọn số câu hoặc thời gian thi, dùng **Cấu hình đề**.
3. Có thể nạp lại bộ câu hỏi. Mã đã có được giữ nguyên, kể cả câu giáo viên đã sửa. Khi thêm câu vào ngân hàng hiện có, bản trước khi thêm được lưu dưới `content_library/backups/` trong hồ sơ.

Có thể nạp từ dòng lệnh khi ứng dụng đã đóng. Chạy từ gốc TuHoc và thay đường dẫn bằng thư mục hồ sơ muốn dùng.

```bash
python -B -m exam_content.grade2 --root "/duong/dan/den/TuHocBeta"
```

## Ma trận độ khó

Mỗi môn có cùng số câu theo mức để đáp ứng tỷ lệ mặc định của 10 Level, kể cả khi tạo đề 50 câu.

| Mức | Câu mỗi môn | Toán | Tiếng Việt |
| --- | ---: | --- | --- |
| M1 | 35 | Hàng trăm, chục, đơn vị, số liền sau, so sánh, cộng trừ đơn giản, đơn vị và hình cơ bản. | Từ chỉ sự vật, hoạt động và đặc điểm, vần, dấu thanh, viết hoa, dấu câu và lời chào. |
| M2 | 15 | Cộng trừ có nhớ, nhân 2 và 5, giờ, khối lượng và dung tích. | Từ gần nghĩa và trái nghĩa, xác định hoạt động, nối từ, điền tiếng và sắp xếp câu. |
| M3 | 15 | Cộng trừ trong phạm vi 1.000, chia đều, đổi đơn vị đo độ dài và nối kết quả. | Đọc tìm chi tiết và thứ tự, dùng lời nói phù hợp, điền từ và sắp xếp cụm từ. |
| M4 | 18 | Toán có lời văn từ hai bước, đổi đơn vị, thời gian và sắp xếp số đo. | Đọc để tìm nguyên nhân hoặc bằng chứng, sử dụng từ nối, dấu phẩy và tổ chức câu. |
| M5 | 17 | Giải toán nhiều bước, đường gấp khúc, lập số, đọc số liệu và suy luận ngược. | Đọc suy luận, đối chiếu và tóm tắt, soạn lời nhắn theo tình huống, nối và hoàn chỉnh câu. |

Các dạng trong bộ gồm trắc nghiệm, đúng/sai, điền đáp án, nối cặp, sắp xếp và điền nhiều ô. Đọc hiểu dùng trắc nghiệm có đoạn đọc kèm theo. Nguồn câu hỏi nằm trong `exam_content/`.
