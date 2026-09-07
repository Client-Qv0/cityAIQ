# -*- coding: utf-8 -*-
"""T3 检测与兜底：01:40 检查数据库是否已自动更新
- 已更新 -> 执行 T4 第二次对比（compare_prediction.py --mode t4）
- 未更新 -> 手动重试 update_daily（最多 3 次，间隔 15 分钟）；均失败 -> 终止 T4 并写入 FAILED
"""
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SA = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'script'))
from auto.update_daily import is_fresh, log, set_status, run_update

PY = sys.executable


def main():
    fresh, mx = is_fresh()
    if fresh:
        log(f'T3 检测：已自动更新（最新 {mx}），执行 T4 对比')
        set_status(t3='ok', latest=mx)
        subprocess.run([PY, str(SA / 'compare_prediction.py'), 't4'])
        log('T4 对比完成，生成 V5 最终版 PPT')
        subprocess.run([PY, str(SA / 'gen_v5_final.py')])
        return
    log(f'T3 检测：未更新（{mx}），开始手动重试（最多 3 次，间隔 15 分钟）')
    ok = False
    for i in range(1, 4):
        log(f'手动重试第 {i} 次：update_daily')
        if run_update():
            ok = True
            break
        if i < 3:
            time.sleep(15 * 60)
    if ok:
        fresh2, mx2 = is_fresh()
        log(f'重试成功（{mx2}），执行 T4 对比')
        set_status(t3='ok_after_retry', latest=mx2)
        subprocess.run([PY, str(SA / 'compare_prediction.py'), 't4'])
        log('T4 对比完成，生成 V5 最终版 PPT')
        subprocess.run([PY, str(SA / 'gen_v5_final.py')])
    else:
        set_status(t3='failed_3_retries')
        log('T3 结论：3 次重试均失败 —— 已终止 T4 第二次对比，需人工处理')


if __name__ == '__main__':
    main()
