"""Select hidden letters or words without changing indices during redraw."""
import re
import tkinter as tk
from tkinter import ttk


class TokenPicker(ttk.Frame):
    def __init__(self, parent, source, read, initial=(), *, letters=False, columns=8):
        super().__init__(parent)
        self.source = source
        self.read = read
        self.letters = letters
        self.columns = columns
        self.selected = set(initial or ())
        self.tokens = None
        self.refresh_job = None
        self.bind('<Destroy>', self.cancel_refresh, add='+')
        self.controls = ttk.Frame(self)
        self.controls.pack(anchor='w')
        self.preview = ttk.Label(self, wraplength=680)
        self.preview.pack(anchor='w', pady=(4, 0))
        self.clear_invalid = ttk.Button(self, text='Bỏ vị trí không còn trong văn bản',
                                        command=self.discard_invalid)
        for sequence in ('<KeyRelease>', '<FocusOut>', '<<Paste>>', '<<Cut>>'):
            source.bind(sequence, self.schedule_refresh, add='+')
        self.refresh()

    def schedule_refresh(self, _event=None):
        if self.refresh_job is None:
            self.refresh_job = self.after_idle(self.run_refresh)

    def cancel_refresh(self, _event=None):
        if self.refresh_job is not None:
            self.after_cancel(self.refresh_job)
            self.refresh_job = None

    def run_refresh(self):
        self.refresh_job = None
        self.refresh()

    def invalid_indices(self):
        return {i for i in self.selected if type(i) is not int or not 0 <= i < len(self.tokens)}

    def refresh(self):
        text = self.read(self.source)
        tokens = list(text) if self.letters else re.findall(r'\S+', text)
        if self.tokens != tokens:
            self.tokens = tokens
            for widget in self.controls.winfo_children():
                widget.destroy()
            self.variables = []
            for index, token in enumerate(tokens):
                selected = tk.BooleanVar(self, value=index in self.selected)
                self.variables.append(selected)
                ttk.Checkbutton(self.controls, text=token or ' ', variable=selected,
                                command=lambda i=index, v=selected: self.toggle(i, v.get())
                                ).grid(row=index // self.columns, column=index % self.columns, sticky='w')
        separator = '' if self.letters else ' '
        preview = separator.join('_' * len(token) if i in self.selected else token
                                 for i, token in enumerate(tokens))
        self.preview.configure(text=preview)
        if self.invalid_indices():
            self.clear_invalid.pack(anchor='w', pady=4)
        else:
            self.clear_invalid.pack_forget()

    def discard_invalid(self):
        self.selected.difference_update(self.invalid_indices())
        self.refresh()

    def toggle(self, index, selected):
        if selected:
            self.selected.add(index)
        else:
            self.selected.discard(index)
        self.refresh()

    def indices(self):
        self.refresh()
        if self.invalid_indices():
            raise ValueError('Vị trí chữ/từ ẩn nằm ngoài văn bản. Hãy bỏ vị trí cũ hoặc khôi phục văn bản.')
        return sorted(self.selected)
