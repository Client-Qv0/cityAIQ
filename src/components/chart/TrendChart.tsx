"use client";

import { EChart } from "./EChart";

export interface TrendPoint {
  date: string;
  value: number;
}

export interface PredictBand {
  predicted: number;
  lower95: number;
  upper95: number;
}

interface Props {
  daily: TrendPoint[];
  predict: PredictBand;
  title: string;
  unit?: string;
  lineColor?: string;
  valueFormatter?: (v: number) => string;
}

/** 14 日趋势 + 明日预测点/区间折线（x 轴追加"明日(预测)"） */
export function TrendChart({ daily, predict, title, unit = "", lineColor = "#2563eb" }: Props) {
  const dates = daily.map((d) => d.date.slice(5));
  const labels = [...dates, "明日(预测)"];
  const values = daily.map((d) => d.value);

  const n = values.length;

  const predictLine = [
    ...Array<number | null>(n - 1).fill(null),
    values[n - 1],
    predict.predicted,
  ];
  const bandLow = [...Array<number | null>(n - 1).fill(null), predict.lower95];
  const bandSpan = [
    ...Array<number | null>(n - 1).fill(null),
    predict.upper95 - predict.lower95,
  ];

  const option = {
    title: { text: title, left: "center", textStyle: { fontSize: 15 } },
    tooltip: {
      trigger: "axis",
      valueFormatter: (v: unknown) => (v == null ? "-" : `${v}${unit}`),
    },
    legend: { bottom: 0, data: [title, "明日预测", "95% 区间"] },
    grid: { left: 50, right: 48, top: 48, bottom: 56 },
    xAxis: {
      type: "category",
      data: labels,
      axisLabel: { rotate: 45, fontSize: 10 },
    },
    yAxis: { type: "value", name: unit },
    series: [
      { name: title, type: "line", data: [...values, null], symbol: "circle", symbolSize: 6, lineStyle: { width: 2 }, itemStyle: { color: lineColor } },
      { name: "明日预测", type: "line", data: predictLine, symbolSize: 8, symbol: "diamond", lineStyle: { width: 2, type: "dashed", color: "#dc2626" }, itemStyle: { color: "#dc2626" } },
      { name: "95% 区间", type: "line", stack: "band", data: bandLow, lineStyle: { opacity: 0 }, symbol: "none", tooltip: { show: false } },
      { name: "95% 区间", type: "line", stack: "band", data: bandSpan, lineStyle: { opacity: 0.35, width: 0 }, symbol: "none", areaStyle: { color: "rgba(220,38,38,0.12)" }, tooltip: { show: false } },
    ],
  };
  return <EChart option={option} height={380} />;
}
