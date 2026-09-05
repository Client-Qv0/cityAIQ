# 数据分析与预测功能实现计划

> **面向 AI 代理的工作者：** 按任务顺序内联执行此计划。步骤使用复选框（`- [ ]`）语法跟踪进度。全程不执行任何 git 操作（用户红线）。

**目标：** 让下一次运行分析脚本时，可以一次性产出全量描述统计、城市排名、质量等级分布、污染物相关性、每日趋势、省份汇总，以及对 338 个城市逐个给出"明日 AQI"的最小二乘预测值与 95% 预测区间，全部导出到 `results/` 供前端与报告消费。

**架构：** 每次运行都直接从 `prisma/weather.db` 读库（不缓存），保证 `getAIQ.py` 更新后重跑即得最新数据。三层：`src/data_loader.py`（pandas 读库）→ `src/analysis.py`（统计/聚合）与 `src/predict.py`（最小二乘）→ `src/main.py`（汇总导出 CSV/PNG/JSON，作为未来前端的数据接口）。前端暂不开发，本次只产出接口数据。

**技术栈：** Python 3.13 + numpy + pandas（需新装）+ matplotlib（仅用于出图）+ pytest（测试，仅开发期）。

**约定：**
- 不新建 requirements.txt 之外的依赖文件；不用 ORM；不改 `script/` 任何文件
- 所有输出统一在 `results/`（数据分析产物，前端直接读取）
- `DateTime` 统一视作天粒度数据（`YYYY-MM-DD`），场景内全为 00:00:00
- 中文字体统一 `['Microsoft YaHei', 'SimHei']`

---

## 文件结构

> 执行时按团队决策采用 `script/req`（爬取）+ `script/analysis`（分析）+ `script/tests` 布局，
> 任务中的 `src/*.py` 路径按 `script/analysis/*.py` 理解；入口为 `script/main.py`。

| 文件 | 职责 |
|---|---|
| `requirements.txt` | 声明运行依赖：numpy/pandas/matplotlib |
| `script/req/getdata.py`、`script/req/getAQI.py` | 既有爬取模块，仅迁移位置不改逻辑 |
| `script/analysis/data_loader.py` | 连接 weather.db，读出带省市名和日期的 DataFrame 与城市清单 |
| `script/analysis/analysis.py` | 描述统计、城市排名、等级分布、每日趋势、省份汇总、相关矩阵 |
| `script/analysis/predict.py` | 对 AQI 序列做最小二乘线性外推 + 95% 预测区间 |
| `script/analysis/main.py` | 编排：全量分析 + 全城预测 + 导出 results/ 下 CSV/PNG/JSON |
| `script/main.py` | 命令入口：仅调 `analysis.main.run()` |
| `script/tests/test_data_loader.py`、`test_analysis.py`、`test_predict.py` | 单元测试（pytest） |

---

## 任务 1：安装 pandas 依赖

**文件：**
- 创建：`requirements.txt`

- [ ] **步骤 1：安装 pandas**

运行：
```powershell
C:\Users\ASUS\AppData\Local\Programs\Python\Python313\python.exe -m pip install pandas
```
预期：Successfully installed pandas-*

- [ ] **步骤 2：创建 requirements.txt**

```text
numpy>=2.0
pandas>=2.2
matplotlib>=3.9
```

- [ ] **步骤 3：验证导入**

运行：
```powershell
C:\Users\ASUS\AppData\Local\Programs\Python\Python313\python.exe -c "import pandas, numpy, matplotlib; print('ok')"
```
预期：`ok`

---

## 任务 2：src/data_loader.py —— pandas 读库

**文件：**
- 创建：`src/data_loader.py`
- 创建：`src/__init__.py`（空）
- 创建：`tests/test_data_loader.py`

设计：`load_aqi_df()` 一次 JOIN 三张表，返回含 `CityName`/`ProvinceName` 的宽表；`load_cities_df()` 返回城市清单（未来前端下拉框用它）。

- [ ] **步骤 1：编写失败的测试**

```python
# tests/test_data_loader.py
from src.data_loader import load_aqi_df, load_cities_df

def test_load_aqi_df_from_real_db():
    df = load_aqi_df()
    assert len(df) > 4000
    assert set(['CityCode', 'CityName', 'ProvinceName', 'DateTime',
                'SO2_24h', 'CO_24h', 'NO2_24h', 'O3_8h_24h', 'PM10_24h',
                'PM2_5_24h', 'AQI', 'Quality', 'PrimaryPollutant']) <= set(df.columns)
    assert df['AQI'].isna().sum() == 0
    assert df['AQI'].dtype.kind == 'f'

def test_load_cities_df_fields():
    df = load_cities_df()
    assert {'CityCode', 'CityName', 'ProvinceName'} <= set(df.columns)
    assert len(df) >= 300
```

- [ ] **步骤 2：运行测试确认失败**

运行：
```powershell
C:\Users\ASUS\AppData\Local\Programs\Python\Python313\python.exe -m pytest tests/test_data_loader.py -v
```
预期：FAIL（ModuleNotFoundError: src.data_loader）

- [ ] **步骤 3：实现 data_loader.py**

