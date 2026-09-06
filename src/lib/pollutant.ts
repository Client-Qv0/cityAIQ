import type { MetricKey } from "@/validations";

/** 污染物指标（不含 AQI 自身） */
export type PollutantKey = Exclude<MetricKey, "AQI">;

/** HJ 633 断点：levels = IAQI 档，caps = 对应浓度（24h / O3 8h） */
export interface PollutantBreaks {
  levels: number[];
  caps: number[];
}

export const POLLUTANT_BREAKS: Record<string, PollutantBreaks> = {
  SO2_24h: { levels: [0, 50, 100, 150, 200, 300, 500], caps: [0, 50, 150, 475, 800, 1600, 2620] },
  CO_24h: { levels: [0, 50, 100, 150, 200, 300, 500], caps: [0, 2, 4, 14, 24, 36, 48] },
  NO2_24h: { levels: [0, 50, 100, 150, 200, 300, 500], caps: [0, 40, 80, 180, 280, 565, 750] },
  O3_8h_24h: { levels: [0, 50, 100, 150, 200, 300], caps: [0, 100, 160, 215, 265, 800] },
  PM10_24h: { levels: [0, 50, 100, 150, 200, 300, 500], caps: [0, 50, 150, 250, 350, 420, 500] },
  PM2_5_24h: { levels: [0, 50, 100, 150, 200, 300, 500], caps: [0, 35, 75, 115, 150, 250, 350] },
};

const COLUMN_TO_KEY: Record<string, PollutantKey> = {
  SO2_24h: "SO2",
  CO_24h: "CO",
  NO2_24h: "NO2",
  O3_8h_24h: "O3_8h",
  PM10_24h: "PM10",
  PM2_5_24h: "PM2.5",
};

export const GOV_ACTIONS: Record<PollutantKey, string[]> = {
  "PM2.5": ["加强施工扬尘与道路扬尘管控", "开展机动车排放抽检与限行", "督导涉尘企业错峰生产"],
  PM10: ["强化施工工地抑尘措施检查", "加大道路机械化清扫与洒水频次", "加强矿山及物料堆场覆盖管理"],
  O3_8h: ["推进 VOC 与 NOx 协同管控", "鼓励加油站错峰卸油与夜间作业", "强化沥青涂装等挥发性工序错时施工"],
  NO2: ["优化交通组织并扩大公共交通运力", "严格柴油货车限行与排放检查", "加强机动车尾气遥感监测执法"],
  SO2: ["督促燃煤设施稳定达标排放", "推进清洁能源替代与煤改气工程", "强化工业窑炉在线监控"],
  CO: ["治理机动车尾气与怠速排放", "强化冬季取暖燃煤监管", "排查密闭空间与工业锅炉一氧化碳隐患"],
};

export const PERSONAL_ACTIONS: Record<PollutantKey, string[]> = {
  "PM2.5": ["减少户外活动", "外出佩戴 KN95 级别口罩", "关闭门窗并开启空气净化器"],
  PM10: ["户外活动做好防护", "避免剧烈运动", "回家后及时清洗面部与鼻腔"],
  O3_8h: ["午后时段减少户外停留", "通风优先选择清晨", "敏感人群避免长时间户外"],
  NO2: ["减少私家车出行", "避开主干道等拥堵路段", "骑行或步行时远离车流"],
  SO2: ["减少户外活动", "敏感人群做好呼吸防护", "居家及时关闭门窗"],
  CO: ["保持室内通风", "不在密闭空间使用燃油设备", "避免吸入二手烟"],
};

/** 浓度 → IAQI（线性插值；None/<=0 返回 null；超出档顶按最高档封顶） */
export function iaqi(conc: number | null, breaks: PollutantBreaks): number | null {
  if (conc === null || !Number.isFinite(conc) || conc <= 0) return null;
  const { levels, caps } = breaks;
  for (let i = 0; i < levels.length - 1; i++) {
    if (conc <= caps[i + 1]) {
      const loC = caps[i];
      const hiC = caps[i + 1];
      const loI = levels[i];
      const hiI = levels[i + 1];
      if (hiC === loC) return hiI;
      return hiI - ((hiI - loI) * (hiC - conc)) / (hiC - loC);
    }
  }
  return levels[levels.length - 1];
}

export interface PollutantDay {
  date: string;
  SO2_24h: number | null;
  CO_24h: number | null;
  NO2_24h: number | null;
  O3_8h_24h: number | null;
  PM10_24h: number | null;
  PM2_5_24h: number | null;
  AQI: number | null;
}

export interface PollutantResult {
  good: boolean;
  note: string;
  AQI: number;
  main: PollutantKey[];
  government: string[];
  personal: string[];
  week7: {
    avg_aqi: number;
    good_days: number;
    freq: Record<PollutantKey, number>;
    dominant: PollutantKey | null;
    good: boolean;
  };
}

function judge(day: PollutantDay, threshold: number): { mains: PollutantKey[]; good: boolean } {
  const iaqis: Record<string, number> = {};
  for (const [col, key] of Object.entries(COLUMN_TO_KEY)) {
    const v = iaqi(day[col as keyof PollutantDay] as number | null, POLLUTANT_BREAKS[col]);
    if (v !== null && v > 0) iaqis[key] = v;
  }
  const aqi = day.AQI ?? 0;
  if (aqi <= threshold) return { mains: [], good: true };
  const values = Object.entries(iaqis);
  if (values.length === 0) return { mains: [], good: true };
  const mx = Math.max(...values.map(([, v]) => v));
  return {
    mains: values.filter(([, v]) => v === mx).map(([k]) => k as PollutantKey),
    good: false,
  };
}

export const GOOD_NOTE = "空气质量佳，适宜外出游玩";

/** 双粒度分析：最近 1 天（主控因子+建议，主要）+ 最近 7 天（频次参照，次要） */
export function analyzePollutant(rows: PollutantDay[], threshold = 50): PollutantResult {
  rows = [...rows].sort((a, b) => a.date.localeCompare(b.date));
  const latest = rows[rows.length - 1];
  const { mains, good } = judge(latest, threshold);
  const government = good ? [] : [...new Set(mains.flatMap((m) => GOV_ACTIONS[m]))];
  const personal = good ? [] : [...new Set(mains.flatMap((m) => PERSONAL_ACTIONS[m]))];

  const tail = rows.slice(-7);
  const freq: Partial<Record<PollutantKey, number>> = {};
  let goodDays = 0;
  for (const day of tail) {
    const j = judge(day, threshold);
    if (j.good) goodDays++;
    for (const m of j.mains) freq[m] = (freq[m] ?? 0) + 1;
  }
  const dominantEntries = Object.entries(freq);
  let dominant: PollutantKey | null = null;
  if (dominantEntries.length > 0) {
    dominant = dominantEntries.sort(([, a], [, b]) => b - a)[0][0] as PollutantKey;
  }
  const avgAqi = tail.length ? tail.reduce((s, d) => s + (d.AQI ?? 0), 0) / tail.length : 0;

  return {
    good,
    note: good ? GOOD_NOTE : "",
    AQI: latest.AQI ?? 0,
    main: mains,
    government,
    personal,
    week7: {
      avg_aqi: Math.round(avgAqi * 100) / 100,
      good_days: goodDays,
      freq: freq as Record<PollutantKey, number>,
      dominant,
      good: goodDays === tail.length,
    },
  };
}
