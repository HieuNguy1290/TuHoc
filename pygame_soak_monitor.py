"""Non-invasive long-run Pygame process monitor. Python 3.9+; pip install psutil.

Usage: python pygame_soak_monitor.py --pid 1234 --hours 4 --interval 2
Stop with Ctrl+C. Results are written incrementally and analyzed at shutdown.
"""
import argparse
import csv
import datetime as dt
import json
import statistics
import time
from collections import deque
from pathlib import Path


def summarize(rows, interval):
    if len(rows) < 2:
        return {'status': 'insufficient_samples', 'samples': len(rows)}
    rss = [float(r['rss_mib']) for r in rows]
    threads = [int(r['threads']) for r in rows]
    handles = [int(r['handles']) for r in rows if r['handles'] != '']
    # Compare steady-state windows, avoiding false positives from initial loading.
    window = max(3, min(len(rows)//5, int(600 / interval)))
    start = statistics.median(rss[:window]); end = statistics.median(rss[-window:])
    delta = end-start
    return {
        'status': 'measured_not_proven_leak', 'samples': len(rows),
        'elapsed_minutes': round((float(rows[-1]['elapsed_s'])-float(rows[0]['elapsed_s']))/60, 2),
        'rss_start_mib_median': round(start,2), 'rss_end_mib_median': round(end,2),
        'rss_delta_mib': round(delta,2), 'rss_peak_mib': round(max(rss),2),
        'thread_start': threads[0], 'thread_end': threads[-1], 'thread_peak': max(threads),
        'handle_start': handles[0] if handles else None,
        'handle_end': handles[-1] if handles else None,
        'handle_peak': max(handles) if handles else None,
        'possible_growth_flag': len(rows)>=max(30,int(1800/interval)) and delta>max(80, start*0.2),
        'note': 'RSS growth is a screening signal, not proof of a leak. Repeat identical UI cycles and inspect heap/handles.'
    }


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--pid',type=int,required=True)
    ap.add_argument('--hours',type=float,default=4)
    ap.add_argument('--interval',type=float,default=2)
    ap.add_argument('--output',default='pygame_soak.csv')
    args=ap.parse_args()
    if args.pid<=0 or args.hours<=0 or args.interval<0.2: ap.error('invalid PID/hours/interval')
    try: import psutil
    except ImportError: ap.error('psutil is required: pip install psutil')
    process=psutil.Process(args.pid)
    created=process.create_time()
    process.cpu_percent(None)
    path=Path(args.output); path.parent.mkdir(parents=True,exist_ok=True)
    columns=['utc','elapsed_s','rss_mib','vms_mib','cpu_percent','threads','handles','read_bytes','write_bytes','status']
    rows=[]; start=time.monotonic(); status='completed'
    try:
        with path.open('w',newline='',encoding='utf-8') as f:
            writer=csv.DictWriter(f,fieldnames=columns); writer.writeheader()
            while time.monotonic()-start < args.hours*3600:
                try:
                    if abs(process.create_time()-created)>0.001: status='pid_reused';break
                    mem=process.memory_info()
                    io=process.io_counters() if hasattr(process,'io_counters') else None
                    try: handles=process.num_handles() if hasattr(process,'num_handles') else ''
                    except (psutil.AccessDenied,psutil.Error): handles=''
                    row={'utc':dt.datetime.now(dt.timezone.utc).isoformat(),
                         'elapsed_s':round(time.monotonic()-start,2),
                         'rss_mib':round(mem.rss/1048576,3),'vms_mib':round(mem.vms/1048576,3),
                         'cpu_percent':process.cpu_percent(None),'threads':process.num_threads(),
                         'handles':handles,'read_bytes':getattr(io,'read_bytes',''),
                         'write_bytes':getattr(io,'write_bytes',''),'status':process.status()}
                    writer.writerow(row); f.flush(); rows.append(row)
                except (psutil.NoSuchProcess,psutil.ZombieProcess): status='process_exited';break
                except psutil.AccessDenied: status='access_denied';break
                time.sleep(args.interval)
    except KeyboardInterrupt: status='interrupted'
    result=summarize(rows,args.interval);result['monitor_status']=status;result['pid']=args.pid
    report=path.with_suffix('.summary.json')
    report.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    print('CSV:',path,'Summary:',report)

if __name__=='__main__': main()
