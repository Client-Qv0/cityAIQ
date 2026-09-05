# AGENTS.md — 城市天气质量数据检测分析与可视化

## 项目概览

数据管线分两段：**数据爬取与清洗（已完成，`script/`）** → 数据分析与可视化（待开发）。
数据源为中国环境监测总站 <https://air.cnemc.cn:18007>，经清洗后存入 SQLite，下游一律从数据库读，不要直接请求接口。

技术栈：Python 3.13 + requests + sqlite3 标准库（无 ORM、无 requirements.txt）。

## 目录结构

```
prisma/weather.db        # SQLite 数据库（3 张表），数据全量约 4700 行
script/                  # Python 数据管线（爬蛇 + 分析；src/ 预留给前端 Next.js）
  db.py                  #   共享层：DB_PATH、三表 DDL（SCHEMA）、get_conn()
  req/                   # 数据爬取与清洗
    getdata.py           #     省份 + 地市级：爬取入库 & 读库
    getAQI.py            #     城市近 14 日 AQI：爬取入库 & 读库
  analysis/              # 数据分析与预测
    data_loader.py       #     pandas 读库（load_aqi_df / load_cities_df）
    analysis.py          #     统计与聚合（描述统计/排名/等级/趋势/省份汇总/相关矩阵）
    predict.py           #     最小二乘预测明日 AQI + 95% 区间（14 点线性外推）
    main.py              #     全量统计+全城预测
  tests/                 # pytest 单元测试（test_data_loader / test_analysis / test_predict）
  main.py                # 命令行入口：python script/main.py
src/                     # 预留：将来 Next.js 前端（app/components/lib/types/validations）
results/                 # 分析产物：CSV/PNG/JSON（前端数据接口）
plan.md                  # 分析+预测功能开发计划
city.json                # 接口返回格式样例，仅作字段参考（代码不读取）
city_day_AQI.json        # 同上
文档.docx                # 课程材料（已被 .gitignore 忽略）
```

## 常用命令

```bash
# Python 一律用绝对路径或 py，勿裸用 python 关键字
C:\Users\ASUS\AppData\Local\Programs\Python\Python313\python.exe script/req/getdata.py  # 刷新省份+城市，约 2 分钟
C:\...\python.exe script/req/getAQI.py                                                    # 全量刷新 AQI，15~20 分钟，可中断续跑
C:\...\python.exe script/main.py                                                          # 全量分析+预测，覆盖写出 results/
C:\...\python.exe -m pytest script/tests/ -v                                              # 运行全部测试（12 条）
# 依赖：requests（爬虫）；numpy/pandas/matplotlib（分析，见 requirements.txt）
```

预测说明：`predict_next_aqi` 对单城 AQI 序列做最小二乘线性外推，预测下一天并给 95% 预测区间（基于残差标准误与 t 分布）。仅反映短期趋势，无气象因子，误差较大；`results/predictions.json` 键为 CityCode（前端直接查）。

路径以 `__file__` 推导（`script/../prisma/weather.db`），从任意工作目录运行均可。

## 数据模型（prisma/weather.db）

**provinces**（34 行）：`Id` PK | `ProvinceCode` UNIQUE（如 110000）| `ProvinceJC`（BJ）| `ProvinceName`（北京）

**cities**（341 行）：`Id` PK | `CityCode` UNIQUE（如 130100）| `CityName` | `ProvinceId` → provinces.Id | `CityJC`

**city_day_aqi**（338 城 × 14 日 = 4732 行）：
`Id` PK（接口 Id）| `CityCode` | `DateTime` TEXT `'YYYY-MM-DD HH:MM:SS'`（东八区）| `TimePoint` INTEGER（毫秒时间戳）| `TimePointStr`（'21日'）| `Area` | `SO2_24h` `CO_24h` `NO2_24h` `O3_8h_24h` `PM10_24h` `PM2_5_24h` `AQI` 均为 REAL（缺失 NULL）| `PrimaryPollutant` | `Quality` | `Measure` | `Unheathful`（接口原始拼写，有意保留）
约束：`UNIQUE(CityCode, DateTime)`；每城仅存最近一次爬取的 14 条。

## 下游代码读取数据（可视化/分析必读）

方式一，直接 SQL：

```python
import sqlite3
conn = sqlite3.connect("prisma/weather.db")  # 项目根为工作目录
```

方式二，复用读库函数（返回 `list[dict]`，键名与接口字段一致）：

```python
import sys; sys.path.insert(0, "script")
from getdata import get_provice_info, get_city_info      # 省份列表 / 某省城市
from getAIQ import get_city_day_AQI                       # 单城市近14日，按时间升序
```

注意：`get_city_day_AQI` 入参是 CityCode（`140100`），不是城市名；先查 `cities` 表拿编码。

## 更新频率

- 行政区划：基本不变，每月或有新城市时跑 `getdata.py`
- AQI：每天跑一次 `getAIQ.py`；**接口只滚动提供最近 14 日，库内同样覆盖写入，历史数据不留存**，需长序列请自行定期导出

## 约定与红线（改 `script/` 必须遵守）

1. 数据源仅三个接口：`GET /CityData/GetProvince`、`GET /CityData/GetCitiesByPid?pid=`、`POST /HourChangesPublish/GetCityDayAqiHistoryByCondition?citycode=`
2. 任何批量爬取，请求之间必须 `time.sleep(random.uniform(1.5, 3))`，不得移除
3. 合法空响应（勿当异常）：台湾/香港/澳门（ProvinceId 32/33/34）城市返回 `[]`；县级市 130181、130682、419001 的 AQI 返回 `[]`（此时保留库中旧数据）
4. AQI 入库前按 `TimePoint` 截断为最近 14 条；覆盖语义 = 先 `DELETE` 该城市再插入
5. 字段清洗：浓度与 AQI 转 REAL，空值/'-' 存 NULL；不要改动 `Unheathful` 列名（映射接口原始键）
6. 勿删 `prisma/weather.db`；sync 函数幂等，重复运行安全
7. 不做任何 git 提交/推送操作，除非成员明确要求
