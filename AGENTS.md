# AGENTS.md — 城市天气质量数据检测分析与可视化

## 项目概览

数据管线三段，全链路已完成：

```
script/req（爬取）→ script/analysis（分析/预测）→ Next.js 前端（src/，直读数据库）
```

数据源为中国环境监测总站 <https://air.cnemc.cn:18007>，经清洗后存入 SQLite，下游一律从数据库读，不要直接请求接口。

- 爬取：requests + sqlite3 标准库（`script/req/`）
- 分析：numpy + pandas + matplotlib（`script/analysis/`），产物落 `results/`
- 前端：Next.js 16（App Router）+ TypeScript strict + Tailwind 4 + Zod + ECharts（`src/`），经 API Route + better-sqlite3 直读库（与 Python 同口径），**不读 `results/*.json`**（JSON 仅作报告备料）

## 目录结构

```
prisma/weather.db        # SQLite 数据库（3 张表），数据全量约 4700 行
script/                  # Python 数据管线
  db.py                  #   共享层：DB_PATH、三表 DDL（SCHEMA）、get_conn()
  req/                   # 数据爬取与清洗
    getdata.py           #     省份 + 地市级：爬取入库 & 读库
    getAQI.py            #     城市近 14 日 AQI：爬取入库 & 读库
  analysis/              # 数据分析与预测
    data_loader.py       #     pandas 读库（load_aqi_df / load_cities_df）
    analysis.py          #     统计与聚合（描述统计/排名/等级/趋势/省份汇总/相关矩阵/area_average/area_daily_aqi）
    predict.py           #     最小二乘预测明日 AQI + 95% 区间（14 点线性外推）
    main.py              #     全量统计+全城预测+省/全国均值与明日预测
  tests/                 # pytest（17 条）
  main.py                # 命令行入口：python script/main.py
src/                     # Next.js 前端（App Router）
  app/page.tsx           #   / 全国概览（地图着色/等级饼图/趋势+预测点/省排名）
  app/[ProvinceJC]/page.tsx          # 省页（段名大写，params 键兼容见页内注释）
  app/[ProvinceJC]/[CityCode]/page.tsx  # 城市页（?key= 切换指标，14+1 天折线）
  app/not-found.tsx
  app/api/               #   Route Handlers：national / province/[provinceJC] / city/[cityCode]?key=
  components/            #   chart/(EChart ChinaMap TrendChart QualityPie) ui/ MetricSwitcher ProvinceCompare
  lib/                   #   db queries predict jc aqiColors provinceMap utils
  types/  validations/   #   共享类型 / zod schema（指标白名单）
public/geo/china.json    # 中国省界 GeoJSON（本地化，来源 longwosion/geojson-map-china，jsdelivr 拉取）
results/                 # 分析产物：CSV/PNG/JSON（报告备料）
tests/                   # vitest：predict/jc/queries（12 条）
plan.md                  # 阶段一（Python 分析）+ 阶段二（前端）实现计划
city.json / city_day_AQI.json  # 接口返回格式样例，仅作字段参考（代码不读取）
文档.docx                # 课程材料（已被 .gitignore 忽略）
答辩PPT大纲.md
```

## 常用命令

```bash
# Python 一律用绝对路径或 py，勿裸用 python 关键字
C:\Users\ASUS\AppData\Local\Programs\Python\Python313\python.exe script/req/getdata.py  # 刷新省份+城市，约 2 分钟
C:\...\python.exe script/req/getAQI.py                                                    # 全量刷新 AQI，15~20 分钟，可中断续跑
C:\...\python.exe script/main.py                                                          # 全量分析+预测，覆盖写出 results/
C:\...\python.exe -m pytest script/tests/ -v                                              # Python 全部测试（17 条）
npm run dev              # 前端开发服务器（localhost:3000）
npm run build            # 前端生产构建（含 tsc 校验）
npm run start            # 前端生产模式
npm test                 # 前端 vitest（12 条）
# 依赖：requests（爬虫）；numpy/pandas/matplotlib（分析，requirements.txt）；Next 全家桶见 package.json
```

路径以 `__file__` 推导（`script/../prisma/weather.db`），Python 侧从任意工作目录运行均可；Node 侧约定从项目根运行（`db.ts` 用 `process.cwd()`）。

## 数据模型（prisma/weather.db）

**provinces**（34 行）：`Id` PK | `ProvinceCode` UNIQUE（如 110000）| `ProvinceJC`（BJ）| `ProvinceName`（北京）

**cities**（341 行）：`Id` PK（接口流水号 1~767 全局唯一，按省分段；语义稳定性低于 CityCode）| `CityCode` UNIQUE（如 130100）| `CityName` | `ProvinceId` → provinces.Id | `CityJC`（**全国不唯一**，省内亦有 5 组重复：浙 HZS、皖 CZS、鲁 JNS、湘 YYS、青 HNCZZZZ，共 10 城——故前端路由城市段用 CityCode）

