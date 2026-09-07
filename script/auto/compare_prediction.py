# -*- coding: utf-8 -*-
"""预测准确性评估脚本（T2 第一次对比 / T4 第二次对比）

--mode t1 : 留一验证：前 13 天预测第 14 天 vs 实际（全城）
--mode t2 : 用完整 14 天预测下一天（预测日=窗口后一日），记录预测值 json
--mode t4 : 读 t2 记录的预测值，与库中实际值对比（凌晨更新后）
报告输出：无关文件/预测准确性评估.md 与 预测_下一天_记录.json
"""
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(r'F:\_Qv0\opencode\软件开发实践课')
sys.path.insert(0, str(ROOT / 'script'))
from analysis.predict import predict_next_aqi

DB = ROOT / 'prisma' / 'weather.db'
OUT_DIR = ROOT / '无关文件'
REPORT = OUT_DIR / '预测准确性评估.md'
PRED15 = OUT_DIR / '预测_下一天_记录.json'


def load_all():
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        """SELECT a.CityCode, c.CityName, a.DateTime, a.AQI
           FROM city_day_aqi a JOIN cities c ON a.CityCode = c.CityCode
           ORDER BY a.CityCode, a.DateTime""").fetchall()
    conn.close()
    cities = {}
    for code, name, dt, aqi in rows:
        cities.setdefault(code, {'name': name, 'dates': [], 'aqi': []})
        cities[code]['dates'].append(dt[:10])
        cities[code]['aqi'].append(aqi)
    return cities


def safe_predict(ys):
    try:
        return predict_next_aqi(ys)
    except Exception:
        return None


def mode_t1(cities):
    rows, errs = [], 0
    for code, v in cities.items():
        ys = v['aqi']
        if len(ys) < 5:
            errs += 1
            continue
        pred = safe_predict(ys[:-1])       # 前 13 天拟合
        actual = ys[-1]
        if pred is None or actual is None:
            errs += 1
            continue
        rows.append({'city': v['name'], 'code': code, 'pred': pred['predicted'],
                     'actual': actual, 'err': pred['predicted'] - actual,
                     'r2': pred['r2'], 'date': v['dates'][-1]})
    n = len(rows)
    mae = sum(abs(r['err']) for r in rows) / n
    mape = 100 * sum(abs(r['err']) / max(r['actual'], 1) for r in rows) / n
    within10 = 100 * sum(1 for r in rows if abs(r['err']) <= 10) / n
    bias = sum(r['err'] for r in rows) / n
    corr = None
    if n > 2:
        xs = [r['pred'] for r in rows]
        ys = [r['actual'] for r in rows]
        mx, my = sum(xs) / n, sum(ys) / n
        num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        den = (sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys)) ** 0.5
        corr = num / den if den else None
    top_err = sorted(rows, key=lambda r: -abs(r['err']))[:8]
    best = sorted(rows, key=lambda r: abs(r['err']))[:5]
    lines = [
        '# 最小二乘预测准确性评估',
        '',
        f'> 生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M")}；测试日：第 14 天 = {rows[0]["date"] if rows else "-"}',
        '',
        '## 测试 1：留一验证（前 13 天 → 预测第 14 天，与第 14 天实际值对比）',
        '',
        f'- 样本城市：**{n}**（失败 {errs}）',
        f'- 平均绝对误差 MAE：**{mae:.2f}**（AQI 单位）',
        f'- 平均相对误差 MAPE：**{mape:.2f}%**',
        f'- 平均误差（bias）：**{bias:+.2f}**（正=高估）',
        f'- |误差| ≤ 10 的城市占比：**{within10:.1f}%**',
        f'- 预测与实际 Pearson r：**{corr:.3f}**' if corr is not None else '',
        '',
        '### 误差最大城市（Top8）',
        '',
        '| 城市 | 预测 | 实际 | 误差 |',
        '|---|---|---|---|',
    ]
    for r in top_err:
        lines.append(f'| {r["city"]} | {r["pred"]:.1f} | {r["actual"]:.1f} | {r["err"]:+.1f} |')
    lines += ['', '### 预测最准城市（Top5）', '', '| 城市 | 预测 | 实际 | 误差 |', '|---|---|---|---|']
    for r in best:
        lines.append(f'| {r["city"]} | {r["pred"]:.1f} | {r["actual"]:.1f} | {r["err"]:+.2f} |')
    lines += [
        '',
        '## 测试 2：下一天预测值记录（第 15 天 = 09-06，待凌晨更新后对比）',
        '',
        '- 已保存预测值：`预测_下一天_记录.json`（338 城）',
        '- 对比结果将在凌晨数据自动更新后由 `compare_prediction.py --mode t4` 追加到本文件',
    ]
    return lines, rows


def mode_t2(cities):
    out = {}
    for code, v in cities.items():
        ys = v['aqi']
        if len(ys) < 5:
            continue
        pred = safe_predict(ys)
        if pred is None:
            continue
        out[str(code)] = {
            'CityName': v['name'],
            'last_day': v['dates'][-1],
            'predicted': round(pred['predicted'], 2),
            'lower95': round(pred['lower95'], 2),
            'upper95': round(pred['upper95'], 2),
            'r2': round(pred['r2'], 4),
        }
    PRED15.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f't2 saved {len(out)} cities -> {PRED15.name}')
    return out


def mode_t4(cities):
    preds = json.loads(PRED15.read_text(encoding='utf-8'))
    rows, skip = [], 0
    for code, p in preds.items():
        v = cities.get(int(code))
        if not v:
            skip += 1
            continue
        actuals = [(d, a) for d, a in zip(v['dates'], v['aqi']) if d == '2026-09-06']
        if not actuals:
            skip += 1
            continue
        actual = actuals[0][1]
        rows.append({'city': p['CityName'], 'code': code, 'pred': p['predicted'],
                     'actual': actual, 'err': p['predicted'] - actual, 'r2': p['r2']})
    n = len(rows)
    if n == 0:
        print('t4: 无 09-06 实际数据，等待凌晨更新后重试')
        return None
    mae = sum(abs(r['err']) for r in rows) / n
    mape = 100 * sum(abs(r['err']) / max(r['actual'], 1) for r in rows) / n
    lines = [
        '',
        f'## 测试 2（T4 第二次对比）：第 15 天（09-06）预测 vs 实际',
        '',
        f'- 可对比城市：**{n}**（跳过 {skip}）',
        f'- MAE：**{mae:.2f}**，MAPE：**{mape:.2f}%**',
        '',
        '| 城市 | 预测 | 实际 | 误差 | r² |',
        '|---|---|---|---|---|',
    ]
    for r in sorted(rows, key=lambda x: -abs(x['err']))[:10]:
        lines.append(f'| {r["city"]} | {r["pred"]:.1f} | {r["actual"]:.1f} | {r["err"]:+.1f} | {r["r2"]:.2f} |')
    # 幂等：若报告中已存在该段，先删除旧段再追加
    txt = REPORT.read_text(encoding='utf-8') if REPORT.exists() else ''
    import re as _re
    txt = _re.sub(r'\n## 测试 2（T4 第二次对比）[\s\S]*?(?=\n## |\Z)', '\n', txt)
    REPORT.write_text(txt + '\n'.join(lines) + '\n', encoding='utf-8')
    return True


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 't1'
    cities = load_all()
    if mode == 't1':
        lines, _ = mode_t1(cities)
        REPORT.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        print('t1 written:', REPORT.name)
    elif mode == 't2':
        mode_t2(cities)
    elif mode == 't4':
        result = mode_t4(cities)
        print('t4 done, report updated' if result else 't4 pending: 无 09-06 实际数据')
