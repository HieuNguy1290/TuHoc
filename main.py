"""Start TuHoc from the repository root."""

if __name__ == '__main__':
    from multiprocessing import freeze_support

    freeze_support()
    from tuhoc.app.main import App

    App().mainloop()
elif __name__ == 'main':
    # Keep the historical import name bound to the same application module.
    import sys
    from tuhoc.app import main as application

    sys.modules[__name__] = application