**city_day_aqi**（338 城 × 14 日 = 4732 行）：
`Id` PK（接口 Id）| `CityCode` | `DateTime` TEXT `'YYYY-MM-DD HH:MM:SS'`（东八区）| `TimePoint` INTEGER（毫秒时间戳）| `TimePointStr`（'21日'）| `Area` | `SO2_24h` `CO_24h` `NO2_24h` `O3_8h_24h` `PM10_24h` `PM2_5_24h` `AQI` 均为 REAL（缺失 NULL）| `PrimaryPollutant` | `Quality` | `Measure` | `Unheathful`（接口原始拼写，有意保留）
约束：`UNIQUE(CityCode, DateTime)`；每城仅存最近一次爬取的 14 条。

## 口径约定（Python 与前端严格一致）

- **城市等权**：区域均值 = 每城 14 日均值 → 城市间平均；每日序列 = 每天先城市等权。前端 `src/lib/queries.ts` SQL 版与 Python `area_average/area_daily_aqi` 同口径
- **预测**：最小二乘线性外推 `y = a + b·t`，`t = 0..n-1`，预测 `t = n`，95% 区间 = `pred ± t(0.975,n-2)·s·sqrt(1 + 1/n + (t_n−t̄)²/Sxx)`。Python `predict_next_aqi` ↔ TS `predictNext`，测试使用同一向量（`[3t+10]` → 52）
- AQI 等级色板为 HJ 633 国标：优`#00e400` 良`#f6ec20` 轻`#ff7e00` 中`#ff0000` 重`#8f083a` 严重`#7e0023`

## 下游读取数据

**Python 侧**（返回 `list[dict]`，键名与接口字段一致）：

```python
import sys; sys.path.insert(0, "script/req")
from getdata import get_provice_info, get_city_info   # 省份 / 某省城市（需 p.p 的 Id）
from getAQI import get_city_day_AQI                    # 单城市近14日，按时间升序（入参 CityCode）
```

**前端侧**：三页均为 Server Component 直调 `src/lib/{jc,queries}.ts`；API 三端点 `GET /api/national`、`/api/province/[provinceJC]`、`/api/city/[cityCode]?key=AQI|SO2|CO|NO2|O3_8h|PM10|PM2.5` 返回 `{ data, error, message }`（key 走 zod enum 白名单 → 列名映射 `METRIC_COLUMN`，禁止把用户输入直拼 SQL；key 含 `PM2.5`（点），对象建 key 必须用引号）

## 更新频率

- 行政区划：基本不变，每月或有新城市时跑 `getdata.py`
- AQI：每天跑一次 `getAQI.py`；**接口只滚动提供最近 14 日，库内同样覆盖写入，历史数据不留存**，需长序列请自行定期导出
- 前端无需改动：数据刷新 = 跑分析脚本 → 页面/API 即读库

## 约定与红线（改 `script/` 必须遵守）

1. 数据源仅三个接口：`GET /CityData/GetProvince`、`GET /CityData/GetCitiesByPid?pid=`、`POST /HourChangesPublish/GetCityDayAqiHistoryByCondition?citycode=`
2. 任何批量爬取，请求之间必须 `time.sleep(random.uniform(1.5, 3))`，不得移除
3. 合法空响应（勿当异常）：台湾/香港/澳门（ProvinceId 32/33/34）城市返回 `[]`；县级市 130181、130682、419001 的 AQI 返回 `[]`（此时保留库中旧数据）
4. AQI 入库前按 `TimePoint` 截断为最近 14 条；覆盖语义 = 先 `DELETE` 该城市再插入
5. 字段清洗：浓度与 AQI 转 REAL，空值/'-' 存 NULL；不要改动 `Unheathful` 列名（映射接口原始键）
6. 勿删 `prisma/weather.db`；sync 函数幂等，重复运行安全
7. 不做任何 git 提交/推送操作，除非成员明确要求

## 已知坑（前端）

- **Next 16.3.4 + Windows + 大写段名**：`src/app/[ProvinceJC]/` 运行时 `params` 键是大写 `ProvinceJC`，而生成的 TS 类型是小写——页面已做双键兼容 `as { ProvinceJC?: string; provinceJC?: string }`，勿改回单一解构
- **GeoJSON 不可在线依赖**：DataV/GitHub raw 在本网络不可达；`public/geo/china.json` 已从 jsdelivr 本地化（`longwosion/geojson-map-china`，省全称与库简称不一致，前端用 `src/lib/provinceMap.ts` 映射）
- 首屏地图加载依赖 `public/geo/china.json`（fetch 加载），缺失时地图区域显示"地图加载中"
