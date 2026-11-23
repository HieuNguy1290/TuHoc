"""Offscreen Pygame review embedded in a Tk Frame; no SDL display or worker."""
from tuhoc.exercises.question_prompt import display_prompt
import logging
import math
import os
import re
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

LOG = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'TuHoc' / 'loi_ung_dung.log'

INK = (35, 52, 78)
GREEN = (33, 145, 101)
RED = (190, 55, 70)
GRAY = (95, 107, 115)
GOLD = (245, 178, 31)


def report_error(exc):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=str(LOG), level=logging.ERROR, encoding='utf-8')
    logging.exception('Lỗi màn hình tra đáp án: %s', exc)


def available():
    try:
        import pygame
        from PIL import Image, ImageTk
        return True
    except ImportError:
        return False


def show_review(master, payload, on_action, **kwargs):
    if not available():
        messagebox.showerror('Thiếu thư viện', 'Thiếu thư viện pygame, hãy cài bằng pip install pygame', parent=master)
        return None
    try:
        panel = ReviewPanel(master, payload, on_action, **kwargs)
        panel.pack(fill='both', expand=True)
        return panel
    except Exception as exc:
        report_error(exc)
        messagebox.showerror('Lỗi tra đáp án', f'Không thể hiển thị kết quả: {exc}\nChi tiết: {LOG}', parent=master)
        return None


