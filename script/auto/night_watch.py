# -*- coding: utf-8 -*-
"""夜间观察器：每 5 分钟记录一次自动链路状态，直到 02:30"""
import json
import sqlite3
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(r'F:\_Qv0\opencode\软件开发实践课')
SA = ROOT / 'script' / 'auto'
WATCH_LOG = SA / 'watch.log'
STATUS = SA / 'auto_status.json'
DB = ROOT / 'prisma' / 'weather.db'
END = datetime(2026, 9, 7, 2, 30)


def snap():
    try:
        conn = sqlite3.connect(DB)
        mx = conn.execute('SELECT MAX(DateTime) FROM city_day_aqi').fetchone()[0]
        conn.close()
    except Exception as e:                            # noqa: BLE001
        mx = f'err:{e}'
    st = {}
    if STATUS.exists():
        try:
            st = json.loads(STATUS.read_text(encoding='utf-8'))
        except Exception:                              # noqa: BLE001
            st = {'read': 'error'}
    log_tail = ''
    try:
        lines = (SA / 'auto_update.log').read_text(encoding='utf-8').splitlines()
        log_tail = lines[-1][:80] if lines else '-'
    except Exception:                                  # noqa: BLE001
        log_tail = '-'
    return f"[{datetime.now():%H:%M:%S}] max={mx} | t3={st.get('t3','-')} | updated={st.get('updated','-')} | reason={st.get('reason','-')} | last={st.get('last_check','-')} | log={log_tail}"


def main():
    with open(WATCH_LOG, 'a', encoding='utf-8') as f:
        f.write(f'\n=== watcher start {datetime.now():%Y-%m-%d %H:%M:%S} ===\n')
    while datetime.now() < END:
        line = snap()
        with open(WATCH_LOG, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
        print(line)
        time.sleep(300)
    with open(WATCH_LOG, 'a', encoding='utf-8') as f:
        f.write(f'=== watcher end {datetime.now():%Y-%m-%d %H:%M:%S} ===\n')


if __name__ == '__main__':
    main()
