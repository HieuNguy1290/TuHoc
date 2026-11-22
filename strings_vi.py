"""Vietnamese labels shared by Tk pages and learner-facing notices."""

STRINGS = {
    'home': 'Trang chủ',
    'lessons': 'Bài học',
    'exercises': 'Bài tập',
    'vocab': 'Từ vựng',
    'reading': 'Tập đọc',
    'history': 'Lịch sử làm bài',
    'notifications': 'Thông báo',
    'shortcuts': 'Phím tắt',
    'account': 'Tài khoản ▾',
    'back_tooltip': 'Quay lại · Alt + ←',
    'unexpected_error_title': 'Ứng dụng gặp lỗi',
    'unexpected_error': 'Không thể thực hiện thao tác. Hãy thử lại. Nếu lỗi còn xảy ra, báo mã {code} để được hỗ trợ.',
    'wrong_answers_empty': 'Không có câu trả lời sai phù hợp.',
    'history_empty': 'Chưa có bài tập hoàn thành',
    'quiz_busy_title': 'Đang mở bài tập…',
    'quiz_busy': 'Cửa sổ bài tập đang bận. Đang thử kết nối lại…',
    'quiz_fallback': 'Không thể tải giao diện Pygame cho câu này. Đã chuyển sang giao diện dự phòng.',
    'draft_saved': 'Bài chưa hoàn thành. Tiến độ đã lưu; chưa chấm điểm tổng kết.',
    'draft_unsaved': 'Chưa lưu được bản nháp. Bạn có thể tiếp tục trong phiên này.',
    'quiz_completed': 'Đã trả lời {completed}/{total} câu',
    'correct_feedback': '✓ Đúng',
    'incorrect_feedback': '✗ Chưa đúng',
    'settings_saved': 'Đã lưu cỡ chữ và màu riêng cho Title/Content. Mở lại bài học để xem thay đổi.',
}


def t(key, **values):
    return STRINGS[key].format(**values)
