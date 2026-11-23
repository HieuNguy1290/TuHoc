"""Message boxes compatible with the common Tk call signatures."""
import tkinter as tk
from tkinter import messagebox

from tuhoc.ui.ui_components import ConfirmDialog, Dialog


def _owner(parent):
    root=parent if parent is not None else tk._default_root
    if root is not None and root.winfo_exists() and root.winfo_viewable():
        return root
    return None


def _notice(title,message,tone,options,fallback):
    options=options.copy()
    owner=options.pop('parent',None)
    parent=_owner(owner)
    detail=options.pop('detail','')
    if parent is None or options or getattr(parent.winfo_toplevel(),'use_native_dialogs',False):
        return fallback(title,message,**fallback_options(owner,detail,options))
    Dialog(parent,title,str(message)+(f'\n\n{detail}' if detail else ''),
           primary='Đóng',tone=tone).show()
    return 'ok'


def fallback_options(parent,detail,options):
    if parent is not None:options['parent']=parent
    if detail:options['detail']=detail
    return options


def showinfo(title=None,message=None,**options):
    return _notice(title,message,'info',options,messagebox.showinfo)


def showwarning(title=None,message=None,**options):
    return _notice(title,message,'warning',options,messagebox.showwarning)


def showerror(title=None,message=None,**options):
    return _notice(title,message,'error',options,messagebox.showerror)


def askyesno(title=None,message=None,**options):
    parent=_owner(options.get('parent'))
    if parent is None or set(options)-{'parent','default'} or getattr(parent.winfo_toplevel(),'use_native_dialogs',False):
        return messagebox.askyesno(title,message,**options)
    return ConfirmDialog(parent,title,message,safe=options.get('default')!='yes').show()


askyesnocancel=messagebox.askyesnocancel
