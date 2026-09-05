import { db } from "./db";
import { predictNext } from "./predict";
import { METRIC_COLUMN, METRIC_KEYS, type MetricKey } from "@/validations";
import type { NationalData, ProvinceData, CityData } from "@/types";

/** 区域等权均值 SQL：先城市日均，再城市间平均（与 Python area_average 同口径） */
function areaAvgSQL(column: string, provinceCode?: number): string {
  const where = provinceCode === undefined ? "" : ` WHERE p.ProvinceCode = ${provinceCode}`;
  return `SELECT AVG(city_avg) AS v FROM (
    SELECT a.CityCode, AVG("${column}") AS city_avg
    FROM city_day_aqi a JOIN cities c ON a.CityCode = c.CityCode
    JOIN provinces p ON c.ProvinceId = p.Id${where}
    GROUP BY a.CityCode)`;
}

function areaAvg(column: string, provinceCode?: number): number {
  const row = db.prepare(areaAvgSQL(column, provinceCode)).get() as { v: number | null };
  return row.v === null ? 0 : row.v;
}

/** 每日区域等权 AQI 序列（每天先城市等权） */
function areaDailySeries(provinceCode?: number): { date: string; AQI: number }[] {
  const where = provinceCode === undefined ? "" : ` WHERE p.ProvinceCode = ${provinceCode}`;
  const rows = db
    .prepare(
      `SELECT dt, AVG(v) AS AQI FROM (
         SELECT a.DateTime AS dt, a.CityCode, AVG(a.AQI) AS v
         FROM city_day_aqi a JOIN cities c ON a.CityCode = c.CityCode
         JOIN provinces p ON c.ProvinceId = p.Id${where}
         GROUP BY a.DateTime, a.CityCode
       ) GROUP BY dt ORDER BY dt`
    )
    .all() as { dt: string; AQI: number }[];
  return rows.map((r) => ({ date: r.dt.slice(0, 10), AQI: r.AQI }));
}

/** 单指标区域均值 + 明日预测（7 项里只对选中的列做预测） */
function areaAvgWithPredict(provinceCode?: number) {
  const avg = {} as Record<MetricKey, number>;
  for (const key of METRIC_KEYS) avg[key] = Number(areaAvg(METRIC_COLUMN[key], provinceCode).toFixed(2));
  const daily = areaDailySeries(provinceCode);
  const values = daily.map((d) => d.AQI);
  const pred = predictNext(values);
  return {
    avg: {
      ...avg,
      next_day: daily[daily.length - 1]?.date ?? "",
      next_predicted: pred.predicted,
      next_lower95: pred.lower95,
      next_upper95: pred.upper95,
      next_r2: pred.r2,
    },
    daily,
  };
}

function statsOf(): Record<string, { mean: number; max: number }> {
  const out: Record<string, { mean: number; max: number }> = {};
  for (const key of METRIC_KEYS) {
    const col = METRIC_COLUMN[key];
    const row = db
      .prepare(`SELECT AVG("${col}") AS mean, MAX("${col}") AS max FROM city_day_aqi`)
      .get() as { mean: number; max: number };
    out[key] = { mean: Number(row.mean.toFixed(2)), max: row.max };
  }
  return out;
}

export function qNational(): NationalData {
  const { avg, daily } = areaAvgWithPredict();
  const stats = statsOf();
  const quality = db
    .prepare(`SELECT Quality, COUNT(*) AS count FROM city_day_aqi GROUP BY Quality ORDER BY count DESC`)
    .all() as { Quality: string; count: number }[];
  const province_rank = db
    .prepare(
      `SELECT p.ProvinceName, p.ProvinceJC, AVG(v) AS AQI_mean FROM (
         SELECT c.ProvinceId, AVG(a.AQI) AS v FROM city_day_aqi a JOIN cities c ON a.CityCode = c.CityCode
         GROUP BY c.ProvinceId, a.CityCode
       ) JOIN provinces p ON p.Id = ProvinceId GROUP BY ProvinceId ORDER BY AQI_mean DESC`
    )
    .all() as { ProvinceName: string; ProvinceJC: string; AQI_mean: number }[];
  const range = db
    .prepare(`SELECT MIN(DateTime) AS mn, MAX(DateTime) AS mx FROM city_day_aqi`)
    .get() as { mn: string; mx: string };
  return {
    stats,
    avg,
    daily,
    quality,
    province_rank: province_rank.map((r) => ({
      ...r,
      AQI_mean: Number(r.AQI_mean.toFixed(2)),
    })),
    data_range: [range.mn.slice(0, 10), range.mx.slice(0, 10)],
  };
}