```python
"""读取 prisma/weather.db 为 pandas DataFrame（分析模块唯一数据来源）

每次运行直接读库，不缓存；getAIQ.py 刷新后重跑即得最新数据。
"""
from pathlib import Path

import pandas as pd
import sqlite3

DB_PATH = Path(__file__).resolve().parents[1] / "prisma" / "weather.db"

_AQI_COLS = ['SO2_24h', 'CO_24h', 'NO2_24h', 'O3_8h_24h', 'PM10_24h', 'PM2_5_24h']


def _connect():
    return sqlite3.connect(DB_PATH)


def load_cities_df():
    """cities JOIN provinces，返回行政区划清单（前端城市下拉框数据源）"""
    with _connect() as conn:
        return pd.read_sql_query(
            "SELECT c.CityCode, c.CityName, p.ProvinceName "
            "FROM cities c JOIN provinces p ON c.ProvinceId = p.Id "
            "ORDER BY p.ProvinceCode, c.CityCode",
            conn,
        )


def load_aqi_df():
    """city_day_aqi JOIN cities JOIN provinces 的宽表

    列：CityCode CityName ProvinceName DateTime + 6 项浓度 + AQI + Quality +
        PrimaryPollutant；DateTime 已截断为 YYYY-MM-DD（天粒度）
    """
    with _connect() as conn:
        df = pd.read_sql_query(
            "SELECT a.CityCode, c.CityName, p.ProvinceName, a.DateTime, "
            + ", ".join(f"a.{col}" for col in _AQI_COLS)
            + ", a.AQI, a.Quality, a.PrimaryPollutant "
            "FROM city_day_aqi a "
            "JOIN cities c ON a.CityCode = c.CityCode "
            "JOIN provinces p ON c.ProvinceId = p.Id",
            conn,
        )
    df['DateTime'] = pd.to_datetime(df['DateTime']).dt.strftime('%Y-%m-%d')
    return df
```

- [ ] **步骤 4：运行测试确认通过**

运行：
```powershell
C:\Users\ASUS\AppData\Local\Programs\Python\Python313\python.exe -m pytest tests/test_data_loader.py -v
```
预期：PASS（2 条）

---

## 任务 3：src/analysis.py —— 统计与聚合

**文件：**
- 创建：`src/analysis.py`
- 创建：`tests/test_analysis.py`

- [ ] **步骤 1：编写失败的测试**

```python
# tests/test_analysis.py
import pandas as pd
from src.analysis import (descriptive_summary, city_aqi_ranking,
                          quality_distribution, daily_trend, province_summary,
                          correlation_matrix)


def _fake_df():
    rows = []
    for day in ['2026-08-21', '2026-08-22']:
        # base 使各浓度列有方差（否则相关矩阵为 NaN）
        for city, aqi, q, base in [('A市', 50, '优', 1.0),
                                   ('B市', 150, '轻度污染', 3.0),
                                   ('C市', 100, '良', 2.0)]:
            rows.append(dict(CityCode=1, CityName=city, ProvinceName='X省',
                             DateTime=day, SO2_24h=10.0 * base, CO_24h=0.5 * base,
                             NO2_24h=20.0 * base, O3_8h_24h=30.0 * base,
                             PM10_24h=60.0 * base, PM2_5_24h=35.0 * base,
                             AQI=float(aqi), Quality=q,
                             PrimaryPollutant='PM2.5'))
    return pd.DataFrame(rows)


def test_descriptive_summary_contains_aqi_stats():
    out = descriptive_summary(_fake_df())
    row = out.loc['AQI']
    assert out.loc['AQI', 'mean'] == 100.0
    assert out.shape[0] == 7

def test_city_aqi_ranking_desc():
    out = city_aqi_ranking(_fake_df())
    assert out.iloc[0]['CityName'] == 'B市'
    assert out.iloc[0]['AQI_mean'] == 150.0

def test_quality_distribution():
    out = quality_distribution(_fake_df())
    assert out.loc['优', 'count'] == 2
    assert out.loc['轻度污染', 'count'] == 2

def test_daily_trend_each_day_one_row():
    out = daily_trend(_fake_df())
    assert len(out) == 2
    assert out['AQI_mean'].iloc[0] == 100.0

def test_province_summary():
    out = province_summary(_fake_df())
    assert out.iloc[0]['ProvinceName'] == 'X省'
    assert out.iloc[0]['AQI_mean'] == 100.0

def test_correlation_symmetric_ones_diag():
    out = correlation_matrix(_fake_df())
    assert out.shape == (7, 7)
    assert pd.testing.assert_frame_equal(out, out.T) is None
    assert all(abs(out.iloc[i, i] - 1) < 1e-9 for i in range(7))
```

- [ ] **步骤 2：运行测试确认失败**

运行：
```powershell
C:\Users\ASUS\AppData\Local\Programs\Python\Python313\python.exe -m pytest tests/test_analysis.py -v
```
预期：FAIL（ModuleNotFoundError: src.analysis）

- [ ] **步骤 3：实现 analysis.py**

