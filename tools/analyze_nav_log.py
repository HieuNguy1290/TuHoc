"""Summarize measured navigation stages from a saved TuHoc profiler log."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
from statistics import median

STAGE = re.compile(r'\| stage=(\w+) \| ms=(\d+(?:\.\d+)?) \|')


def summarize(lines):
    timings=defaultdict(list)
    for line in lines:
        match=STAGE.search(line)
        if match:
            stage,reading=match.groups()
            timings[stage].append(float(reading))
    return sorted((dict(stage=stage,n=len(values),median_ms=round(median(values),2),
                        max_ms=max(values)) for stage,values in timings.items()),
                  key=lambda item:(-item['median_ms'],item['stage']))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('log',type=Path)
    args=parser.parse_args()
    print(json.dumps(summarize(args.log.read_text(encoding='utf-8').splitlines()),indent=2))


if __name__=='__main__':
    main()
