# -*- coding: utf-8 -*-
"""数据自动化更新器（T1）

触发方式：
  1. --once       立即检查并更新一次后退出（挂 npm predev/prestart 与计划任务）
  2. --daemon     守护模式：启动时先检查更新，随后在每天 01:00~01:30 窗口触发
逻辑：
  - 新鲜度检查：库 MAX(DateTime).date() == 今天 -> 最新，跳过（不改库、不爬取）
  - 更新链：getAQI.sync_all_city_day_aqi()（全量爬取，保留限速）→ analysis.main.run()（统计+预测+分析）
状态：script/auto/auto_status.json + script/auto/auto_update.log
"""
import json
import subprocess
import sys
import time
from datetime import datetime, date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # 项目根
SA = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'script'))

import sqlite3

DB = ROOT / 'prisma' / 'weather.db'
STATUS = SA / 'auto_status.json'
LOG = SA / 'auto_update.log'

WINDOW_START_H, WINDOW_END_H = 1, 1        # 01:00 ~ 01:30
WINDOW_START_M, WINDOW_END_M = 0, 30


def log(msg):
    line = f'[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}'
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(line + '\n')
    print(line)


def set_status(**kw):
    st = {}
    if STATUS.exists():
        st = json.loads(STATUS.read_text(encoding='utf-8'))
    st.update(kw)
    st['last_check'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    STATUS.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding='utf-8')


def is_fresh():
    conn = sqlite3.connect(DB)
    mx = conn.execute('SELECT MAX(DateTime) FROM city_day_aqi').fetchone()[0]
    conn.close()
    today = date.today()
    latest = mx[:10] if mx else '-'
    # 接口存在发布延迟：库最新可达"昨天"即视为已是最新（避免每天凌晨重复白爬）
    fresh = bool(mx) and latest >= (today - timedelta(days=1)).strftime('%Y-%m-%d')
    return fresh, latest


def run_update():
    try:
        log('开始自动更新：爬取 AQI（getAQI.sync_all_city_day_aqi）')
        from req.getAQI import sync_all_city_day_aqi
        sync_all_city_day_aqi()
        log('爬取完成，运行分析（analysis.main.run）')
        from analysis.main import run
        run()
        log('分析与预测完成')
        set_status(updated=True, reason='auto_ok', last_update=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        return True
    except Exception as e:                                   # noqa: BLE001
        log(f'更新失败: {e!r}')
        set_status(updated=False, reason=f'error: {e}')
        return False


def check_and_update():
    fresh, mx = is_fresh()
    if fresh:
        log(f'数据已是最新（{mx}），跳过更新')
        set_status(updated=False, reason='already_fresh', latest=mx)
        return False
    log(f'库最新 {mx}，非最新，执行更新链')
    return run_update()


def in_window():
    now = datetime.now()
    return (now.hour == WINDOW_START_H and WINDOW_START_M <= now.minute <= WINDOW_END_M +
            15) or \
           (now.hour == WINDOW_END_H and now.minute <= WINDOW_END_M)


def daemon():
    log(f'守护模式启动，本次先检查一次')
    check_and_update()
    last_day = None
    while True:
        if in_window():
            today = date.today().isoformat()
            if last_day != today:
                last_day = today
                check_and_update()
        time.sleep(60)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--daemon':
        daemon()
    else:
        check_and_update()
