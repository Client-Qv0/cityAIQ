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
                               correlation_matrix)
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


def _plot(df):
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    # 全国每日趋势
    tr = daily_trend(df)
    axes[0, 0].plot(tr['DateTime'], tr['AQI_mean'], marker='o')
    axes[0, 0].set_title('全国每日 AQI 均值')
    axes[0, 0].tick_params(axis='x', rotation=45)
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
