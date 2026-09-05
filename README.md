# 城市天气质量数据检测分析与可视化

课程项目：面向中国环境监测总站（[air.cnemc.cn:18007](https://air.cnemc.cn:18007)）公开数据的城市空气质量分析可视化系统。

系统包含完整数据链路：**数据爬取 → 数据清洗入库 → 统计分析/预测 → Web 可视化**。覆盖全国 34 个省级行政区、341 个地级市，入库近 14 日滚动监测数据（4732 条），支持全国/省份/城市三级查看，并对 AQI 提供次日最小二乘预测。

---

## 功能特性

- **数据采集**：从中国环境监测总站接口抓取省份、城市与逐日 AQI 数据，清洗后写入 SQLite（幂等，可重复执行）
- **统计分析**：描述统计、城市排名、质量等级分布、污染因子皮尔逊相关、每日趋势、省份/全国均值（城市等权口径）
- **短期预测**：基于近 14 日序列的最小二乘线性外推，给出明日 AQI 预估值与 95% 预测区间（城市/省份/全国三个粒度）
- **可视化前端**：
  - 全国页：中国地图省均值着色、等级分布饼图、每日趋势（含明日预测点与区间）、省排名
  - 省份页：省内城市明细表（含预测值）、省每日趋势、7 项指标省 vs 全国对比
  - 城市页：14+1 天折线（14 日历史 + 明日预测），支持 AQI / SO₂ / CO / NO₂ / O₃-8h / PM10 / PM2.5 七个指标切换（`?key=`）
- **测试**：Python pytest 17 条 + 前端 vitest 12 条

## 技术栈

| 层 | 技术 |
|---|---|
| 爬取 | Python 3.13 + requests + sqlite3（标准库） |
| 分析 | numpy + pandas + matplotlib |
| 预测 | 最小二乘线性外推（Python/TypeScript 双端同公式实现） |
| 前端 | Next.js 16（App Router）+ React 19 + TypeScript strict + TailwindCSS 4 + Zod 4 |
| 图表 | ECharts 5 + echarts-for-react（中国地图 GeoJSON 本地化） |
| 数据访问 | better-sqlite3 直读 SQLite（API Route，只读） |

## 系统架构

```
┌────────────┐   ┌──────────────────┐   ┌────────────────────────┐
│ air.cnemc.cn │ → │ script/req/ 爬取  │ → │ prisma/weather.db      │
│ (三个接口)  │   │ + 清洗入库         │   │ (SQLite, 3 张表)       │
└────────────┘   └──────────────────┘   └──────────┬─────────────┘
                                                   │ better-sqlite3 只读
                                    ┌──────────────┴──────────────┐
                                    │ script/analysis/ 分析与预测  │
                                    │  → results/(CSV/PNG/JSON)   │
                                    └──────────────┬──────────────┘
                                    ┌──────────────┴──────────────┐
                                    │ src/ Next.js 前端            │
                                    │  /  /[ProvinceJC]/[CityCode] │
                                    └─────────────────────────────┘
```

**口径一致性**：分析模块与前端采用同一"城市等权"口径（每城先取 14 日均值、再对城市平均），预测公式两端复刻（Python `predict_next_aqi` ↔ TS `predictNext`，共享同一测试向量）。前端每次请求实时读库，数据刷新无需改代码。

## 目录结构

```
├── prisma/weather.db          # SQLite 数据库（爬取产物，勿删）
├── script/                    # Python 数据管线
│   ├── db.py                  #   连接与建表（共享层）
│   ├── req/                   #   数据爬取与清洗
│   │   ├── getdata.py         #     省份/地市级
│   │   └── getAQI.py          #     城市近 14 日 AQI
│   ├── analysis/              #   数据分析与预测
│   │   ├── data_loader.py     #     pandas 读库
│   │   ├── analysis.py        #     统计/聚合
│   │   ├── predict.py         #     最小二乘预测
│   │   └── main.py            #     全量分析入口
│   ├── tests/                 #   pytest（17 条）
│   └── main.py                #   命令行入口
├── src/                       # Next.js 前端
│   ├── app/                   #   页面（page.tsx ×3）+ api/ Route Handlers
│   ├── components/            #   chart/(EChart/ChinaMap/TrendChart/QualityPie) 等
│   ├── lib/                   #   db/queries/predict/jc/aqiColors/provinceMap/utils
│   ├── types/  validations/   #   共享类型与 zod schema
├── tests/                     # vitest（12 条）
├── public/geo/china.json      # 中国省界 GeoJSON（本地化，前端地图数据源）
├── results/                   # 分析产物：CSV/PNG/JSON（报告与论文备料）
├── plan.md                    # 两期实现计划
└── requirements.txt / package.json
```

## 快速开始

### 环境要求

- Python 3.13（`requests`、`numpy`、`pandas`、`matplotlib`）
- Node.js 20+（npm）

### 1. 安装与数据爬取

```bash
# Python 依赖（Windows 下建议使用 py 启动器）
py -m pip install -r requirements.txt

# 1) 省份+城市列表（约 2 分钟）
py script/req/getdata.py

# 2) 城市近 14 日 AQI 全量（338 城 × 14 日，约 15~20 分钟，可中断重跑）
py script/req/getAQI.py
```

> 接口只滚动提供最近 14 日数据，库中同窗口覆盖写入；建议每天运行一次 `getAQI.py`。

### 2. 数据分析与预测

```bash
py script/main.py   # 统计+预测 → 覆盖写出 results/
py -m pytest script/tests/ -v   # Python 测试（17 条）
```

产物：`summary_stats.csv`、`city_ranking.csv`、`quality_distribution.csv`、`daily_trend.csv`、`province_summary.csv`、`correlation.csv`、`predictions.csv`、`area_averages.csv`、`overview.png`、`province_overview.png`、`summary.json`、`predictions.json`、`area_averages.json`。

### 3. 前端

```bash
npm install        # 或 npm ci
npm run dev        # http://localhost:3000
# 生产构建：npm run build && npm run start
npm test           # 前端测试（12 条）
```

## 页面路由

| 路由 | 内容 |
|---|---|
| `/` | 全国概览：中国地图（省均值着色）/等级分布/每日趋势+预测点/省 AQI 排名 |
| `/[ProvinceJC]`（如 `/ZJ`） | 省份页：省内城市表、省趋势、7 指标省 vs 全国对比 |
| `/[ProvinceJC]/[CityCode]`（如 `/ZJ/330100`） | 城市页：14+1 天折线 + 预测区间；`?key=PM2.5` 切换指标 |

## API 接口

返回格式 `{ data, error, message }`；公开只读，无鉴权。

| 接口 | 说明 |
|---|---|
| `GET /api/national` | 全国 7 项指标等权均值、明日预测、14 日序列、等级分布、省排名 |
| `GET /api/province/[provinceJC]` | 省均值+预测、省内城市明细（含明日预测）、省每日序列 |
| `GET /api/city/[cityCode]?key=` | 所选指标 14 日序列 + 预测；`key ∈ AQI/SO2/CO/NO2/O3_8h/PM10/PM2.5`（白名单校验） |

## 数据说明

- 来源：中国环境监测总站"全国城市空气质量实时发布平台"
- 字段：SO₂ / CO / NO₂ / O₃-8h / PM10 / PM2.5 二十四小时均值 + AQI + 等级 + 首要污染物
- 等级与配色：HJ 633 国标六等级（优/良/轻度/中度/重度/严重污染）
- 预测局限：AQI 日际波动主要受气象条件驱动，无气象输入的统计外推仅反映短期趋势，标注"仅供参考"

## 已知注意事项

- `CityJC`（城市拼音简称）全国不唯一，城市路由一律使用国标 6 位 `CityCode`
- Next 16.3.4 在 Windows 大写动态段名（`[ProvinceJC]`）下，运行时 params 键与生成类型大小写不一致，页面已做兼容处理
- 中国地图 GeoJSON 已本地化到 `public/geo/china.json`，离线可用