```python
"""统计分析模块：描述统计、排名、等级、趋势、省份聚合、相关性

输入统一为 data_loader.load_aqi_df() 的宽表；纯函数，无副作用。
"""
import pandas as pd

METRIC_COLS = ['SO2_24h', 'CO_24h', 'NO2_24h', 'O3_8h_24h', 'PM10_24h',
               'PM2_5_24h', 'AQI']
CN_KEYS = {'SO2_24h': 'SO2', 'CO_24h': 'CO', 'NO2_24h': 'NO2',
           'O3_8h_24h': 'O3_8h', 'PM10_24h': 'PM10', 'PM2_5_24h': 'PM2.5',
           'AQI': 'AQI'}


def descriptive_summary(df):
    """7 项指标的 count/mean/std/min/分位数/max；
    idx 使用 CN_KEYS 便于报告排版，中文列名友好化

    """
    st = df[METRIC_COLS].describe(percentiles=[.25, .5, .75]).T
    st = st.rename(index=CN_KEYS)
    return st.reindex(columns=['count', 'mean', 'std', 'min',
                               '25%', '50%', '75%', 'max'])


def city_aqi_ranking(df):
    """每城 14 日 AQI 均值排名（降序前 10），含等级占比与达标天数"""
    df_ = df.copy()
    df_['is_good'] = df_['Quality'].isin(['优', '良'])
    g = df_.groupby(['CityName', 'ProvinceName']).agg(
        AQI_mean=('AQI', 'mean'), AQI_max=('AQI', 'max'),
        AQI_min=('AQI', 'min'), good_days=('is_good', 'sum'))
    return g.sort_values('AQI_mean', ascending=False).head(10).reset_index()


def quality_distribution(df):
    """AQI 等级数量统计表：quality 列 = 优/良/轻度污染/中度污染/重度污染/严重污染"""
    out = df['Quality'].value_counts().rename('count').reset_index()
    return out.rename(columns={'index': 'Quality'})


def daily_trend(df, city_code=None):
    """全国（或单城市）每日 AQI 均值趋势"""
    if city_code is not None:
        df = df[df['CityCode'] == city_code]
    return (df.groupby('DateTime')['AQI'].mean()
            .rename('AQI_mean').reset_index())


def province_summary(df):
    """各省 AQI 均值（城市等权后按省平均）、最大值与监测城市数"""
    city_mean = (df.groupby(['ProvinceName', 'CityName'])['AQI']
                 .agg(['mean', 'max'])
                 .rename(columns={'mean': 'AQI_mean', 'max': 'AQI_max'}))
    out = (city_mean.reset_index()
           .groupby('ProvinceName', as_index=False)
           .agg(AQI_mean=('AQI_mean', 'mean'),
                AQI_max=('AQI_max', 'max'),
                city_count=('CityName', 'nunique')))
    return out.sort_values('AQI_mean', ascending=False).reset_index(drop=True)


def correlation_matrix(df):
    """7 项指标皮尔逊相关矩阵（索引/列用 CN_KEYS）"""
    corr = df[METRIC_COLS].corr(method='pearson')
    corr.index = [CN_KEYS[c] for c in corr.index]
    corr.columns = [CN_KEYS[c] for c in corr.columns]
    return corr
```

- [ ] **步骤 4：运行测试确认通过**

运行：
```powershell
C:\Users\ASUS\AppData\Local\Programs\Python\Python313\python.exe -m pytest tests/test_analysis.py -v
```
预期：PASS（6 条）。若 `daily_trend` 相关断言失败，以期望值（每行 AQI_mean）为准修正测试。

---

## 任务 4：src/predict.py —— 最小二乘单步预测

**文件：**
- 创建：`src/predict.py`
- 创建：`tests/test_predict.py`

设计：`y = a + b·t`（t = 0..n-1 为日期序号），普通最小二乘；预测 t = n 的 AQI；
95% 预测区间基于残差标准误差 s 与 t 分布分位数（df=5..12 查表，其余用 1.96）。

- [ ] **步骤 1：编写失败的测试**

```python
# tests/test_predict.py
import math
import pandas as pd

from src.predict import predict_next_aqi

def test_perfect_linear_recovers_exact():
    # y = 3t + 10，t=0..13；下一值应为 52
    s = pd.Series([3 * i + 10 for i in range(14)])  # 10,13,...,49
    r = predict_next_aqi(s)
    assert math.isclose(r['predicted'], 52.0, abs_tol=1e-6)
    assert math.isclose(r['slope'], 3.0, abs_tol=1e-6)
    assert math.isclose(r['intercept'], 10.0, abs_tol=1e-6)

def test_interval_covers_predicted():
    r = predict_next_aqi(pd.Series([40, 55, 48, 70, 62, 75, 68, 90, 80, 95, 88, 105, 98, 112]))
    assert r['lower95'] < r['predicted'] < r['upper95']

def test_insufficient_data_raises():
    try:
        predict_next_aqi(pd.Series([50.0, 52.0, 53.0, 54.0]))
        assert False, '应抛出 ValueError'
    except ValueError:
        pass

def test_series_with_nan_raises():
    try:
        predict_next_aqi(pd.Series([50.0, None, 53.0] * 5))
        assert False, '应抛出 ValueError'
    except ValueError:
        pass
```

- [ ] **步骤 2：运行测试确认失败**

运行：
```powershell
C:\Users\ASUS\AppData\Local\Programs\Python\Python313\python.exe -m pytest tests/test_predict.py -v
```
预期：FAIL（ModuleNotFoundError: src.predict）

- [ ] **步骤 3：实现 predict.py**

