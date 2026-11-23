"""Run: python VERIFY_PATCH03.py (no GUI required)."""
import sqlite3
from datetime import datetime,timedelta
from tuhoc.ui.learning_analytics_ui import aggregate

conn=sqlite3.connect(':memory:')
conn.execute('CREATE TABLE learning_sessions(id INTEGER PRIMARY KEY,student_id INTEGER,theme TEXT,level INTEGER,started REAL,seconds REAL,correct INTEGER,total INTEGER)')
now=datetime(2026,10,28,14,0)
def add(sid,theme,days,correct,total,seconds):
    conn.execute('INSERT INTO learning_sessions(student_id,theme,level,started,seconds,correct,total) VALUES(?,?,?,?,?,?,?)',
                 (sid,theme,1,(now-timedelta(days=days)).timestamp(),seconds,correct,total))
add(1,'vi:Family',0,8,10,120)
add(1,'Vioedu',1,5,10,60)
add(1,'Vioedu',45,10,10,100)
add(2,'vi:Family',0,1,10,20)
all_data=aggregate(conn,1,30,'all',now)
assert all_data['sessions']==2 and all_data['correct']==13 and all_data['total']==20
assert all_data['percent']==65 and all_data['seconds']==180
assert aggregate(conn,1,30,'vi',now)['sessions']==1
assert aggregate(conn,1,30,'en',now)['sessions']==1
assert aggregate(conn,1,7,'all',now)['sessions']==2
assert aggregate(conn,2,30,'all',now)['sessions']==1
assert aggregate(conn,3,30,'all',now)['percent'] is None
assert conn.execute('SELECT COUNT(*) FROM learning_sessions').fetchone()[0]==4
print('PASS: 8 checks (filter, totals, date range, student isolation, empty data, read-only)')
