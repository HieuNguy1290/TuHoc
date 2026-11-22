"""Time real Tk page builds in a temporary profile and disposable checkout."""
import json
import os
from pathlib import Path
import random
from statistics import median
import sys
from time import perf_counter


def main():
    source=Path(sys.argv[1]).resolve()
    if not os.environ.get('LOCALAPPDATA'):
        raise SystemExit('Set LOCALAPPDATA to a temporary profile before measuring.')
    sys.path.insert(0,str(source))
    from main import App

    random.seed(2600)
    app=App()
    app.geometry('1140x780')
    app.update_idletasks()
    app.db.add_student('Học sinh kiểm thử',4)
    app.student=app.db.students()[0]
    results={}
    try:
        pages={'home':app.home,'journey_page':app.journey_page,
               'quiz_history_page':app.quiz_history_page}
        for name,callback in pages.items():
            samples=[]
            for _ in range(7):
                start=perf_counter()
                callback()
                app.update_idletasks()
                samples.append(round((perf_counter()-start)*1000,3))
            results[name]={'samples_ms':samples,'median_ms':median(samples)}
    finally:
        app._shutdown_app()
    print(json.dumps(results,indent=2))


if __name__=='__main__':
    main()