```python
"""AQI 最小二乘预测：线性趋势外推 + 95% 预测区间

模型：AQI(t) = intercept + slope * t，t = 0..n-1；预测 t = n。
区间公式：pred ± t(0.975, n-2) * s * sqrt(1 + 1/n + (t_n-t_bar)^2/Sxx)
 """
import math

import numpy as np
import pandas as pd

# t 分布双侧 0.975 分位数表（df = n-2 ∈ 1..12），其余 df 用 1.96 近似
_T_VALUE = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571,
            6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
            11: 2.201, 12: 2.179}


def predict_next_aqi(aqi_series, min_points=5):
    """对一维 AQI 序列做最小二乘线性外推，预测下一天值

    :param aqi_series: pd.Series / list，长度 >= min_points，不允许空值
    :return: dict:
        predicted 下一天 AQI 预测值
        lower95/upper95 95% 预测区间
        slope/intercept 拟合系数
        r2 决定系数
        stderr 残差标准误差
    """
    y = pd.Series(aqi_series).astype(float).reset_index(drop=True)
    if len(y) < min_points:
        raise ValueError(f'数据点不足（{len(y)} < {min_points}），无法拟合')
    if y.isna().any() or np.isinf(y).any():
        raise ValueError('AQI 序列包含空值或无穷值')

    n = len(y)
    t = np.arange(n, dtype=float)
    t_bar = t.mean()
    y_bar = y.mean()
    sxx = ((t - t_bar) ** 2).sum()
    sxy = ((t - t_bar) * (y - y_bar)).sum()
    slope = sxy / sxx
    intercept = y_bar - slope * t_bar

    y_fit = intercept + slope * t
    sse = ((y - y_fit) ** 2).sum()
    r2 = 1 - sse / ((y - y_bar) ** 2).sum() if ((y - y_bar) ** 2).sum() > 0 else 1.0
    stderr = math.sqrt(sse / (n - 2)) if n > 2 else float('nan')

    df = n - 2
    tval = _T_VALUE.get(df, 1.96)
    t_next = float(n)  # 序号 n 即明天
    se_pred = stderr * math.sqrt(1 + 1 / n + (t_next - t_bar) ** 2 / sxx)
    predicted = intercept + slope * t_next

    return {
        'predicted': float(predicted),
        'lower95': float(predicted - tval * se_pred),
        'upper95': float(predicted + tval * se_pred),
        'slope': float(slope),
        'intercept': float(intercept),
        'r2': float(r2),
        'stderr': float(stderr),
        'n_points': int(n),
    }
```

- [ ] **步骤 4：运行测试确认通过**

运行：
```powershell
C:\Users\ASUS\AppData\Local\Programs\Python\Python313\python.exe -m pytest tests/test_predict.py -v
```
预期：PASS（4 条）

---

## 任务 5：src/main.py + 根 main.py —— 全量分析导出

**文件：**
- 创建：`src/main.py`
- 创建：`src/__init__.py`（若未建）
- 修改：`main.py`（根目录占位）

设计：
- 每次全量重算（读库 → 分析 → 覆盖写 results/）
- 数据新鲜度检查：若库内 MAX(DateTime) 早于昨天则打印提醒
- CSV：总体统计 / 城市排名 / 等级分布 / 每日趋势 / 省份汇总 / 相关矩阵 / 全部城市预测表
- PNG：中文字体 Microsoft YaHei，5 张图
- JSON：`summary.json`（前端首页数据）+ `predictions.json`（前端按城取预测），键名约定为前端接口

- [ ] **步骤 1：实现 src/main.py**

```python
"""全量分析入口：读库 → 统计/预测 → 导出 results/（CSV/PNG/JSON）

用法： python main.py（任意工作目录，路径按 __file__ 推导）
"""
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.data_loader import load_aqi_df, load_cities_df
from src.analysis import (descriptive_summary, city_aqi_ranking,
                          quality_distribution, daily_trend, province_summary,
                          correlation_matrix, METRIC_COLS)
from src.predict import predict_next_aqi

RESULTS = Path(__file__).resolve().parents[1] / "results"

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False


def _check_freshness(df):
    newest = pd.to_datetime(df['DateTime'].max())
    yesterday = pd.Timestamp(datetime.now().date() - timedelta(days=1))
    if newest < yesterday:
        print(f"[警告] 库内最新数据为 {newest.date()}，早于昨日；"
              f"建议先运行 script/getAIQ.py 刷新后再分析")


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
    out, last = {}, df.groupby('CityCode')['DateTime'].max()
    for _, row in cities.iterrows():
        code = int(row['CityCode'])
        ys = df[df['CityCode'] == code][['AQI']].sort_values('DateTime')['AQI']
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
```

- [ ] **步骤 2：改写根 main.py（占位文件）**

```python
"""城市天气质量数据分析与预测入口"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.main import run

if __name__ == '__main__':
    run()
```

- [ ] **步骤 3：运行冒烟验证**

运行：
```powershell
C:\Users\ASUS\AppData\Local\Programs\Python\Python313\python.exe main.py
```
预期：打印"分析完成：4732 行，338 城市，预测 338 城"；`results/` 下出现
`summary_stats.csv`、`city_ranking.csv`、`quality_distribution.csv`、
`daily_trend.csv`、`province_summary.csv`、`correlation.csv`、`predictions.csv`、
`overview.png`、`province_overview.png`、`summary.json`、`predictions.json`

---

## 任务 6：更新 AGENTS.md 说明新模块

