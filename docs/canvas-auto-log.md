# Nhật ký quyết định Canvas v3

- Giữ lệnh di trú mặc định ở v2 để bảo toàn các hướng dẫn và lệnh gọi hiện có. Chọn rõ `--version 3` khi nâng tệp lên v3. Dùng bản sao mới nếu tệp đã có bản `.bak` từ một lần di trú khác.
- Giữ hình học và các trường v1/v2 đã lưu. Registry chỉ mở chỉnh sửa các thành phần điều khiển mà renderer bài học đọc. Với dạng ngoài registry, Studio vẫn cho thêm hộp văn bản.
- Giữ số câu và nút hoàn thành ở lớp điều khiển của từng trình chạy. Bố cục bài kiểm tra có khung riêng, nên hộp văn bản được chiếu theo bề rộng của cột câu hỏi.
- Khóa và ẩn phần tử áp dụng trong phiên Studio. Thứ tự z của hộp văn bản được lưu. Phần tử ảnh và nút điều khiển của bài học giữ thứ tự của renderer.
- Chỉ hiện Dán ảnh khi có hỗ trợ đọc clipboard. Tệp PNG được giữ tạm đến khi lưu bố cục. Tk không có API kéo thả tệp tích hợp đồng nhất giữa các nền tảng đã hỗ trợ.
- Tệp mẫu nằm trong hồ sơ ứng dụng. Áp dụng hàng loạt yêu cầu xác nhận số câu thay đổi và lưu bản `.bak`.
