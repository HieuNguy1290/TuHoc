"""Original grade-two math items grouped by Exam Mode difficulty."""


def items(level, choice, fill, truth, order, matching):
    if level == 1:
        for n in (126, 238, 342, 457, 683):
            h, t = divmod(n // 10, 10)
            yield choice(f"Chữ số hàng chục của số {n} là chữ số nào?", t, h, n % 10)
        for n in (217, 325, 448, 569, 782):
            yield fill(f"Điền số liền sau của {n}. Chỉ ghi số.", n + 1)
        for left, right in ((241, 214), (391, 419), (652, 625), (790, 709), (806, 860)):
            yield truth(f"Số {left} lớn hơn số {right}.", left > right)
        for left, right in ((21, 14), (35, 22), (43, 25), (52, 16), (64, 13)):
            yield choice(f"{left} + {right} bằng bao nhiêu?", left + right, left + right + 10, left - right)
        for left, right in ((48, 15), (59, 26), (65, 23), (76, 34), (87, 52)):
            yield fill(f"Tính {left} − {right}. Chỉ ghi số.", left - right)
        for prompt, answer, wrong1, wrong2 in (
            ("Để đo chiều dài cây bút chì, em nên dùng đơn vị nào?", "xăng-ti-mét", "ki-lô-gam", "lít"),
            ("Để đo cân nặng của một bao gạo, em nên dùng đơn vị nào?", "ki-lô-gam", "mét", "lít"),
            ("Để đo lượng nước trong một can, em nên dùng đơn vị nào?", "lít", "giờ", "xăng-ti-mét"),
            ("Hình vuông có bao nhiêu cạnh?", 4, 3, 5),
            ("Thứ liền sau thứ Năm là thứ mấy?", "Thứ Sáu", "Thứ Tư", "Thứ Bảy"),
        ):
            yield choice(prompt, answer, wrong1, wrong2)
        for numbers in ((102, 120, 201), (315, 351, 513), (410, 401, 144),
                        (630, 600, 603), (517, 571, 715)):
            yield order("Chọn các số theo thứ tự từ bé đến lớn:", *map(str, sorted(numbers)))

    elif level == 2:
        for left, right in ((38, 27), (56, 19), (67, 25)):
            value = left + right
            yield choice(f"Tính {left} + {right}.", value, value - 10, value + 10)
        for left, right in ((63, 28), (72, 37), (94, 59)):
            yield fill(f"Tính {left} − {right}. Chỉ ghi số.", left - right)
        for n, answer in ((4, 8), (6, 12), (8, 15)):
            yield truth(f"Phép tính 2 × {n} có kết quả là {answer}.", 2 * n == answer)
        for n in (3, 5, 7):
            yield matching("Nối mỗi phép tính với kết quả của nó.",
                           (f"5 × {n}", str(5 * n)), (f"2 × {n}", str(2 * n)), (f"5 × {n + 1}", str(5 * (n + 1))))
        yield choice("Nếu bây giờ là 8 giờ sáng thì sau 2 giờ là mấy giờ?",
                     "10 giờ", "9 giờ", "6 giờ")
        yield choice("Một bao gạo nặng 10 kg, một bao nếp nặng 5 kg. Cả hai bao nặng bao nhiêu?",
                     "15 kg", "5 kg", "20 kg")
        yield choice("Can có 12 lít nước. Ba rót ra 3 lít. Can còn bao nhiêu nước?",
                     "9 lít", "15 lít", "8 lít")

    elif level == 3:
        for left, right in ((178, 246), (365, 287), (489, 176)):
            yield fill(f"Tính {left} + {right}. Chỉ ghi số.", left + right)
        for left, right in ((503, 178), (620, 294), (804, 267)):
            yield fill(f"Tính {left} − {right}. Chỉ ghi số.", left - right)
        for pencils, boxes in ((20, 5), (18, 2), (35, 5)):
            yield choice(f"Cô chia đều {pencils} cây bút chì vào {boxes} hộp. Mỗi hộp có mấy cây?",
                         pencils // boxes, pencils - boxes, boxes)
        for n, cm in ((1, 20), (2, 45), (3, 75)):
            yield fill(f"{n} m {cm} cm bằng bao nhiêu xăng-ti-mét? Chỉ ghi số.", n * 100 + cm)
        for prompt, pairs in (
            ("Nối số đo theo đề-xi-mét với số đo bằng nó theo xăng-ti-mét.", (("2 dm", "20 cm"), ("5 dm", "50 cm"), ("7 dm", "70 cm"))),
            ("Nối thời điểm với cách viết theo giờ và phút.", (("7 giờ rưỡi", "7 giờ 30 phút"), ("8 giờ", "8 giờ 00 phút"), ("9 giờ rưỡi", "9 giờ 30 phút"))),
            ("Nối phép chia với thương tương ứng.", (("20 : 5", "4"), ("10 : 2", "5"), ("14 : 2", "7"))),
        ):
            yield matching(prompt, *pairs)

    elif level == 4:
        for morning, added, sold in ((36, 24, 19), (48, 32, 27), (57, 23, 35)):
            yield fill(f"Quầy có {morning} trái cam. Má đem thêm {added} trái, rồi bán {sold} trái. "
                       "Quầy còn bao nhiêu trái cam? Chỉ ghi số.", morning + added - sold)
        for bags, given in ((5, 3), (6, 4), (8, 7)):
            yield choice(f"Có {bags} túi, mỗi túi 5 viên bi. Bé cho bạn {given} viên. Bé còn mấy viên bi?",
                         bags * 5 - given, bags * 5, bags * 5 + given)
        for total, used in ((20, 4), (30, 8), (40, 10)):
            yield fill(f"Chia đều {total} quyển tập vào 2 ngăn. Lấy ra {used} quyển từ một ngăn. "
                       "Ngăn đó còn bao nhiêu quyển? Chỉ ghi số.", total // 2 - used)
        for meters, cut in ((1, 35), (2, 65), (3, 75)):
            yield choice(f"Sợi dây dài {meters} m. Cắt đi {cut} cm. Sợi dây còn bao nhiêu xăng-ti-mét?",
                         100 * meters - cut, 100 * meters + cut, 100 * meters)
        for start in (7, 8, 9):
            yield choice(f"Lớp bắt đầu đọc sách lúc {start} giờ 30 phút sáng. "
                         "Đọc 30 phút thì xong. Lớp đọc xong lúc mấy giờ?",
                         f"{start + 1} giờ", f"{start} giờ 30 phút", f"{start + 1} giờ 30 phút")
        for cm, dm, meters in ((35, 4, 1), (54, 6, 2), (71, 8, 3)):
            yield order("Chọn các số đo theo thứ tự từ ngắn nhất đến dài nhất:",
                        f"{cm} cm", f"{dm} dm", f"{meters} m")

    elif level == 5:
        for baskets, sold in ((7, 8), (8, 6), (9, 11)):
            yield fill(f"Có {baskets} giỏ, mỗi giỏ 5 trái xoài. Bán {sold} trái, rồi mua thêm 6 trái. "
                       "Bây giờ có bao nhiêu trái xoài? Chỉ ghi số.", baskets * 5 - sold + 6)
        for total, extra in ((20, 3), (30, 4), (40, 2)):
            each = total // 5
            yield choice(f"Chia đều {total} nhãn dán cho 5 bạn. Lan được tặng thêm {extra} nhãn dán "
                         f"ngoài phần đã chia. Lan có bao nhiêu nhãn dán?", each + extra, each, each + 5)
        for a, b, c in ((12, 15, 18), (21, 26, 28)):
            yield fill(f"Đường gấp khúc có ba đoạn dài {a} cm, {b} cm và {c} cm. "
                       "Đường đó dài bao nhiêu xăng-ti-mét? Chỉ ghi số.", a + b + c)
        yield choice("Bảng số sách lớp đọc trong tuần: Thứ Hai 18 cuốn, thứ Ba 25 cuốn, "
                     "thứ Tư 21 cuốn. Hai ngày đọc nhiều sách nhất đọc được tổng cộng bao nhiêu cuốn?",
                     46, 43, 39)
        for digits in ((2, 5, 8), (3, 1, 6), (4, 3, 7)):
            smallest, _, biggest = sorted(digits)
            yield fill(f"Dùng ba chữ số {digits[0]}, {digits[1]}, {digits[2]}, mỗi chữ số đúng một lần. "
                       "Số có ba chữ số lớn nhất hơn số nhỏ nhất bao nhiêu đơn vị? Chỉ ghi số.", 99 * (biggest - smallest))
        for c1, c2 in ((45, 65), (55, 75), (65, 85)):
            total = c1 + c2
            yield choice(f"Hai đoạn dây dài {c1} cm và {c2} cm. Nối chúng lại, "
                         "bỏ qua chỗ nối. Cách viết nào đúng độ dài sợi dây?",
                         f"1 m {total - 100} cm", f"1 m {total - 90} cm", f"2 m {total - 100} cm")
        yield order("Xếp các thời điểm trong cùng một ngày từ sớm nhất đến muộn nhất.",
                    "7 giờ sáng", "12 giờ trưa", "3 giờ chiều", "7 giờ tối")
        yield choice("Na có một số viên bi. Nếu cho bạn 8 viên thì còn 17 viên. "
                     "Nếu thay vào đó Na cho bạn 5 viên thì còn bao nhiêu viên?", 20, 12, 25)