**文件：**
- 修改：`AGENTS.md`

- [ ] **步骤 1：更新目录结构与常用命令**

在 AGENTS.md 中补充：

```markdown
src/                     # 数据分析与预测模块
  data_loader.py         #   pandas 读库（load_aqi_df / load_cities_df）
  analysis.py            #   统计与聚合（排名/等级/趋势/相关）
  predict.py             #   最小二乘预测明日 AQI + 95% 区间
  main.py                #   全量统计+全城预测，导出 results/
results/                 # 分析产物：CSV/PNG/JSON（前端数据接口）
```

并追加命令：
```bash
C:\Users\ASUS\AppData\Local\Programs\Python\Python313\python.exe main.py   # 全量分析+预测，导出 results/
C:\...\python.exe -m pytest tests/ -v                                       # 运行全部测试
```

- [ ] **步骤 2：最终回归验证**

运行：
```powershell
C:\Users\ASUS\AppData\Local\Programs\Python\Python313\python.exe -m pytest tests/ -v
```
预期：PASS 共 12 条

---

# 阶段二：前端界面实现计划

> 数据源：所有数据经 Next.js API Route + better-sqlite3 直读 `prisma/weather.db`（与 Python 分析同库同口径）；
> 路由：`/`（全国）、`/[ProvinceJC]`（省）、`/[ProvinceJC]/[CityCode]`（城市，CityCode 为国标 6 位唯一编码，无歧义）。
> 全程不执行任何 git 操作（用户红线）。

**目标：** 三页可视化前端：全国概览（中国地图 + 区域均值/预测）、省份页（省内城市列表 + 省均值/预测）、城市页（14 日时序 + 明日预测点），外观对齐国标 HJ 633 六色图例。

**架构：** 根目录为 Next.js 项目（`src/app` App Router，对齐 mini-mall 范式）；Python 全部在 `script/`（已完成，不动）。前端只读库：`better-sqlite3` 直连 weather.db，SQL 聚合口径与 Python 一致（城市等权：先城市日均再城市间平均），预测算法复刻 `script/analysis/predict.py` 的最小二乘公式（`src/lib/predict.ts`，两端口径一致）。

**技术栈：**

| 技术 | 版本 | 用途 |
|---|---|---|
| Next.js | 16.x | App Router（路由 + Route Handlers） |
| React | 19.x | UI |
| TypeScript | ^5 | strict mode，禁止 any |
| TailwindCSS | ^4 | 样式 |
| Zod | ^4 | 请求参数校验 |
| ECharts + echarts-for-react | 5.x / 3.0.x | 地图、折线、饼图 |
| better-sqlite3 | 12.x | 直读 SQLite |
| vitest | ^2 | 单测 |

**约定：**
- API 返回格式：`{ data, error, message }`；公开只读，无鉴权
- 等权口径与 Python 严格一致：区域均值 = 城市 14 日均值 → 城市间平均
- AQI 等级色板（HJ 633）：`src/lib/aqiColors.ts`
- 中国地图 GeoJSON：`public/geo/china.json`（阿里 DataV `100000_full.json`，本地存档，不依赖线上）
- 手写组件与样式，不引入 UI/状态库

---

## 目录结构

```
src/
  app/
    page.tsx                          # / 全国概览
    [ProvinceJC]/page.tsx             # /[ProvinceJC] 省页
    [ProvinceJC]/[CityCode]/page.tsx  # /[ProvinceJC]/[CityCode] 城市页
    api/
      national/route.ts               # GET 全国：均值+预测+每日序列+等级+省排名
      province/[provinceJC]/route.ts  # GET 某省：省均值+预测+省内城市+每日序列
      city/[cityCode]/route.ts        # GET 某城：14 日序列+预测+基本信息；支持 ?key= 切换指标
    layout.tsx  globals.css
  components/
    chart/EChart.tsx                  # 'use client' 通用 ECharts 包装
    chart/ChinaMap.tsx                # 中国地图着色（省均值色阶）+ 点击跳转
    chart/TrendChart.tsx              # 折线（14 日 + 明日预测点虚线/区间）
    chart/QualityPie.tsx              # 等级分布饼图
    ui/StatCard.tsx  ui/Table.tsx  ui/Badge.tsx  ui/Breadcrumb.tsx
  lib/
    db.ts                             # better-sqlite3 单例（prisma/weather.db 只读）
    queries.ts                        # 全部 SQL（national/province/city）
    predict.ts                        # 最小二乘预测（复刻 Python 版）
    aqiColors.ts                      # HJ633 色板、qualityOf()/colorOf()
    jc.ts                             # ProvinceJC<->ProvinceId、CityCode 解析与归属校验
    utils.ts                          # cn()、数字格式化
  types/index.ts
  validations/index.ts                # zod schema（cityCode/provinceJC）
public/geo/china.json                 # 中国省界 GeoJSON（DataV）
tests/                                # vitest：predict / jc / queries
```

Node 依赖：next/react/ts/tailwind4/zod/echarts/echarts-for-react/better-sqlite3/vitest。
`next.config.ts`：`transpilePackages: ['echarts', 'zrender']`。

---

## API 契约

