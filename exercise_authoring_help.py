"""Read-only authoring help for exercise types. No question data is changed."""
import tkinter as tk
from tkinter import ttk

GUIDES = {
'image_multi_choice': ('Thêm 2-4 ảnh đáp án, chọn nút A/B/C/D bên cạnh ảnh đúng.', 'Ảnh A: quả táo\nẢnh B: quả cam\nChọn B nếu câu hỏi yêu cầu tìm quả cam.'),
'listening_image_choice': ('Chọn tệp âm thanh và các ảnh lựa chọn; đánh dấu ảnh tương ứng với nội dung nghe.', 'Âm thanh: “apple”\nẢnh A: quả táo; ảnh B: quả chuối\nĐáp án: A.'),
'picture_missing_letters': ('Chọn ảnh, nhập từ hoàn chỉnh rồi bấm vào các chữ cái muốn ẩn.', 'Ảnh: quả táo\nĐáp án hoàn chỉnh: APPLE\nBấm ẩn chữ P và L.'),
'sentence_gaps': ('Nhập câu hoàn chỉnh, bấm chọn các từ muốn ẩn; có thể thêm ảnh và từ gây nhiễu, phân cách bằng |.', 'Câu: I like red apples.\nChọn ẩn: red\nĐáp án nhiễu: blue | green'),
'conversation_gaps': ('Mỗi hàng là một lượt thoại: tên nhân vật, lời thoại và các từ cần ẩn. Thêm lượt bằng nút tương ứng.', 'An: How are you?\nBình: I am fine.\nChọn ẩn: fine'),
'passage_gaps': ('Nhập đoạn văn hoàn chỉnh, bấm chọn các từ cần ẩn, thêm từ nhiễu phân cách bằng | nếu cần.', 'Đoạn: Lan has a red bag. She likes it.\nẨn: red, likes'),
'image_multi_select': ('Nhập các lựa chọn, đánh dấu tất cả đáp án đúng. Có thể dùng ảnh làm ngữ cảnh.', 'Câu hỏi: Chọn động vật\nLựa chọn: mèo, bàn, chó\nĐúng: mèo và chó'),
 'text_multi_select': ('Nhập câu hỏi và các lựa chọn; đánh dấu nhiều đáp án đúng.', 'Câu hỏi: Chọn số chẵn\nLựa chọn: 2, 3, 4\nĐúng: 2 và 4'),
'audio_multi_select': ('Chọn âm thanh, nhập các lựa chọn và đánh dấu nhiều đáp án đúng.', 'Nghe: “cat and dog”\nChọn đúng: cat, dog'),
'image_write_answer': ('Chọn hình minh họa và nhập đáp án văn bản mong đợi.', 'Ảnh: con mèo\nĐáp án: con mèo'),
'image_underline_choice': ('Tạo nội dung lựa chọn có hình minh họa, chỉ định phần học sinh phải gạch chân.', 'Ảnh: con chó\nCác từ: mèo, chó, cá\nGạch chân: chó'),
'sentence_underline_words': ('Nhập câu và chọn từ/cụm từ cần gạch chân làm đáp án đúng.', 'Câu: Bé đang đọc sách.\nGạch chân: đọc'),
'dropdown_fill_blank': ('Nhập nội dung có ô trống và các phương án cho danh sách thả xuống; xác định phương án đúng.', 'Câu: Bé .... sách.\nLựa chọn: đọc, chạy\nĐúng: đọc'),
'multi_fill_blanks': ('Nhập nội dung có nhiều chỗ trống và khai báo đáp án tương ứng từng ô.', 'Câu: 2 + 3 = ....; 4 + 1 = ....\nĐáp án theo thứ tự: 5, 5'),
'image_sentence_fill': ('Dùng .... để đánh dấu từng chỗ trống. Nhập mỗi đáp án trên một dòng theo thứ tự ô trống.', 'Câu: Em .... học.\nĐáp án: đi'),
'image_letter_pick': ('Dùng .... để đánh dấu ô trống. Có thể nhóm bằng |a ... |a/, |b ... |b/ trong nội dung; khai báo |a đáp án 1, đáp án 2 ở phần đáp án. Đảo thứ tự trong cùng nhóm được chấp nhận khi bật chế độ nhóm. Câu cũ không dùng nhóm vẫn chấm theo thứ tự.', 'Nội dung:\nTừ chỉ hoạt động: |a ...., ...., .... |a/\nTừ chỉ sự vật: |b ...., .... |b/\n\nĐáp án:\n|a vẽ tranh, đánh cầu lông, đi học\n|b hoa hồng, quyển sách\n\nCó thể dùng |c ... |c/, |d ... |d/ ...'),
'inline_dropdown_fill': ('Đặt ô lựa chọn ngay trong câu, khai báo phương án và đáp án đúng cho từng vị trí.', 'Câu: Hôm nay trời [nắng/mưa].\nĐáp án đúng: nắng'),
}

