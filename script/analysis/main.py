"""全量分析入口：读库 → 统计/预测 → 导出 results/（CSV/PNG/JSON）

用法： python script/main.py（任意工作目录，路径按 __file__ 推导）
"""
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

from analysis.data_loader import load_aqi_df, load_cities_df
from analysis.analysis import (descriptive_summary, city_aqi_ranking,
                               quality_distribution, daily_trend, province_summary,
                               correlation_matrix, area_average, area_daily_aqi,
                               pollutant_analysis)
from analysis.predict import predict_next_aqi

RESULTS = Path(__file__).resolve().parents[2] / "results"

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False


def _check_freshness(df):
    newest = pd.to_datetime(df['DateTime'].max()).date()
    yesterday = datetime.now().date() - timedelta(days=1)
    if newest < yesterday:
        print(f"[警告] 库内最新数据为 {newest}，早于昨日；"
              f"建议先运行 script/req/getAQI.py 刷新后再分析")


def _save_csvs(df, predictions):
    RESULTS.mkdir(exist_ok=True)
    descriptive_summary(df).to_csv(RESULTS / 'summary_stats.csv')
    city_aqi_ranking(df).to_csv(RESULTS / 'city_ranking.csv', index=False)
    quality_distribution(df).to_csv(RESULTS / 'quality_distribution.csv', index=False)
    daily_trend(df).to_csv(RESULTS / 'daily_trend.csv', index=False)
    province_summary(df).to_csv(RESULTS / 'province_summary.csv', index=False)
    correlation_matrix(df).to_csv(RESULTS / 'correlation.csv')
    pd.DataFrame(predictions).T.to_csv(RESULTS / 'predictions.csv')


def _area_rows(df):
    """省/全国：7 项指标平均（城市等权）+ 明日 AQI 预测，逐行组装"""
    def _build(name):
        src = df if name is None else df[df['ProvinceName'] == name]
        rec = {'ProvinceName': '全国'} if name is None else {'ProvinceName': name}
        rec['city_count'] = int(src['CityName'].nunique())
        rec.update({k: float(v) for k, v in area_average(df, name).items()})
        daily = area_daily_aqi(df, name)
        if len(daily) >= 5:
            pred = predict_next_aqi(daily['AQI'])
            rec.update({'next_day': str(daily['DateTime'].max()),
                        'next_predicted': pred['predicted'],
                        'next_lower95': pred['lower95'],
                        'next_upper95': pred['upper95'],
                        'next_r2': pred['r2']})
        return rec

    prov_names = sorted(df['ProvinceName'].drop_duplicates().tolist())
    return [_build(None)] + [_build(n) for n in prov_names]


def _write_area_averages(df):
    rows = _area_rows(df)
    pd.DataFrame(rows).to_csv(RESULTS / 'area_averages.csv', index=False)
    provinces = {r['ProvinceName']: {k: v for k, v in r.items() if k != 'ProvinceName'}
                 for r in rows[1:]}
    with open(RESULTS / 'area_averages.json', 'w', encoding='utf-8') as f:
        json.dump({'national': rows[0], 'provinces': provinces},
                  f, ensure_ascii=False, indent=2)