**GET /api/national**
```json
{ "data": { "stats": {"AQI": {"mean": 51.7, "max": 179}},
            "avg": {"AQI": 51.7, "PM2.5": 13.7, "next_predicted": 59.1,
                    "next_lower95": 47.4, "next_upper95": 70.7, "next_r2": 0.46},
            "daily": [{"date": "2026-08-21", "AQI": 62.1}],
            "quality": [{"Quality": "优", "count": 2818}],
            "province_rank": [{"ProvinceName": "河南", "AQI_mean": 78.2}] } }
```

**GET /api/province/[provinceJC]**
```json
{ "data": { "province": {"ProvinceName": "浙江", "ProvinceJC": "ZJ", "city_count": 11},
            "avg": {"AQI": 58.2, "next_predicted": 61.1, "…": 0},
            "cities": [{"CityCode": 330100, "CityName": "杭州市", "AQI_mean": 58,
                        "next_predicted": 62, "good_days": 12}],
            "daily": [{"date": "2026-08-21", "AQI": 55.2}] } }
```

**GET /api/city/[cityCode]（`?key=` 切换指标，缺省 AQI；key ∈ AQI/SO2/CO/NO2/O3_8h/PM10/PM2.5，白名单校验防注入）**
```json
{ "data": { "city": {"CityCode": 330100, "CityName": "杭州市", "ProvinceName": "浙江", "CityJC": "HZS"},
            "key": "AQI", "unit": "",
            "daily": [{"date": "2026-08-21", "value": 56, "Quality": "优", "SO2_24h": 6.1, "CO_24h": 0.5, "NO2_24h": 21.3,
                       "O3_8h_24h": 74.2, "PM10_24h": 31.2, "PM2_5_24h": 15.4}],
            "predict": {"predicted": 51.4, "lower95": 2.1, "upper95": 100.6,
                        "r2": 0.05, "slope": -1.02, "n_points": 14},
            "summary": {"AQI_mean": 59, "good_days": 11, "primary_pollutant": "O3_8h"} } }
```

**城市页指标切换语义**：`/ZJ/330100` → AQI 14+1 折线；`/ZJ/330100?key=PM2.5` → PM2.5 14+1 折线（该指标同样做最小二乘预测）；`daily[].value` 与 `predict` 均针对所选 key。UI 提供 7 个指标的切换器（AQI/SO2/CO/NO2/O3_8h/PM10/PM2.5），URL query 同步。

---

## 任务 1：前端工程骨架（手写初始化，避免 create-next-app 非空目录冲突）

**文件：**
- 创建：`package.json`、`tsconfig.json`、`next.config.ts`、`postcss.config.mjs`、`src/app/globals.css`、`src/app/layout.tsx`

- [ ] **步骤 1：package.json**

```json
{
  "name": "city-aqi-web",
  "version": "0.1.0",
  "private": true,
  "scripts": { "dev": "next dev", "build": "next build", "start": "next start",
               "lint": "next lint", "test": "vitest run" },
  "dependencies": {
    "better-sqlite3": "^12.0.0", "echarts": "^5.6.0", "echarts-for-react": "^3.0.6",
    "next": "^16.2.11", "react": "^19.2.4", "react-dom": "^19.2.4", "zod": "^4.4.3"
  },
  "devDependencies": {
    "@tailwindcss/postcss": "^4", "@types/better-sqlite3": "^7.6.0",
    "@types/node": "^20", "@types/react": "^19", "@types/react-dom": "^19",
    "tailwindcss": "^4", "typescript": "^5", "vitest": "^2.1.0"
  }
}
```

- [ ] **步骤 2：npm install**

运行：`npm install`
预期：无 peer 冲突；`node -e "console.log(Object.keys(require('better-sqlite3')))"` 打印数组（native 二进制 OK）。

- [ ] **步骤 3：next.config.ts**

```ts
import type { NextConfig } from "next"
const nextConfig: NextConfig = { transpilePackages: ["echarts", "zrender"] }
export default nextConfig
```