def show_help(parent, kind, labels):
    win = tk.Toplevel(parent)
    win.title('Hướng dẫn sử dụng - Thêm bài tập')
    win.geometry('790x570')
    win.minsize(590, 420)
    win.transient(parent.winfo_toplevel())
    frame = ttk.Frame(win, padding=16)
    frame.pack(fill='both', expand=True)
    ttk.Label(frame, text='HƯỚNG DẪN TẠO BÀI TẬP', font=('Segoe UI', 15, 'bold')).pack(anchor='w', pady=(0, 10))
    names = list(labels)
    selector = ttk.Combobox(frame, state='readonly', values=[labels[k] for k in names], font=('Segoe UI', 10))
    selector.pack(fill='x', pady=(0, 12))
    viewer = tk.Text(frame, wrap='word', font=('Segoe UI', 11), padx=15, pady=15, relief='flat', bg='#F4F8F5')
    viewer.pack(fill='both', expand=True)
    viewer.tag_configure('heading', font=('Segoe UI', 12, 'bold'), foreground='#285D40', spacing1=12, spacing3=8)
    viewer.tag_configure('example', font=('Consolas', 11), lmargin1=12, lmargin2=12, spacing1=8)
    def update(event=None):
        key = names[selector.current()]
        description, example = GUIDES.get(key, ('Điền thông tin theo các trường trong trình chỉnh sửa.', ''))
        viewer.config(state='normal')
        viewer.delete('1.0', 'end')
        viewer.insert('end', 'CÁCH NHẬP\n', 'heading')
        viewer.insert('end', description + '\n')
        viewer.insert('end', '\nVÍ DỤ CẤU TRÚC\n', 'heading')
        viewer.insert('end', example + '\n', 'example')
        viewer.insert('end', '\nLƯU Ý\n', 'heading')
        viewer.insert('end', 'Ví dụ minh họa cách khai báo; các trường bắt buộc và kiểm tra dữ liệu thực tế vẫn do trình chỉnh sửa hiện tại quyết định.\n')
        viewer.config(state='disabled')
    selector.bind('<<ComboboxSelected>>', update)
    selector.current(names.index(kind) if kind in names else 0)
    update()
    ttk.Button(frame, text='Đóng', command=win.destroy).pack(anchor='e', pady=(12, 0))
    win.focus_set()

def add_help_icon(parent, kind, labels):
    bar = tk.Frame(parent, bg='white')
    bar.pack(fill='x', pady=(0, 6))
    button = tk.Label(bar, text='ⓘ', font=('Segoe UI', 15, 'bold'), bg='white', fg='#2878A0', cursor='hand2')
    button.pack(side='right', padx=(5, 8))
    button.bind('<Button-1>', lambda event: show_help(parent, kind, labels))
    tip = None
    def enter(event):
        nonlocal tip
        if tip is not None: return
        tip = tk.Toplevel(button)
        tip.wm_overrideredirect(True)
        tip.wm_geometry('+%d+%d' % (button.winfo_rootx()+18, button.winfo_rooty()+25))
        tk.Label(tip, text='hướng dẫn sử dụng', bg='#FFF7D8', fg='#333333', relief='solid', bd=1, padx=7, pady=4).pack()
    def leave(event):
        nonlocal tip
        if tip is not None:
            tip.destroy()
            tip = None
    button.bind('<Enter>', enter)
    button.bind('<Leave>', leave)