export function qProvince(provinceCode: number): ProvinceData {
  const { avg, daily } = areaAvgWithPredict(provinceCode);
  const province = db
    .prepare(`SELECT ProvinceName, ProvinceJC FROM provinces WHERE ProvinceCode = ?`)
    .get(provinceCode) as { ProvinceName: string; ProvinceJC: string };
  const citiesRows = db
    .prepare(
      `SELECT a.CityCode, c.CityName, AVG(a.AQI) AS AQI_mean,
              SUM(CASE WHEN a.Quality IN ('优','良') THEN 1 ELSE 0 END) AS good_days
       FROM city_day_aqi a JOIN cities c ON a.CityCode = c.CityCode
       JOIN provinces p ON c.ProvinceId = p.Id WHERE p.ProvinceCode = ?
       GROUP BY a.CityCode ORDER BY AQI_mean DESC`
    )
    .all(provinceCode) as {
    CityCode: number;
    CityName: string;
    AQI_mean: number;
    good_days: number;
  }[];
  const cities = citiesRows.map((r) => {
    const values = db
      .prepare(`SELECT AQI AS v FROM city_day_aqi WHERE CityCode = ? ORDER BY DateTime`)
      .pluck()
      .all(r.CityCode) as number[];
    return {
      CityCode: r.CityCode,
      CityName: r.CityName,
      AQI_mean: Number(r.AQI_mean.toFixed(1)),
      good_days: r.good_days,
      next_predicted: Number(predictNext(values).predicted.toFixed(1)),
    };
  });
  const national = areaAvgWithPredict();
  return {
    province: { ProvinceName: province.ProvinceName, ProvinceJC: province.ProvinceJC, city_count: cities.length },
    avg,
    cities,
    daily,
    national_compare: [nationAvgKeys(national.avg)],
  };
}

function nationAvgKeys(nationalAvg: Record<MetricKey, number> | Record<string, unknown>) {
  const m = nationalAvg as Record<MetricKey, number>;
  const o = {} as Record<MetricKey, number>;
  for (const k of METRIC_KEYS) o[k] = m[k];
  return o;
}

export function qCity(cityCode: number, key: MetricKey): CityData {  const col = METRIC_COLUMN[key];
  const rows = db
    .prepare(
      `SELECT DateTime, "${col}" AS value, AQI, Quality, PrimaryPollutant
       FROM city_day_aqi WHERE CityCode = ? ORDER BY DateTime`
    )
    .all(cityCode) as {
    DateTime: string;
    value: number | null;
    AQI: number | null;
    Quality: string;
    PrimaryPollutant: string | null;
  }[];
  if (rows.length === 0) throw new Error(`no data for city ${cityCode}`);

  const values = rows.map((r) => r.value ?? 0);
  const aqiValues = rows.map((r) => r.AQI ?? 0);
  const predict = predictNext(values);
  const mean = values.reduce((a, b) => a + b, 0) / values.length;
  const max = Math.max(...values);
  const goodDays = rows.filter((r) => r.Quality === "优" || r.Quality === "良").length;

  // 首要污染物：非空调格频次最高的
  const counts = new Map<string, number>();
  for (const r of rows) {
    if (!r.PrimaryPollutant || r.PrimaryPollutant === "无") continue;
    counts.set(r.PrimaryPollutant, (counts.get(r.PrimaryPollutant) ?? 0) + 1);
  }
  let primary: string | null = null;
  let best = 0;
  for (const [name, c] of counts) {
    if (c > best) {
      best = c;
      primary = name;
    }
  }

  const cityInfo = db
    .prepare(
      `SELECT c.CityCode, c.CityName, c.CityJC, p.ProvinceName
       FROM cities c JOIN provinces p ON c.ProvinceId = p.Id WHERE c.CityCode = ?`
    )
    .get(cityCode) as {
    CityCode: number;
    CityName: string;
    CityJC: string;
    ProvinceName: string;
  };

  return {
    city: cityInfo,
    key,
    unit: key === "AQI" ? "" : key === "CO" ? "mg/m³" : "μg/m³",
    daily: rows.map((r, i) => ({
      date: r.DateTime.slice(0, 10),
      value: values[i],
      ...(key === "AQI" ? { Quality: r.Quality } : {}),
    })),
    predict: {
      ...predict,
      r2: Number(predict.r2.toFixed(4)),
      predicted: Number(predict.predicted.toFixed(2)),
      lower95: Number(predict.lower95.toFixed(2)),
      upper95: Number(predict.upper95.toFixed(2)),
      slope: Number(predict.slope.toFixed(4)),
    },
    summary: {
      mean: Number(mean.toFixed(1)),
      max,
      good_days: goodDays,
      primary_pollutant: primary,
    },
  };
}

// ---------- 侧边栏导航树 ----------

export interface NavCity {
  CityCode: number;
  CityName: string;
  CityJC: string;
}
export interface NavProvince {
  ProvinceJC: string;
  ProvinceName: string;
  cities: NavCity[];
}

/** 导航树：省份 → 城市（仅含有 AQI 数据的城市，避免死链） */
export function qNavTree(): NavProvince[] {
  const rows = db
    .prepare(
      `SELECT p.ProvinceJC, p.ProvinceName, c.CityCode, c.CityName, c.CityJC
       FROM provinces p
       JOIN cities c ON c.ProvinceId = p.Id
       WHERE EXISTS (SELECT 1 FROM city_day_aqi a WHERE a.CityCode = c.CityCode)
       ORDER BY p.ProvinceCode, c.CityCode`
    )
    .all() as {
    ProvinceJC: string;
    ProvinceName: string;
    CityCode: number;
    CityName: string;
    CityJC: string;
  }[];
  const map = new Map<string, NavProvince>();
  for (const r of rows) {
    let p = map.get(r.ProvinceJC);
    if (!p) {
      p = { ProvinceJC: r.ProvinceJC, ProvinceName: r.ProvinceName, cities: [] };
      map.set(r.ProvinceJC, p);
    }
    p.cities.push({ CityCode: r.CityCode, CityName: r.CityName, CityJC: r.CityJC });
  }
  return [...map.values()];
}
