import { db } from "./db";

export interface ProvinceRef {
  provinceCode: number;
  name: string;
}

export interface CityRef {
  cityCode: number;
  cityName: string;
  cityJC: string;
}

/** ProvinceJC（如 ZJ）→ 省份信息；不存在返回 null */
export function parseProvinceJC(jc: string): ProvinceRef | null {
  const row = db
    .prepare("SELECT ProvinceCode, ProvinceName FROM provinces WHERE ProvinceJC = ?")
    .get(jc) as { ProvinceCode: number; ProvinceName: string } | undefined;
  if (!row) return null;
  return { provinceCode: row.ProvinceCode, name: row.ProvinceName };
}

/** URL 路由校验：CityCode 唯一 + 必须归属该省（错配返回 null，触发 404） */
export function parseCityRoute(provinceJC: string, cityCode: number): CityRef | null {
  const row = db
    .prepare(
      `SELECT c.CityCode, c.CityName, c.CityJC
       FROM cities c JOIN provinces p ON c.ProvinceId = p.Id
       WHERE c.CityCode = ? AND p.ProvinceJC = ?`
    )
    .get(cityCode, provinceJC) as
    | { CityCode: number; CityName: string; CityJC: string }
    | undefined;
  if (!row) return null;
  return { cityCode: row.CityCode, cityName: row.CityName, cityJC: row.CityJC };
}

/** 省份下所有城市（有 AQI 数据的） */
export function citiesOfProvince(provinceCode: number): CityRef[] {
  const rows = db
    .prepare(
      `SELECT c.CityCode, c.CityName, c.CityJC
       FROM cities c WHERE c.ProvinceId = (
         SELECT Id FROM provinces WHERE ProvinceCode = ?) ORDER BY c.CityCode`
    )
    .all(provinceCode) as { CityCode: number; CityName: string; CityJC: string }[];
  return rows.map((r) => ({ cityCode: r.CityCode, cityName: r.CityName, cityJC: r.CityJC }));
}
