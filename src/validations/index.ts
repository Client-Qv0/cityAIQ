import { z } from "zod";

export const cityCodeSchema = z.coerce.number().int().min(100000).max(999999);

export const provinceJCSchema = z.string().min(2).max(4).regex(/^[A-Z]+$/);

export const METRIC_KEYS = ["AQI", "SO2", "CO", "NO2", "O3_8h", "PM10", "PM2.5"] as const;
export type MetricKey = (typeof METRIC_KEYS)[number];

export const metricKeySchema = z.enum(METRIC_KEYS).default("AQI");

// key 白名单 → 库列名映射，禁止把用户输入直接拼进 SQL
export const METRIC_COLUMN: Record<MetricKey, string> = {
  AQI: "AQI",
  SO2: "SO2_24h",
  CO: "CO_24h",
  NO2: "NO2_24h",
  O3_8h: "O3_8h_24h",
  PM10: "PM10_24h",
  "PM2.5": "PM2_5_24h",
};

export const METRIC_UNIT: Record<MetricKey, string> = {
  AQI: "",
  SO2: "μg/m³",
  CO: "mg/m³",
  NO2: "μg/m³",
  O3_8h: "μg/m³",
  PM10: "μg/m³",
  "PM2.5": "μg/m³",
};

export const METRIC_NAME: Record<MetricKey, string> = {
  AQI: "AQI",
  SO2: "二氧化硫 SO₂",
  CO: "一氧化碳 CO",
  NO2: "二氧化氮 NO₂",
  O3_8h: "臭氧 O₃-8h",
  PM10: "可吸入颗粒物 PM10",
  "PM2.5": "细颗粒物 PM2.5",
};
