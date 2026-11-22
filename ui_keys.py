"""Keyboard routing shared by the Tk shell, help and lesson grid."""
import tkinter as tk

HELP = (
    ('F1','Mở bảng phím tắt'),
    ('Esc','Đóng hộp thoại, tắt công cụ hoặc quay lại'),
    ('Alt + ←','Quay lại trang trước'),
    ('Tab / Shift + Tab','Chuyển vùng chọn'),
    ('Enter / Space','Kích hoạt nút đang chọn'),
    ('↑ ↓ ← →','Di chuyển trong lưới Level'),
)
TEXT_INPUT = frozenset({'Entry','TEntry','Text','Spinbox','TSpinbox','TCombobox'})
GRID_MOVES = {'Left':-1,'Right':1,'Up':-5,'Down':5}


def action_for(key,state,widget_class):
    if widget_class in TEXT_INPUT:
        return None
    if key=='F1':
        return 'help'
    if key=='Escape' or key=='Left' and state&0x0008:
        return 'back'
    return None


def allow_shell(app,widget):
    return (isinstance(widget,tk.Misc) and widget.winfo_toplevel() is app
            and widget.winfo_class() not in TEXT_INPUT)


def focus_first(container):
    if not container.winfo_viewable():
        return
    def find(widget):
        for child in widget.winfo_children():
            if not child.winfo_viewable():
                continue
            kind=child.winfo_class()
            if kind in {'Button','TButton','TCombobox','Entry','Listbox'}:
                if str(child.cget('state'))!='disabled':
                    return child
            elif kind in {'Frame','TFrame','Labelframe','TLabelframe','Canvas'}:
                if kind in {'Frame','TFrame','Canvas'} and str(child.cget('takefocus'))=='1':
                    return child
                target=find(child)
                if target is not None:
                    return target
        return None
    first=find(container)
    if first is not None:
        first.focus_set()


def keyboard_button(widget):
    widget.configure(takefocus=True,highlightthickness=2)
    def invoke(_event):
        if str(widget.cget('state'))!='disabled':
            widget.invoke()
        return 'break'
    widget.bind('<Return>',invoke)
