"use client";

import { EChart } from "@/components/chart/EChart";
import { METRIC_KEYS, METRIC_NAME } from "@/validations";
import type { MetricKey } from "@/validations";

interface Props {
  provinceAvg: Record<MetricKey, number>;
  nationalAvg: Record<MetricKey, number>;
}

/** 省 vs 全国 7 指标对比横向条形图 */
export function ProvinceCompare({ provinceAvg, nationalAvg }: Props) {
  const keys = [...METRIC_KEYS];
  const option = {
    tooltip: { trigger: "axis" },
    legend: { bottom: 0 },
    grid: { left: 110, right: 24, top: 20, bottom: 56 },
    xAxis: { type: "value" },
    yAxis: {
      type: "category",
      data: keys.map((k) => METRIC_NAME[k]),
      axisLabel: { fontSize: 11 },
    },
    series: [
      {
        name: "本省",
        type: "bar",
        data: keys.map((k) => Number(provinceAvg[k].toFixed(2))),
        itemStyle: { color: "#0ea5e9" },
      },
      {
        name: "全国",
        type: "bar",
        data: keys.map((k) => Number(nationalAvg[k].toFixed(2))),
        itemStyle: { color: "#94a3b8" },
      },
    ],
  };
  return <EChart option={option} height={300} />;
}