def _write_pollutants(df):
    """主要污染物双粒度分析：day1 主控因子建议 + week7 频次参照"""
    out = pollutant_analysis(df)
    out.to_csv(RESULTS / 'pollutant_analysis.csv', index=False)
    records = []
    for r in out.to_dict('records'):
        for k in ('day1_gov', 'day1_personal', 'week7'):
            r[k] = json.loads(r[k])
        r['good'] = bool(r['good'])
        records.append({int(r['CityCode']): r})
    payload = {}
    for r in records:
        payload.update(r)
    with open(RESULTS / 'pollutant_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return len(payload)


def _plot(df):
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    # 全国每日 AQI（城市等权）趋势 + 明日预测
    nd = area_daily_aqi(df)
    xs = list(range(len(nd)))
    ax0 = axes[0, 0]
    ax0.plot(xs, nd['AQI'], marker='o', label='全国日均 AQI（城市等权）')
    labels = list(nd['DateTime'])
    if len(nd) >= 5:
        pred = predict_next_aqi(nd['AQI'])
        ax0.plot([xs[-1], len(nd)], [nd['AQI'].iloc[-1], pred['predicted']],
                 'r--', label='明日预测')
        ax0.errorbar([len(nd)], [pred['predicted']],
                     yerr=[[pred['predicted'] - pred['lower95']],
                           [pred['upper95'] - pred['predicted']]],
                     fmt='o', color='r', capsize=4)
        labels += ['明日(预测)']
    ax0.set_xticks(range(len(labels)), labels)
    ax0.tick_params(axis='x', rotation=45)
    ax0.set_title('全国每日 AQI 趋势与明日预测')
    ax0.legend(fontsize=8)
    # 城市排名 Top10
    top = city_aqi_ranking(df)
    axes[0, 1].barh(top['CityName'][::-1], top['AQI_mean'][::-1], color='orange')
    axes[0, 1].set_title('AQI 均值 Top10 城市')
    # 等级分布
    q = quality_distribution(df)
    axes[1, 0].pie(q['count'], labels=q['Quality'], autopct='%1.1f%%')
    axes[1, 0].set_title('空气质量等级分布')
    # 相关热力图
    corr = correlation_matrix(df)
    im = axes[1, 1].imshow(corr, cmap='RdYlGn_r', vmin=-1, vmax=1)
    axes[1, 1].set_xticks(range(len(corr)), corr.columns, rotation=45)
    axes[1, 1].set_yticks(range(len(corr)), corr.index)
    for i in range(len(corr)):
        for j in range(len(corr)):
            axes[1, 1].text(j, i, f'{corr.iloc[i, j]:.2f}', ha='center', va='center')
    axes[1, 1].set_title('污染物相关性矩阵')
    fig.colorbar(im, ax=axes[1, 1], fraction=0.046)
    fig.tight_layout()
    fig.savefig(RESULTS / 'overview.png', dpi=150)
    # 各省 AQI 均值
    fig2, ax2 = plt.subplots(figsize=(10, 6))
    ps = province_summary(df)
    ax2.bar(ps['ProvinceName'], ps['AQI_mean'], color='steelblue')
    ax2.set_title('各省 AQI 均值')
    ax2.tick_params(axis='x', rotation=90)
    fig2.tight_layout()
    fig2.savefig(RESULTS / 'province_overview.png', dpi=150)


def _predict_all(df, cities):
    """逐城市最小二乘预测，返回 {CityCode: {CityName, ProvinceName, ...}}"""
    last = df.groupby('CityCode')['DateTime'].max().to_dict()
    out = {}
    for _, row in cities.iterrows():
        code = int(row['CityCode'])
        ys = (df[df['CityCode'] == code]
              .sort_values('DateTime')['AQI'])
        if len(ys) < 5:
            continue
        r = predict_next_aqi(ys)
        out[code] = {
            'CityName': row['CityName'], 'ProvinceName': row['ProvinceName'],
            'last_day': str(last.get(code)), **r,
        }
    return out


def run():
    df = load_aqi_df()
    cities = load_cities_df()
    _check_freshness(df)
    predictions = _predict_all(df, cities)

    RESULTS.mkdir(exist_ok=True)
    _save_csvs(df, predictions)
    _write_area_averages(df)
    n_poll = _write_pollutants(df)
    _plot(df)

    with open(RESULTS / 'summary.json', 'w', encoding='utf-8') as f:
        json.dump({
            'stats': descriptive_summary(df).to_dict('index'),
            'city_ranking': city_aqi_ranking(df).to_dict('records'),
            'quality': quality_distribution(df).to_dict('records'),
            'daily_trend': daily_trend(df).to_dict('records'),
            'province': province_summary(df).to_dict('records'),
            'correlation': correlation_matrix(df).to_dict('index'),
            'data_range': [df['DateTime'].min(), df['DateTime'].max()],
        }, f, ensure_ascii=False, indent=2)
    with open(RESULTS / 'predictions.json', 'w', encoding='utf-8') as f:
        json.dump(predictions, f, ensure_ascii=False, indent=2)

    print(f'分析完成：{len(df)} 行，{df["CityName"].nunique()} 城市，'
          f'预测 {len(predictions)} 城，产物见 {RESULTS}/')


if __name__ == '__main__':
    run()