class ReviewPanel(tk.Frame):
    def __init__(self, master, payload, on_action, on_audio=None, **kwargs):
        super().__init__(master, bg='#f0f7fb', **kwargs)
        import pygame
        from PIL import Image, ImageTk
        from tuhoc.exercises.pygame_window_utils import vietnamese_font
        self.pg, self.Image, self.ImageTk = pygame, Image, ImageTk
        self.font_factory = lambda size, bold=False: vietnamese_font(pygame, size, bold)
        self.payload, self.on_action, self.on_audio = payload, on_action, on_audio
        self.rows = payload.get('rows', [])
        self.index, self.scroll, self.confirming = None, 0, False
        self.max_scroll = 0
        self.alive, self.job, self.surface, self.photo = True, None, None, None
        self.buttons = []
        # width/height nhỏ để canvas ăn theo chỗ được chia, không giữ mặc định 10c x 7c
        self.canvas = tk.Canvas(self, bg='#f0f7fb', highlightthickness=0, takefocus=1, width=320, height=240)
        self.canvas.pack(fill='both', expand=True)
        self.image_id = self.canvas.create_image(0, 0, anchor='nw')
        self.canvas.bind('<Configure>', self._resize)
        self.canvas.bind('<Button-1>', self._click)
        self.canvas.bind('<Motion>', self._hover)
        self.canvas.bind('<MouseWheel>', self._wheel)
        self.canvas.bind('<Button-4>', lambda e: self._wheel(e, 1))
        self.canvas.bind('<Button-5>', lambda e: self._wheel(e, -1))
        self.canvas.bind('<KeyPress>', self._key)
        self.bind('<Destroy>', self._destroy, add='+')
        self.canvas.focus_set()
        self._bind_target = self._bind_id = None
        self._expand_chain()
        self.after(50, self._fit_to_window)
        self.after(300, self._fit_to_window)
        try:
            host, _ = self._host()
            self._bind_target = host or self.winfo_toplevel()
            self._bind_id = self._bind_target.bind('<Configure>', self._fit_to_window, add='+')
        except tk.TclError:
            pass
        self._tick()

    # ------------------------------------------------------------------ layout
    def _expand_chain(self):
        """Bắt mọi frame cha (tới cửa sổ chính) chiếm hết chỗ trống."""
        top = self.winfo_toplevel()
        w = self.master
        while w is not None and w is not top:
            try:
                mgr = w.winfo_manager()
                if mgr == 'pack':
                    w.pack_configure(fill='both', expand=True)
                elif mgr == 'grid':
                    info = w.grid_info()
                    w.master.rowconfigure(info['row'], weight=1)
                    w.master.columnconfigure(info['column'], weight=1)
                    w.grid_configure(sticky='nsew')
            except tk.TclError:
                pass
            w = w.master

    def _host(self):
        """Canvas cuộn của trang đang chứa panel (main.layout) và widget con trực tiếp của nó."""
        top = self.winfo_toplevel()
        child, w = self, self.master
        while w is not None and w is not top:
            if isinstance(w, tk.Canvas):
                return w, child
            child, w = w, w.master
        return None, None

    def _fit_to_window(self, event=None):
        """Đặt chiều cao canvas pygame vừa đúng phần còn trống của trang, không dư (để nút không tụt xuống)."""
        if not self.alive or not self.winfo_exists():
            return
        try:
            host, child = self._host()
            if host is not None:
                if host.winfo_height() <= 1:
                    return
                # khoảng cách từ đỉnh trang tới panel (tiêu đề...) không đổi khi trang cuộn
                offset = self.canvas.winfo_rooty() - child.winfo_rooty()
                avail = host.winfo_height() - offset - 20  # 16px lề dưới của trang
            else:
                top = self.winfo_toplevel()
                if top.winfo_height() <= 1:
                    return
                bottom = min(top.winfo_rooty() + top.winfo_height(), self.winfo_screenheight() - 48)
                avail = bottom - self.canvas.winfo_rooty() - 12
            if avail > 240 and abs(self.canvas.winfo_height() - avail) > 2:
                self.canvas.configure(height=int(avail))
        except tk.TclError:
            pass

    def _resize(self, event):
        self.surface = None
        self.scroll = 0

    def _destroy(self, event):
        if event.widget is not self:
            return
        self.alive = False
        if self._bind_target is not None:
            try: self._bind_target.unbind('<Configure>', self._bind_id)
            except tk.TclError: pass
            self._bind_target = self._bind_id = None
        if self.job is not None:
            try: self.after_cancel(self.job)
            except tk.TclError: pass
        self.job = None
        self.surface = self.photo = None

    def _tick(self):
        self.job = None
        if not self.alive or not self.winfo_exists(): return
        try:
            self.render()
        except Exception as exc:
            self.alive = False
            report_error(exc)
            messagebox.showerror('Lỗi tra đáp án', f'{exc}\nChi tiết: {LOG}', parent=self)
            return
        if self.alive and self.winfo_exists(): self.job = self.after(33, self._tick)

    # ------------------------------------------------------------------ drawing helpers
    def _font(self, size=19, bold=False):
        return self.font_factory(max(11, int(size)), bold)

    def _lines(self, value, font, width):
        """Wrap text, including tokens longer than the available width."""
        result = []
        for paragraph in str(value).split('\n'):
            line = ''
            for word in paragraph.split():
                candidate = (line + ' ' + word).strip()
                if font.size(candidate)[0] <= width:
                    line = candidate
                    continue
                if line: result.append(line); line = ''
                for char in word:
                    if line and font.size(line + char)[0] > width:
                        result.append(line); line = ''
                    line += char
            result.append(line)
        return result

    def _text(self, value, x, y, width, size=19, color=INK, bold=False):
        font = self._font(size, bold)
        for line in self._lines(value, font, max(20, width)):
            if line: self.surface.blit(font.render(line, True, color), (int(x), int(y)))
            y += font.get_height() + 6
        return y

    def _icon(self, kind, x, y, size, color):
        """Vẽ biểu tượng bằng hình học, không phụ thuộc font (font tiếng Việt thiếu ✓ ✕ ⭐ 🔊)."""
        pg, s = self.pg, self.surface
        x, y, size = int(x), int(y), max(8, int(size))
        t = max(2, size // 6)
        if kind == 'ok':
            pg.draw.lines(s, color, False, [(x + size * .08, y + size * .55), (x + size * .38, y + size * .85), (x + size * .92, y + size * .15)], t)
        elif kind == 'no':
            pg.draw.line(s, color, (x + size * .15, y + size * .15), (x + size * .85, y + size * .85), t)
            pg.draw.line(s, color, (x + size * .85, y + size * .15), (x + size * .15, y + size * .85), t)
        elif kind == 'wait':
            pg.draw.circle(s, color, (x + size // 2, y + size // 2), max(3, size // 2 - 1), 2)
        elif kind == 'star':
            cx, cy, r = x + size / 2, y + size / 2, size / 2
            pts = [(cx + (r if i % 2 == 0 else r * .45) * math.cos(-math.pi / 2 + i * math.pi / 5),
                    cy + (r if i % 2 == 0 else r * .45) * math.sin(-math.pi / 2 + i * math.pi / 5)) for i in range(10)]
            pg.draw.polygon(s, color, pts)
        elif kind == 'sound':
            pg.draw.polygon(s, color, [(x, y + size * .35), (x + size * .3, y + size * .35), (x + size * .6, y + size * .1),
                                       (x + size * .6, y + size * .9), (x + size * .3, y + size * .65), (x, y + size * .65)])
            pg.draw.arc(s, color, (x + size * .45, y + size * .2, size * .5, size * .6), -1.0, 1.0, 2)

    def _marked(self, mark, value, x, y, width, size=19, color=INK, bold=False):
        """Dòng chữ có biểu tượng ở đầu; mark=None vẫn chừa chỗ để các dòng thẳng hàng."""
        box = self._font(size, bold).get_height()
        if mark: self._icon(mark, x, y + 3, box - 6, color)
        return self._text(value, x + box + 6, y, width - box - 6, size, color, bold)

    def _stars(self, count, x, y, size=34):
        for i in range(count):
            self._icon('star', x + i * (size + 8), y, size, GOLD)
        return y + size

    def _button(self, name, title, rect, disabled=False, icon=None):
        pg = self.pg
        r = pg.Rect(*(int(v) for v in rect))
        pg.draw.rect(self.surface, (144,159,173) if disabled else (24,129,204), r, border_radius=9)
        font = self._font(15, True)
        label = font.render(title, True, 'white')
        lr = label.get_rect(center=r.center)
        if icon:
            isz = font.get_height() - 2
            lr.centerx += (isz + 8) // 2
            self._icon(icon, lr.left - isz - 8, r.centery - isz // 2, isz, (255, 255, 255))
        self.surface.blit(label, lr)
        if not disabled: self.buttons.append((name, r))

    def _image(self, path, x, y, width, height):
        if not path: return
        try:
            img = self.pg.image.load(str(path))
            ratio = min(width / img.get_width(), height / img.get_height())
            img = self.pg.transform.smoothscale(img, (max(1,int(img.get_width()*ratio)), max(1,int(img.get_height()*ratio))))
            self.surface.blit(img, img.get_rect(center=(int(x+width/2),int(y+height/2))))
        except (OSError, ValueError, self.pg.error): pass

    # ------------------------------------------------------------------ dạng "nghe và chọn hình"
    def _draw_image_options(self, q, answer, y, w):
        """Lưới hình đáp án: viền xanh = đáp án đúng, viền đỏ = hình bạn chọn sai."""
        pg = self.pg
        opts = []
        for opt in q.get('image_options') or []:
            ref = str(opt.get('image', '') if isinstance(opt, dict) else opt).strip()
            label = str(opt.get('label', '') or '').strip() if isinstance(opt, dict) else ''
            if ref: opts.append((ref, label))
        if not opts:
            return self._text('Bài làm: ' + str(answer or ''), 35, y, w - 70, 18) + 8
        accepted = q.get('accepted_answers') or [q.get('answer', '')]
        if isinstance(accepted, str): accepted = accepted.split('|')
        accepted = {str(a).strip() for a in accepted}
        picked = str(answer or '').strip()
        files = q.get('_choice_images') or {}
        cols = min(3, len(opts))
        gap, left = 12, 29
        cw = max(90, (w - 58 - gap * (cols - 1)) // cols)
        ih, lh = 120, 26
        ch = ih + lh + 12
        for i, (ref, label) in enumerate(opts):
            r, c = divmod(i, cols)
            x, top = left + c * (cw + gap), int(y + r * (ch + gap))
            right, chosen = ref in accepted, ref == picked
            color = GREEN if right else RED if chosen else (200, 210, 222)
            box = pg.Rect(x, top, cw, ch)
            pg.draw.rect(self.surface, 'white', box, border_radius=12)
            pg.draw.rect(self.surface, color, box, 4 if (right or chosen) else 2, border_radius=12)
            path = files.get(ref) or (ref if Path(ref).is_file() else '')
            if path:
                self._image(path, x + 8, top + 8, cw - 16, ih)
            else:
                self._text('(không có hình)', x + 10, top + ih // 2, cw - 20, 15, GRAY)
            if label:
                self._text(label, x + 10, top + ih + 12, cw - 20, 16, color if (right or chosen) else INK, right or chosen)
            if right:
                self._icon('ok', x + cw - 30, top + 8, 22, GREEN)
            elif chosen:
                self._icon('no', x + cw - 30, top + 8, 22, RED)
        rows = (len(opts) + cols - 1) // cols
        y = int(y + rows * (ch + gap)) + 4
        if not picked:
            y = self._text('Bạn chưa chọn hình nào.', 35, y, w - 70, 17, GRAY) + 6
        return y

    # ------------------------------------------------------------------ dạng "hoàn thành câu"
    def _draw_gaps(self, q, answer, y, w):
        """Vẽ câu/hội thoại/đoạn văn với bài làm của học sinh nằm trong từng ô trống
        (xanh = đúng, đỏ = sai) theo đúng cách tách từ của new_exercise_runtime."""
        from tuhoc.exercises.new_exercise_runtime import gaps, expected
        from tuhoc.exercises.review_normalize import normalize
        parts = gaps(q)
        exp = expected(q) or []
        if not exp:
            return None
        if isinstance(answer, (list, tuple)):
            given = [str(a).strip() for a in answer]
        elif answer:
            given = [p.strip() for p in str(answer).split('|')]
        else:
            given = []
        given += [''] * (len(exp) - len(given))
        oks = [bool(g) and normalize(g) == normalize(e) for g, e in zip(given, exp)]

        pg = self.pg
        font = self._font(21)
        fh = font.get_height()
        box_h, line_h = fh + 10, fh + 18
        card_x, card_w = 20, w - 40
        inner_w = card_w - 32
        space = font.size(' ')[0]
        dialogue = q.get('dialogue') or []
        items, cx, cy, slot = [], 0, 0, 0
        for j, (source, indices) in enumerate(parts):
            hidden = set(indices)
            if q.get('type') == 'conversation_gaps' and j < len(dialogue):
                prefix = str(dialogue[j].get('speaker', '')) + ': '
                items.append(('s', prefix, cx, cy, font.size(prefix)[0], None))
                cx += font.size(prefix)[0]
            for i, m in enumerate(re.finditer(r'\S+', source)):
                token = m.group()
                if i in hidden and slot < len(exp):
                    label = given[slot] or '—'
                    bw = max(64, font.size(label)[0] + 24)
                    if cx and cx + bw > inner_w: cx, cy = 0, cy + line_h
                    items.append(('b', label, cx, cy, bw, oks[slot]))
                    cx += bw + 8
                    slot += 1
                else:
                    ww = font.size(token)[0]
                    if cx and cx + ww > inner_w: cx, cy = 0, cy + line_h
                    items.append(('t', token, cx, cy, ww, None))
                    cx += ww + space
            if j < len(parts) - 1:
                cx, cy = 0, cy + line_h + (6 if q.get('type') == 'conversation_gaps' else 0)
        info = '' if all(oks) else 'Đáp án đúng: ' + ' | '.join(exp)
        small = self._font(17)
        info_lines = self._lines(info, small, inner_w) if info else []
        card_h = cy + line_h + 16 + (len(info_lines) * (small.get_height() + 6) + 4 if info_lines else 0)

        pg.draw.rect(self.surface, (255, 255, 255), (card_x, int(y), card_w, int(card_h)), border_radius=14)
        ox, oy = card_x + 16, int(y) + 14
        for kind, label, ix, iy, bw, ok in items:
            if kind in ('t', 's'):
                color = (33, 104, 176) if kind == 's' else INK
                self.surface.blit(font.render(label, True, color), (ox + ix, oy + iy + (box_h - fh) // 2))
            else:
                col = GREEN if ok else RED
                r = pg.Rect(ox + ix, oy + iy, bw, box_h)
                pg.draw.rect(self.surface, (222, 243, 231) if ok else (251, 226, 229), r, border_radius=8)
                pg.draw.rect(self.surface, col, r, width=2, border_radius=8)
                img = font.render(label, True, col)
                self.surface.blit(img, img.get_rect(center=r.center))
        if info_lines:
            self._text(info, ox, oy + cy + line_h + 2, inner_w, 17, GREEN)
        return y + card_h + 12

    # ------------------------------------------------------------------ render
    def render(self):
        pg = self.pg
        w, h = max(320, self.canvas.winfo_width()), max(240, self.canvas.winfo_height())
        self.surface = pg.Surface((w, h))
        self.surface.fill((240, 247, 251))
        self.buttons = []
        pg.draw.rect(self.surface, (35, 52, 78), (0, 0, w, 83))
        title = 'KẾT QUẢ LEVEL' if self.index is None else f'TRA ĐÁP ÁN  •  Câu {self.index+1}/{len(self.rows)}'
        self._text(title, 24, 19, w - 48, min(28, max(18, w // 32)), 'white', True)

        # Cố định vị trí thanh nút ở đáy màn hình
        btn_height = 48
        btn_y = h - btn_height - 24

        if self.index is None:
            # 1. Màn hình KẾT QUẢ TỔNG KẾT
            content_top = 105
            content_bottom = btn_y - 16
            viewport = pg.Rect(20, content_top, w - 40, max(1, content_bottom - content_top))
            old = self.surface.get_clip()
            self.surface.set_clip(viewport)

            y = content_top - self.scroll
            stars = int(self.payload.get('stars', 0) or 0)
            if stars:
                y = self._stars(stars, 32, y, 34) + 16
            else:
                y = self._text('CỐ GẮNG THÊM NHÉ!', 32, y, w - 64, 29, INK, True) + 16
            y = self._text(f"Đúng {self.payload.get('correct', 0)}/{self.payload.get('total', 0)} câu  •  {self.payload.get('percent', 0):.0%}", 32, y, w - 64, 27, GREEN, True) + 18
            y = self._text('Thời gian làm bài: ' + str(self.payload.get('duration', '')), 32, y, w - 64, 19) + 14
            y = self._text(self.payload.get('message', ''), 32, y, w - 64, 18) + 12
            y = self._text(self.payload.get('unlock', ''), 32, y, w - 64, 17) + 10

            # Read-only performance breakdown. Keep it inside the existing
            # scroll viewport, above the pinned action buttons.
            insights = self.payload.get('insights') or {}
            by_type = insights.get('by_type') or []
            if by_type:
                y += 12
                y = self._text('KẾT QUẢ THEO DẠNG BÀI', 32, y, w - 64, 21, INK, True) + 8
                for item in by_type:
                    name = str(item.get('name', ''))
                    n = max(0, int(item.get('total', 0)))
                    good = max(0, min(n, int(item.get('correct', 0))))
                    y = self._text(f'{name}: {good}/{n} đúng', 34, y, w - 68, 17,
                                   GREEN if good == n else INK) + 5
                wrong = insights.get('wrong_numbers') or []
                if wrong:
                    preview = ', '.join(str(n) for n in wrong[:18])
                    if len(wrong) > 18:
                        preview += ', ...'
                    y += 8
                    y = self._text('Câu cần ôn lại: ' + preview, 32, y, w - 64, 18, RED, True) + 8
                    y = self._text('Chọn TRA ĐÁP ÁN để xem chi tiết từng câu.',
                                   32, y, w - 64, 16, GRAY) + 8
                else:
                    y = self._text('Tuyệt vời! Bạn đã trả lời đúng tất cả các câu.',
                                   32, y, w - 64, 17, GREEN) + 8

            total = y + self.scroll  # đáy nội dung, không phụ thuộc vị trí cuộn
            self.max_scroll = max(0, int(total - content_bottom))
            self.scroll = min(self.scroll, self.max_scroll)
            self.surface.set_clip(old)

            # Nút nằm ngay dưới nội dung; chỉ dồn xuống đáy khi nội dung dài (cần cuộn)
            bar_y = int(total + 24)
            if bar_y + btn_height > h - 24:
                bar_y = btn_y
            names = [('review', 'TRA ĐÁP ÁN'), ('back', 'VỀ BÀI HỌC'), ('retry', 'LÀM LẠI')]
            bw = max(80, (w - 48 - 16 * (len(names) - 1)) // len(names))
            for i, (name, label) in enumerate(names):
                self._button(name, label, (24 + i * (bw + 16), bar_y, bw, btn_height), name == 'review' and not self.rows)
        else:
            # 2. Màn hình TRA ĐÁP ÁN TỪNG CÂU
            row = self.rows[self.index]
            q = row.get('question') or {}
            answer = row.get('answer')
            ok = row.get('correct')

            top = 96
            bottom = btn_y - 16
            viewport = pg.Rect(15, top, w - 30, max(1, bottom - top))
            old = self.surface.get_clip()
            self.surface.set_clip(viewport)

            y = top + 10 - self.scroll
            y = self._text(display_prompt(q), 29, y, w - 58, 21, bold=True) + 10
            state = 'Chờ đánh giá' if ok is None else 'ĐÚNG' if ok else 'SAI'
            mark = 'wait' if ok is None else 'ok' if ok else 'no'
            color = GRAY if ok is None else GREEN if ok else RED
            y = self._marked(mark, state, 29, y, w - 58, 19, color, True) + 8

            image = q.get('_pygame_image') or q.get('image')
            if image:
                self._image(image, 29, y, min(360, w - 58), 190)
                y += 202

            if q.get('audio'):
                self._button('audio', 'NGHE LẠI', (29, y, min(160, w - 58), 39), icon='sound')
                y += 50

            kind = q.get('type', '')
            if kind == 'matching':
                from tuhoc.exercises.matching_widget import parse_pairs
                opts = q.get('options') or []
                if isinstance(opts, str):
                    opts = [v.strip() for v in opts.split('|') if v.strip()]
                pairs = parse_pairs(opts)
                expected = {i: i for i in range(len(pairs))}
                actual = answer if isinstance(answer, dict) else {}
                for left, right in actual.items():
                    valid = expected.get(left) == right
                    label = f'{pairs[left][0]} → {pairs[right][1]}' if isinstance(left, int) and isinstance(right, int) and 0 <= left < len(pairs) and 0 <= right < len(pairs) else f'{left} → {right}'
                    y = self._marked('ok' if valid else 'no', label, 35, y, w - 70, 18, GREEN if valid else RED) + 5
                for i, (left, right) in enumerate(pairs):
                    if actual.get(i) != i:
                        y = self._text(f'Đáp án đúng: {left} → {right}', 35, y, w - 70, 17, GREEN) + 5
                if not pairs:
                    y = self._text('Không có cặp nối.', 35, y, w - 70)
            elif kind == 'listening_image_choice':
                y = self._draw_image_options(q, answer, y, w)
            elif kind in ('image_multi_choice', 'picture_missing_letters', 'sentence_gaps', 'conversation_gaps', 'passage_gaps'):
                new_y = None
                if kind in ('sentence_gaps', 'conversation_gaps', 'passage_gaps'):
                    try:
                        new_y = self._draw_gaps(q, answer, y, w)
                    except Exception as exc:  # không để lỗi riêng dạng này làm sập cả màn hình
                        report_error(exc)
                if new_y is not None:
                    y = new_y
                else:
                    from tuhoc.exercises.new_exercise_review import draw
                    content_height = max(200, h // 2)
                    draw(self.surface, q, answer, y=int(y), height=content_height, scroll=0, area=pg.Rect(20, int(y), w - 40, content_height))
                    y += content_height + 12
            else:
                opts = q.get('options') or []
                if isinstance(opts, str):
                    opts = [v.strip() for v in opts.split('|') if v.strip()]
                if kind in ('choice', 'true_false', 'listening', 'listening_choice', 'picture_choice') and opts:
                    from tuhoc.exercises.review_normalize import normalize
                    accepted = q.get('accepted_answers') or [q.get('answer', '')]
                    if isinstance(accepted, str):
                        accepted = accepted.split('|')
                    for opt in opts:
                        right = normalize(opt) in {normalize(a) for a in accepted}
                        chosen = normalize(opt) == normalize(answer)
                        y = self._marked('ok' if right else 'no' if chosen else None, str(opt), 35, y, w - 70, 18, GREEN if right else RED if chosen else INK) + 7
                elif kind == 'multi_fill_blanks':
                    import re as _re
                    def _mfb(values):
                        return _re.sub(r'\[\[(\d+)\]\]', lambda m: (str(values[int(m.group(1)) - 1]).strip() or '....') if 0 < int(m.group(1)) <= len(values) else '....', str(q.get('blank_text', ''))).replace('\n', '  /  ')
                    given = [x.strip() for x in str(answer or '').split(' | ')] if answer else []
                    y = self._text('Bài làm: ' + _mfb(given), 35, y, w - 70, 18, GREEN if ok else RED) + 8
                    if ok is False:
                        y = self._text('Đáp án đúng: ' + _mfb(q.get('blank_answers') or []), 35, y, w - 70, 18, GREEN) + 8
                elif kind in ('image_sentence_fill', 'image_letter_pick', 'inline_dropdown_fill'):
                    from tuhoc.exercises.image_sentence_extension import fill_text, expected as isf_expected
                    given = [x.strip() for x in str(answer or '').split(' | ')] if answer else []
                    y = self._text('Bài làm: ' + fill_text(q, given).replace('\n', '  /  '), 35, y, w - 70, 18, GREEN if ok else RED) + 8
                    if ok is False:
                        y = self._text('Đáp án đúng: ' + fill_text(q, isf_expected(q)).replace('\n', '  /  '), 35, y, w - 70, 18, GREEN) + 8
                else:
                    y = self._text('Bài làm: ' + str(answer or ''), 35, y, w - 70, 18) + 8
                if ok is False and kind not in ('image_sentence_fill', 'image_letter_pick', 'inline_dropdown_fill', 'multi_fill_blanks'):
                    expected_value = str(q.get('answer', ''))
                    if kind == 'order' and '|' in expected_value:
                        parts = [v.strip() for v in expected_value.split('|') if v.strip()]
                        tiles = q.get('options') or []
                        if isinstance(tiles, str):
                            tiles = [v.strip() for v in tiles.split('|') if v.strip()]
                        expected_value = (''.join(parts) if tiles and all(len(str(v).strip()) == 1 for v in tiles)
                                          else ' '.join(parts))
                    y = self._text('Đáp án đúng: ' + expected_value, 35, y, w - 70, 18, GREEN)

            self.max_scroll = max(0, int(y + self.scroll - bottom + 12))
            self.scroll = min(self.scroll, self.max_scroll)
            self.surface.set_clip(old)

            labels = [('prev', '← TRƯỚC'), ('summary', 'TỔNG KẾT'), ('next', 'TIẾP →'), ('back', 'VỀ BÀI HỌC')]
            bw = max(65, (w - 32 - 8 * 3) // 4)
            for i, (name, label) in enumerate(labels):
                self._button(name, label, (16 + i * (bw + 8), btn_y, bw, btn_height), (name == 'prev' and self.index == 0) or (name == 'next' and self.index == len(self.rows) - 1))

        if self.confirming:
            overlay = pg.Surface((w, h), pg.SRCALPHA)
            overlay.fill((15, 25, 40, 170))
            self.surface.blit(overlay, (0, 0))
            rect = pg.Rect(max(8, w // 2 - 220), max(10, h // 2 - 100), min(440, w - 16), 200)
            pg.draw.rect(self.surface, 'white', rect, border_radius=15)
            self._text('Bạn muốn về bài học?', rect.x + 18, rect.y + 30, rect.width - 36, 22, bold=True)
            self.buttons = []
            self._button('cancel', 'Ở LẠI', (rect.x + 18, rect.bottom - 68, (rect.width - 48) // 2, 48))
            self._button('confirm_back', 'VỀ BÀI HỌC', (rect.centerx + 6, rect.bottom - 68, (rect.width - 48) // 2, 48))

        image = self.Image.frombytes('RGB', (w, h), pg.image.tostring(self.surface, 'RGB'))
        self.photo = self.ImageTk.PhotoImage(image)
        self.canvas.itemconfigure(self.image_id, image=self.photo)

    # ------------------------------------------------------------------ input
    def dispatch(self, event):
        """Accept synthetic pygame events (also used by Tk event adapters)."""
        pg = self.pg
        if event.type == pg.KEYDOWN:
            if event.key == pg.K_ESCAPE:
                self.confirming = not self.confirming
            elif not self.confirming and event.key == pg.K_LEFT:
                self._action('prev')
            elif not self.confirming and event.key == pg.K_RIGHT:
                self._action('next')
            elif not self.confirming and event.key == pg.K_RETURN:
                self._action('summary' if self.index is not None else 'review')
        elif event.type == pg.MOUSEWHEEL and not self.confirming:
            self.scroll = max(0, min(getattr(self, 'max_scroll', 0), self.scroll - event.y * 45))
        elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            for name, rect in reversed(self.buttons):
                if rect.collidepoint(event.pos):
                    self._action(name)
                    break

    def _action(self, action):
        if action == 'cancel':
            self.confirming = False
        elif action == 'confirm_back':
            self.confirming = False
            self.on_action('back')
        elif action == 'back':
            self.confirming = True
        elif action == 'review' and self.rows:
            self.index = 0
            self.scroll = 0
        elif action == 'summary':
            self.index = None
            self.scroll = 0
        elif action == 'prev' and self.index is not None:
            self.index = max(0, self.index - 1)
            self.scroll = 0
        elif action == 'next' and self.index is not None:
            self.index = min(len(self.rows) - 1, self.index + 1)
            self.scroll = 0
        elif action == 'retry':
            self.on_action('retry')
        elif action == 'audio' and self.on_audio and self.index is not None:
            self.on_audio(self.rows[self.index]['question'])

    def _click(self, event):
        self.canvas.focus_set()
        self.dispatch(self.pg.event.Event(self.pg.MOUSEBUTTONDOWN, button=1, pos=(event.x, event.y)))

    def _hover(self, event):
        self.pg.event.Event(self.pg.MOUSEMOTION, pos=(event.x, event.y), rel=(0, 0), buttons=(0, 0, 0))

    def _wheel(self, event, override=None):
        delta = override if override is not None else (1 if event.delta > 0 else -1)
        self.dispatch(self.pg.event.Event(self.pg.MOUSEWHEEL, x=0, y=delta))

    def _key(self, event):
        keys = {'Escape': self.pg.K_ESCAPE, 'Left': self.pg.K_LEFT, 'Right': self.pg.K_RIGHT, 'Return': self.pg.K_RETURN, 'KP_Enter': self.pg.K_RETURN}
        if event.keysym in keys:
            self.dispatch(self.pg.event.Event(self.pg.KEYDOWN, key=keys[event.keysym]))
            return 'break'
