import type { PredictResult } from "@/lib/predict";
import type { MetricKey } from "@/validations";

export interface NationalData {
  stats: Record<string, { mean: number; max: number }>;
  avg: Record<MetricKey, number> & {
    next_day: string;
    next_predicted: number;
    next_lower95: number;
    next_upper95: number;
    next_r2: number;
  };
  daily: { date: string; AQI: number }[];
  quality: { Quality: string; count: number }[];
  province_rank: { ProvinceName: string; ProvinceJC: string; AQI_mean: number }[];
  data_range: string[];
}

export interface ProvinceData {
  province: { ProvinceName: string; ProvinceJC: string; city_count: number };
  avg: Record<MetricKey, number> & {
    next_day: string;
    next_predicted: number;
    next_lower95: number;
    next_upper95: number;
    next_r2: number;
  };
  cities: {
    CityCode: number;
    CityName: string;
    AQI_mean: number;
    good_days: number;
    next_predicted: number;
  }[];
  daily: { date: string; AQI: number }[];
  national_compare: Record<MetricKey, number>[];
}

export interface CityData {
  city: { CityCode: number; CityName: string; ProvinceName: string; CityJC: string };
  key: MetricKey;
  unit: string;
  daily: { date: string; value: number; Quality?: string }[];
  predict: PredictResult;
  summary: {
    mean: number;
    max: number;
    good_days: number;
    primary_pollutant: string | null;
  };
}