- [ ] **步骤 4：tsconfig.json（exclude script/results，paths @/*）**

```json
{ "compilerOptions": { "target": "ES2022", "lib": ["dom", "dom.iterable", "esnext"],
  "strict": true, "noEmit": true, "esModuleInterop": true, "module": "esnext",
  "moduleResolution": "bundler", "resolveJsonModule": true, "isolatedModules": true,
  "jsx": "preserve", "incremental": true, "plugins": [{ "name": "next" }],
  "paths": { "@/*": ["./src/*"] } },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules", "script", "results"] }
```

- [ ] **步骤 5：globals.css + layout.tsx**

`globals.css`：`@import "tailwindcss";`
`layout.tsx`：lang=zh-CN，顶部导航"城市空气质量实时可视化"，面包屑容器。

- [ ] **步骤 6：dev server 起跳**

运行：`npm run dev` → http://localhost:3000 显示占位布局。

---

## 任务 2：数据层 lib（db/queries/predict/jc/aqiColors/types/validations）

**文件：**
- 创建：`src/lib/db.ts`、`queries.ts`、`predict.ts`、`aqiColors.ts`、`jc.ts`、`utils.ts`、`src/types/index.ts`、`src/validations/index.ts`
- 测试：`tests/predict.test.ts`、`tests/jc.test.ts`、`tests/queries.test.ts`

- [ ] **步骤 1：db.ts（单例只读，约定从项目根运行）**

```ts
import Database from "better-sqlite3"
export const db = new Database(process.cwd() + "/prisma/weather.db", { readonly: true })
```

- [ ] **步骤 2：queries.ts 关键 SQL（城市等权与 Python 同口径）**

```ts
// 区域等权均值 = 每城 AQI 日均 → 城市间平均
const AVG_EQUAL_WEIGHT = `
  SELECT AVG(city_avg) FROM (SELECT CityCode, AVG(AQI) AS city_avg FROM city_day_aqi GROUP BY CityCode)`
export function qNational() { /* stats: SELECT AVG()/MAX() 7 指标；avg: 等权 7 指标 + predict(daily 序列);
    daily: SELECT DateTime, AVG(cityAvg) 按日等权; quality: 等级计数; province_rank: JOIN provinces 等权均值 */
}
export function qProvince(provinceId: number) { /* 省信息、等权均值+预测、各城均值/good_days、省每日序列 */ }
export function qCity(cityCode: number) { /* 14 日全字段 + 城市基础信息 */ }
```

- [ ] **步骤 3：predict.ts（与 Python 完全同公式）**

```ts
const T_VALUE: Record<number, number> = {
  5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179,
}
export function predictNext(ys: number[]): {
  predicted: number; lower95: number; upper95: number
  slope: number; intercept: number; r2: number; n_points: number
}
// 最小二乘 y = a + b·t，t = 0..n-1，预测 t = n；区间 pred ± t(0.975, n-2)·s·sqrt(1 + 1/n + (tn−t̄)²/Sxx)
```

测试用例（与 Python 版同值）：`[10,13,...,49]`（n=14）→ predicted=52、r2≈1。

- [ ] **步骤 4：jc.ts（URL 段 → 库标识 + 归属校验）**

`parseProvinceJC(jc)` → `{ provinceId, name } | null`（`SELECT ... WHERE ProvinceJC=?`）；
`parseCityRoute(provinceJC, cityCode)` → `{ cityCode, name } | null`（CityCode 唯一；校验 `ProvinceId` 归属 JC，错配返回 null 触发 404）。

- [ ] **步骤 5：aqiColors.ts（HJ 633 六色 + 判定）**

```ts
export const QualityLevels = ["优", "良", "轻度污染", "中度污染", "重度污染", "严重污染"]
export const LevelColors = ["#00e400", "#f6ec20", "#ff7e00", "#ff0000", "#8f083a", "#7e0023"]
export function qualityOf(aqi: number): string
export function colorOf(aqi: number): string
```

- [ ] **步骤 6：types + validations**

```ts
// types/index.ts
export interface CityDailyRow { date: string; value: number; Quality?: string }
export interface PredictResult { predicted: number; lower95: number; upper95: number;
  r2: number; slope: number; n_points: number }
// validations/index.ts
const cityCodeSchema = z.coerce.number().int().min(100000).max(999999)
const provinceJCSchema = z.string().min(2).max(4).regex(/^[A-Z]+$/)   // BJ/NMG 等
// 指标白名单：key 一律经映射表转列名，禁止直接拼 SQL（防注入）
export const METRIC_KEYS = ["AQI", "SO2", "CO", "NO2", "O3_8h", "PM10", "PM2.5"] as const
export const METRIC_COLUMN: Record<string, string> = {
  AQI: "AQI", SO2: "SO2_24h", CO: "CO_24h", NO2: "NO2_24h",
  O3_8h: "O3_8h_24h", PM10: "PM10_24h", PM2_5: "PM2_5_24h",
}
export const METRIC_UNIT: Record<string, string> = {
  AQI: "", SO2: "μg/m³", CO: "mg/m³", NO2: "μg/m³", O3_8h: "μg/m³", PM10: "μg/m³", PM2_5: "μg/m³",
}
const metricKeySchema = z.enum(METRIC_KEYS).default("AQI")
```

- [ ] **步骤 7：vitest 全绿**

运行：`npm test` → predict（4 用例）/ jc（2 用例）/ queries（真实库集成，3 用例）PASS。

---

## 任务 3：API Route Handlers

**文件：**
- 创建：`src/app/api/national/route.ts`、`src/app/api/province/[provinceJC]/route.ts`、`src/app/api/city/[cityCode]/route.ts`

- [ ] **步骤 1：实现三个 GET（zod 校验 + {data,error,message} + 404 处理）**

```ts
// api/city/[cityCode]/route.ts 结构
const keySchema = z.enum(["AQI", "SO2", "CO", "NO2", "O3_8h", "PM10", "PM2.5"]).default("AQI")
export async function GET(req: Request, ctx: { params: Promise<{ cityCode: string }> }) {
  const { cityCode } = await ctx.params
  const key = keySchema.parse(new URL(req.url).searchParams.get("key"))
  try {
    const parsed = cityCodeSchema.safeParse(cityCode)
    if (!parsed.success) return Response.json(
      { data: null, error: "invalid_cityCode", message: "城市编码非法" }, { status: 400 })
    return Response.json({ data: await loadCityData(parsed.data, key), error: null, message: null })
  } catch {
    return Response.json(
      { data: null, error: "not_found", message: "未找到该城市数据" }, { status: 404 })
  }
}
```

`loadCityData(cityCode, key)`：daily 取所选 key 的序列（`value` 字段；key=AQI 时附带 Quality），`predict` = `predictNext(values)`（6 浓度同样拟合+区间）。

- [ ] **步骤 2：curl 验证**

```bash
curl http://localhost:3000/api/national
curl http://localhost:3000/api/province/ZJ
curl http://localhost:3000/api/city/330100        # 杭州
curl http://localhost:3000/api/city/999999        # 预期 404
```

---

## 任务 4：图表与 UI 组件（ECharts 客户端封装）

**文件：**
- 创建：`src/components/chart/EChart.tsx`、`ChinaMap.tsx`、`TrendChart.tsx`、`QualityPie.tsx`、`src/components/ui/StatCard.tsx`、`ui/Table.tsx`、`ui/Badge.tsx`、`ui/Breadcrumb.tsx`

- [ ] **步骤 1：EChart.tsx（'use client'）**

```tsx
"use client"
import ReactECharts from "echarts-for-react"
export function EChart({ option, height = 360 }: { option: object; height?: number }) {
  return <ReactECharts option={option} notMerge style={{ height, width: "100%" }} />
}
```

- [ ] **步骤 2：TrendChart（14 日时序 + 预测点）**

series[0] 近 14 日实线（markLine at 0? 不需）；series[1] `[末日期, 预测日]` 虚线接预测值；区间用 `stack` 双 series 模拟误差带（lower~upper 透明填充）；tooltip 显示颜色等级。

- [ ] **步骤 3：ChinaMap + GeoJSON**

先下载（任务 6 若未完成也在）：`public/geo/china.json`；组件内 `echarts.registerMap("china", data)`（fetch 加载），series `{ type: "map", map: "china" }`，visualMap `min 0 max 150`，`#00e400→#7e0023` 六段（pieces 模式映射国标区间）；click 事件 `router.push("/" + provinceJC)`（provinceJC 从后端 rank 列表关联）。

