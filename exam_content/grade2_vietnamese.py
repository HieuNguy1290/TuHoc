"""Original Southern Vietnamese grade-two language and reading items."""


def items(level, choice, fill, truth, order, matching, gaps, reading):
    if level == 1:
        for prompt, correct, first, second in (
            ("Từ nào gọi tên một loại trái cây?", "xoài", "chạy", "xanh"),
            ("Từ nào gọi tên một con vật?", "mèo", "cặp", "vở"),
            ("Từ nào gọi tên đồ dùng học tập?", "thước", "cá", "mưa"),
            ("Từ nào chỉ hoạt động?", "đọc", "bông", "trắng"),
            ("Từ nào chỉ màu sắc?", "vàng", "bàn", "hát"),
            ("Từ nào gọi tên một người trong gia đình?", "má", "mây", "mưa"),
            ("Đồ vật nào dùng để đựng cơm khi ăn?", "chén", "nón", "thước"),
            ("Từ nào chỉ tiếng kêu của con mèo?", "meo meo", "gâu gâu", "ò ó o"),
            ("Từ nào chỉ đặc điểm của trái ớt?", "cay", "ngủ", "bếp"),
            ("Chọn tiếng bắt đầu bằng chữ b.", "bông", "công", "hồng"),
            ("Chọn tiếng có vần ang.", "làng", "lồng", "lùng"),
            ("Chọn tiếng có vần ong.", "ong", "ông", "ung"),
            ("Chọn từ viết đúng.", "chăm chỉ", "trăm chỉ", "chăm trỉ"),
            ("Chọn từ viết đúng.", "nghỉ ngơi", "ngỉ ngơi", "nghĩ ngơi"),
            ("Chọn từ viết đúng.", "gõ cửa", "gỏ cửa", "ghõ cửa"),
            ("Chữ nào cần viết hoa trong tên bạn Lan?", "L", "a", "n"),
            ("Kết thúc câu «Em đi học» thường dùng dấu gì?", "Dấu chấm", "Dấu phẩy", "Dấu hai chấm"),
            ("Cuối câu «Bạn tên gì» nên dùng dấu gì?", "Dấu chấm hỏi", "Dấu phẩy", "Dấu chấm"),
            ("Khi gặp cô giáo vào buổi sáng, em nên nói gì?", "Em chào cô ạ!", "Em đi đây.", "Cô ăn cơm chưa?"),
            ("Khi bạn cho em mượn bút, em nên nói gì?", "Mình cảm ơn bạn.", "Bạn đi đi.", "Bạn tên gì?"),
        ):
            yield choice(prompt, correct, first, second)
        for prompt, answer in (
            ("Điền tiếng còn thiếu để được lời cảm ơn: «Cảm ___ bạn.»", "ơn"),
            ("Điền tiếng còn thiếu để được tên con vật kêu gâu gâu: «con ___».", "chó"),
            ("Điền tiếng còn thiếu để được tên loại trái có múi: «trái ___» (tiếng có vần am, bắt đầu bằng c).", "cam"),
            ("Điền tiếng có vần ôm để được cụm từ chỉ món ăn: «cơm ___».", "tôm"),
            ("Điền tiếng cuối của cụm từ «cây bút ___» chỉ loại bút có ruột than.", "chì"),
        ):
            yield fill(prompt, answer)
        for prompt, answer in (
            ("Câu «Con có đi học không?» dùng dấu chấm hỏi.", True),
            ("«Xanh» là từ chỉ một hoạt động.", False),
            ("Tiếng «nón» có thanh sắc.", True),
            ("Tiếng «bà» có thanh ngã.", False),
            ("Chữ cái đầu của tên người cần viết hoa.", True),
        ):
            yield truth(prompt, answer)
        for parts in (("Bé", "đọc", "sách."), ("Bà", "tưới", "cây."),
                      ("Má", "nấu", "cơm."), ("Ba", "sửa", "xe."), ("Mèo", "bắt", "chuột.")):
            yield order("Xếp các tiếng hoặc cụm từ thành câu.", *parts)
    elif level == 2:
        for prompt, correct, first, second in (
            ("Trong câu «Na quét sân», từ nào chỉ việc Na làm?", "quét", "Na", "sân"),
            ("Cặp từ nào có nghĩa trái ngược?", "dài – ngắn", "đẹp – xinh", "nhanh – mau"),
            ("Cặp từ nào có nghĩa gần nhau?", "vui – mừng", "cao – thấp", "vui – buồn"),
            ("Trong câu «Trái xoài chín vàng», từ nào chỉ màu?", "vàng", "trái", "chín"),
            ("Chọn câu được viết hoa và đặt dấu đúng.", "An đi học.", "nam tới lớp.", "An đi học,"),
        ):
            yield choice(prompt, correct, first, second)
        for prompt, answer in (
            ("Trong câu «Bé rửa chén», ghi từ chỉ hoạt động.", "rửa"),
            ("Điền từ trái nghĩa với «đóng» trong «đóng cửa».", "mở"),
            ("Trong câu «Chị xách giỏ đi chợ», ghi tiếng có dấu hỏi chỉ đồ dùng.", "giỏ"),
        ):
            yield fill(prompt, answer)
        yield matching("Nối đồ vật với công dụng phù hợp.", ("cục gôm", "tẩy chữ"), ("cây thước", "kẻ đường thẳng"), ("cây kéo", "cắt giấy"))
        yield matching("Nối con vật với tiếng kêu.", ("con vịt", "cạp cạp"), ("con chó", "gâu gâu"), ("con mèo", "meo meo"))
        yield matching("Nối hai từ có nghĩa trái ngược.", ("nóng", "lạnh"), ("sáng", "tối"), ("lên", "xuống"))
        yield order("Xếp thành câu kể việc bé giúp má sau bữa cơm.", "Bé", "rửa chén", "giúp má.")
        yield order("Xếp thành câu hỏi, bắt đầu bằng «Bạn».", "Bạn", "thích", "trái cây nào?")
        yield gaps("Điền «chén» hoặc «nón», mỗi từ dùng một lần. Bé đội {1} đi học. Bé rửa {2} sau bữa ăn.", "nón", "chén")
        yield gaps("Điền «tưới» hoặc «đọc», mỗi từ dùng một lần. Bà {1} cây. Em {2} sách.", "tưới", "đọc")
    elif level == 3:
        yield reading("Sáng Chủ nhật, Lan theo má ra chợ. Má mua rau, còn Lan chọn một bó bông cúc để tặng bà.",
                      "Lan chọn bông cúc để làm gì?", "Để tặng bà.", "Để bán ở chợ.", "Để làm món ăn.")
        yield reading("Mưa tạt vào hiên. Minh dời đôi dép vào nhà rồi đem khăn lau chỗ sàn bị ướt.",
                      "Minh làm gì sau khi dời đôi dép?", "Lấy khăn lau sàn.", "Đứng ngắm mưa.", "Đem dép ra sân.")
        yield reading("Ba cho An một trái xoài. An rửa sạch trái xoài, cắt ra rồi chia với em.",
                      "An làm gì trước khi cắt xoài?", "Rửa xoài.", "Chia cho em.", "Đem xoài cho ba.")
        yield reading("Lớp em trồng một cây bông giấy. Mỗi sáng, một bạn tưới cây. Sau vài tuần, cây ra bông hồng.",
                      "Các bạn chăm cây bằng cách nào?", "Thay nhau tưới cây.", "Hái bông mỗi sáng.", "Để cây trong tủ.")
        yield reading("Trên đường về, Duy thấy một chú mèo nép dưới mái hiên. Trời đang mưa. Duy lấy một cái hộp khô cho mèo trú.",
                      "Duy cho mèo trú ở đâu?", "Trong một cái hộp khô.", "Dưới gốc cây.", "Bên cạnh vũng nước.")
        for prompt, correct, first, second in (
            ("Câu «Bông cúc nở vàng ngoài sân» cho biết gì về bông cúc?", "Bông cúc có màu vàng.", "Bông cúc có màu đỏ.", "Bông cúc chưa nở."),
            ("Chọn câu nêu rõ nơi bé đang đọc sách.", "Bé đọc sách trong thư viện.", "Bé thích đọc sách.", "Bé thường đọc sách."),
            ("Chọn câu nói lời xin lỗi phù hợp khi em lỡ làm rớt bút của bạn.", "Mình xin lỗi vì làm rớt bút của bạn.", "Cảm ơn bạn đã mượn bút.", "Bạn cho mình đi trước nha."),
        ):
            yield choice(prompt, correct, first, second)
        yield order("Xếp thành câu kể, mở đầu bằng thời gian.", "Chiều nay,", "em và chị", "lau bàn", "giúp má.")
        yield order("Xếp thành câu theo nghĩa ba là người sửa xe.", "Ba", "sửa", "chiếc xe đạp", "cho em.")
        yield order("Xếp thành câu hỏi, mở đầu bằng «Sáng mai,».", "Sáng mai,", "bạn", "có đi", "thư viện không?")
        yield gaps("Điền «lạnh» hoặc «nóng», mỗi từ dùng một lần. Tô canh mới nấu còn {1}. Ly nước có đá thì {2}.", "nóng", "lạnh")
        yield gaps("Điền «khen» hoặc «nhắc», mỗi từ dùng một lần. Cô {1} Nam vì em làm bài tốt. "
                   "Cô {2} bạn xếp ghế trước khi ra về.", "khen", "nhắc")
        yield matching("Nối lời nói với tình huống phù hợp.", ("Mình xin lỗi.", "Lỡ làm bạn buồn"), ("Mình cảm ơn.", "Được bạn giúp"), ("Em chào cô ạ!", "Gặp cô giáo"))
        yield fill("Trong câu «Bé xếp tập vào cặp rồi đi học», ghi từ chỉ hoạt động bé làm với quyển tập.", "xếp")
    elif level == 4:
        yield reading("Mỗi chiều, bà rang đậu phộng. Nam thường đứng nhìn. Hôm nay, bà nhờ Nam nhặt bỏ hạt hư trước khi rang. Nam làm thiệt cẩn thận.",
                      "Vì sao Nam nhặt bỏ hạt hư?", "Để bà rang những hạt còn tốt.", "Để đậu tự mọc.", "Để bà khỏi cần rang đậu.")
        yield reading("Thấy sân còn ướt, cô dặn cả lớp chơi trong hiên. Lộc rủ bạn nhảy dây ngoài sân, nhưng Nga nhắc lại lời cô.",
                      "Nga nhắc Lộc vì điều gì?", "Sân ướt, chạy nhảy dễ trượt.", "Cô muốn cả lớp ra sân.", "Dây nhảy đã bị mất.")
        yield reading("Ngọc mang cuốn truyện tới lớp. Thấy Bình chưa có sách, Ngọc ngồi sát lại để hai bạn cùng đọc. Hết giờ, Bình cảm ơn Ngọc.",
                      "Chi tiết nào cho thấy Ngọc biết chia sẻ?", "Ngọc cùng Bình đọc cuốn truyện.", "Ngọc mang truyện tới lớp.", "Chuông báo hết giờ vang lên.")
        yield reading("Bà chuẩn bị chén, còn bé lấy muỗng. Khi cả nhà ngồi vào bàn, bé mời ông bà ăn cơm rồi mới ăn.",
                      "Việc nào cho thấy bé lễ phép?", "Bé mời ông bà ăn cơm.", "Bé đi lấy muỗng.", "Bà chuẩn bị chén.")
        yield reading("Một nhánh cây gãy sau cơn mưa. Khi thấy tổ chim trên nhánh, ba dặn Hà đứng xa. Ba gọi người lớn hỗ trợ đưa tổ lên chỗ an toàn.",
                      "Hà nên làm gì khi thấy tổ chim?", "Đứng xa và nghe lời ba.", "Tự leo lên cây.", "Lắc nhánh cây để xem chim.")
        yield reading("Sáng nay, Vy định mang đôi dép mới. Thấy trời mưa lớn, Vy lấy đôi dép cũ để đôi mới khỏi ướt.",
                      "Vì sao Vy đổi dép?", "Vy muốn giữ đôi dép mới khỏi ướt.", "Vy làm mất đôi dép cũ.", "Vy đi chân đất.")
        yield reading("Tới lớp, Hân thấy cục gôm dưới bàn. Bạn hỏi cả nhóm rồi mới cất cục gôm vào hộp đồ thất lạc.",
                      "Việc Hân làm trước khi cất cục gôm là gì?", "Hỏi xem cục gôm của ai.", "Đem gôm về nhà.", "Bỏ gôm vào thùng rác.")
        for prompt, correct, first, second in (
            ("Chọn câu kể rõ lý do em mang áo mưa.", "Vì trời có mây đen, em mang áo mưa.", "Em có một cái áo mưa.", "Em treo áo mưa sau cửa."),
            ("Câu nào cho thấy hai việc xảy ra theo thứ tự?", "Nam rửa tay rồi ăn cơm.", "Nam thích cơm và canh.", "Nam ăn cơm với cá."),
            ("Câu nào dùng dấu phẩy để ngăn các món đồ được liệt kê?", "Em mang tập, bút và thước.", "Em, mang tập bút và thước.", "Em mang, tập bút và thước."),
        ):
            yield choice(prompt, correct, first, second)
        yield order("Xếp thành câu nêu lý do, bắt đầu bằng «Vì».", "Vì trời mưa,", "cả lớp", "đọc truyện", "trong phòng.")
        yield order("Xếp thành câu kể, bắt đầu bằng «Sau khi».", "Sau khi ăn cơm,", "bé", "bưng chén", "vào bếp.")
        yield order("Xếp thành câu, bắt đầu bằng «Ở góc sân,».", "Ở góc sân,", "một bụi bông trang", "đang nở", "những chùm bông đỏ.")
        yield gaps("Điền «trước» hoặc «sau», mỗi từ dùng một lần. Em rửa tay {1} khi ăn. "
                   "Em rửa chén {2} khi ăn xong.", "trước", "sau")
        yield gaps("Điền «che» hoặc «lau», mỗi từ dùng một lần. Bé lấy dù {1} mưa. "
                   "Về tới nhà, bé dùng khăn {2} tóc.", "che", "lau")
        yield gaps("Điền «hỏi» hoặc «đáp», mỗi từ dùng một lần. Bạn Mai {1} giờ ra chơi. "
                   "Cô giáo {2} rằng còn năm phút nữa.", "hỏi", "đáp")
        yield truth("Trong câu «Vì trời mưa, bé chơi trong nhà», phần «Vì trời mưa» cho biết lý do.", True)
        yield truth("Câu «Em đọc sách ở thư viện» cho biết em đọc bao nhiêu cuốn sách.", False)
    elif level == 5:
        yield reading("Mấy ngày đầu, bé Như tưới cây mỗi sáng. Tối qua mưa lớn, đất trong chậu còn ướt. "
                      "Sáng nay, Như sờ đất rồi cất bình tưới.",
                      "Vì sao Như cất bình tưới?", "Vì đất trong chậu còn ướt.", "Vì cây đã chết.", "Vì Như làm mất bình.")
        yield reading("Phúc thấy bạn ngồi một mình trong giờ chơi. Phúc rủ bạn vô nhóm đá cầu. Lúc đầu bạn ngại, "
                      "nhưng cả nhóm chừa chỗ nên bạn vui vẻ vào chơi.", "Việc nào giúp bạn bớt ngại?",
                      "Nhóm chừa chỗ để bạn cùng chơi.", "Phúc cất trái cầu đi.", "Cả nhóm đổi trò rồi giải tán.")
        yield reading("Bà kể hồi nhỏ bà thường chèo xuồng đi chợ. Nay có cầu, bé đi bộ sang chợ với bà. "
                      "Hai bà cháu đứng trên cầu nhìn xuống dòng nước.",
                      "Cách đi chợ của bà hồi nhỏ khác bé bây giờ thế nào?", "Bà đi xuồng, còn bé đi bộ qua cầu.",
                      "Bà đi bộ qua cầu, còn bé đi xuồng.", "Cả hai đều đi xuồng.")
        yield reading("Cô giao nhóm làm bảng giới thiệu vườn trường. Lâm vẽ cây, Trúc viết tên cây, còn An dán hình. "
                      "Hết giờ, nhóm cùng xem lại bảng trước khi nộp.", "Nhóm đã làm việc theo cách nào?",
                      "Mỗi bạn làm một phần, rồi cả nhóm cùng kiểm tra.", "Chỉ Lâm làm từ đầu đến cuối.",
                      "Cả nhóm nộp bảng trước khi dán hình.")
        yield reading("Mưa vừa tạnh. Mai mang cơm tới cho bà. Ba chỉ con đường vòng vì lối tắt còn ngập. "
                      "Mai tới chậm hơn một chút nhưng hộp cơm vẫn khô.",
                      "Chọn câu tóm tắt đúng nhất.", "Mai mang cơm cho bà và đi đường vòng để tránh chỗ ngập.",
                      "Mai chờ tới hôm sau mới mang cơm.", "Ba mang cơm cho bà bằng lối tắt.")
        yield reading("Ba nói: «Con nhớ tắt đèn khi ra khỏi phòng.» Trí đã bước ra hành lang, nghe ba nhắc liền quay lại. "
                      "Rồi hai ba con đi chợ.", "Trí quay lại phòng để làm gì?",
                      "Để tắt đèn.", "Để lấy áo mưa.", "Để mở cửa sổ.")
        yield reading("Hôm qua Khôi quên trả truyện cho thư viện. Sáng nay em đặt truyện cạnh cặp. "
                      "Trước khi ra cửa, em nhìn thấy truyện và bỏ vào cặp ngay.",
                      "Khôi làm gì để nhớ mang truyện?", "Đặt truyện cạnh cặp.", "Để truyện dưới gối.", "Chờ bạn nhắc ở lớp.")
        yield reading("Ngoài sân có hai chậu cây. Chậu gần cửa ra bông đỏ. Chậu cạnh vòi nước chưa có bông. "
                      "Bé buộc một sợi dây xanh vào chậu chưa có bông để đánh dấu.", "Chậu buộc dây xanh nằm ở đâu?",
                      "Cạnh vòi nước.", "Gần cửa.", "Ở trong bếp.")
        yield reading("Bé viết: «Mời bà qua nhà con ăn cơm chiều thứ Bảy.» Má nhắc bé ghi thêm giờ. "
                      "Bé thêm vào lời mời: «Lúc 5 giờ chiều.»", "Vì sao cần ghi thêm giờ?",
                      "Để bà biết thời điểm qua nhà.", "Để bà biết tên món ăn.", "Để bà biết ai nấu cơm.")
        yield choice("Câu nào giữ đủ ý «Vy đến trễ vì xe bị hư» khi đưa lý do lên đầu?",
                     "Vì xe bị hư, Vy đến trễ.", "Vì đến trễ, xe của Vy bị hư.", "Xe Vy bị hư sau khi Vy tới.")
        yield choice("Mai muốn mượn cuốn truyện em đang xem. Câu nào vừa là lời đề nghị vừa lịch sự?",
                     "Khi nào xem xong, bạn cho mình mượn cuốn truyện nha?",
                     "Bạn đưa cuốn truyện đây liền!", "Cuốn truyện của bạn có nhiều hình.")
        yield choice("Em viết lời nhắn dặn bạn tưới cây chiều thứ Sáu. Lời nhắn nào cho biết rõ việc và thời gian?",
                     "Chiều thứ Sáu, bạn tưới cây giùm mình nha.", "Bạn làm giùm mình nha.", "Chiều thứ Sáu có thể trời nắng.")
        yield order("Xếp thành câu nối hai việc theo thứ tự, bắt đầu bằng «Sau khi».",
                    "Sau khi đọc xong,", "Na", "cất sách", "rồi mới ra sân.")
        yield order("Xếp thành câu nối lý do với việc làm, bắt đầu bằng «Vì».",
                    "Vì gió thổi mạnh,", "ba", "khép cửa sổ", "trong phòng khách.")
        yield gaps("Điền «nên» hoặc «vì», mỗi từ dùng một lần. Trời mưa {1} cả lớp ở trong phòng. "
                   "Nam mang dù {2} sợ bị ướt.", "nên", "vì")
        yield gaps("Điền «nhưng» hoặc «và», mỗi từ dùng một lần. Trời đã tối {1} đường vẫn sáng nhờ đèn. "
                   "Mẹ cất chén {2} bé lau bàn.", "nhưng", "và")
        yield matching("Nối phần mở đầu với phần còn lại để câu có nghĩa rõ ràng.",
                       ("Vì trời nắng,", "bé đội nón."), ("Khi chuông reo,", "cả lớp vào học."),
                       ("Sau bữa cơm,", "em rửa chén."))