- [ ] **步骤 4：StatCard/Badge/Table/Breadcrumb**

StatCard：指标名 + 值 + 单位 + 等级色；Badge：等级丸；Table：城市/省份排名表；Breadcrumb：首页 / 浙江 / 杭州。

---

## 任务 5：三个页面

**文件：**
- 创建：`src/app/page.tsx`、`src/app/[ProvinceJC]/page.tsx`、`src/app/[ProvinceJC]/[CityCode]/page.tsx`

- [ ] **步骤 1：首页 `/`**

KPI 行（全国 AQI 均值、明日预测、预测区间、数据日期）→ 左 ChinaMap（省均值着色，点击滚入省页）→ 右 QualityPie + TrendChart（每日等权序列含预测点）→ 底部省排名 Table。

- [ ] **步骤 2：省页 `/[ProvinceJC]`**

Breadcrumb（首页 / 浙江）→ KPI（省均值/明日预测/城市数）→ 城市表（城市名/AQI 均值/明日预测/良好天数，行点击 → `/[ProvinceJC]/[CityCode]`）→ 省 TrendChart → 省 vs 全国 7 指标对比条。

- [ ] **步骤 3：城市页 `/[ProvinceJC]/[CityCode]`**

Breadcrumb（首页 / 浙江 / 杭州）→ **指标切换器**（AQI/SO2/CO/NO2/O3_8h/PM10/PM2.5 七个 tab，默认 AQI，`?key=` 与 URL 同步；key=AQI 时有等级底色）→ 当前值大卡（等级色 + 首要污染物 + 明日预测与区间，区间为所选指标）→ TrendChart（所选指标 14 日 + 预测虚线/误差带，单位随 key 变化）→ 信息卡（CityCode/省属/JC）。

- [ ] **步骤 4：404 处理**

三页调用 `parseProvinceJC/parseCityRoute` 或 fetch API 失败均 `notFound()`；`not-found.tsx` 提供返回首页链接。

---

## 任务 6：GeoJSON + lint/build/验收

**文件：**
- 创建：`public/geo/china.json`

- [ ] **步骤 1：下载省界 GeoJSON**

```bash
mkdir -p public/geo && curl -o public/geo/china.json https://geo.datav.aliyuncs.com/areas_v3/bound/100000_full.json
```
备选：`https://raw.githubusercontent.com/echarts-maps/echarts-china-cities-js/master/echarts-china-map.json`
确认文件含 `"features"` 且 size ~2MB 内。

- [ ] **步骤 2：质量门**

运行：`npm run build` + `npx tsc --noEmit` + `npm test`
预期：0 error；13 用例 PASS（simplified）。

- [ ] **步骤 3：验收清单**

- [ ] `/` 地图着色正常，点击省份能跳转
- [ ] `/ZJ` 城市列表可跳转城市页
- [ ] `/ZJ/330100` 时序 + 预测点展示；`/BJ/330100`（省城错配）404
- [ ] `/ZJ/330100?key=PM2.5` 切换为 PM2.5 折线 + 该指标明日预测；key 非法值（如 `?key=foo` → 400 或回落 AQI）
- [ ] 浓度指标同样带 95% 区间（14+1 天格式统一）
- [ ] API 四组 curl（national/省份/城市/非法）全部符合契约
- [ ] AQI 色板与国标一致（优绿、良黄、轻橙、中红、重紫、严重褐）

---

> **说明：** 阶段一`results/*.json` 保留作报告备料；前端一律经 API 直读数据库（实时更新靠 `script/req/getAQI.py` 刷新 + 页面刷新）。


