"use client";

import { EChart } from "./EChart";
import { LevelColors, QualityLevels } from "@/lib/aqiColors";

/** AQI 等级分布饼图 */
export function QualityPie({ data }: { data: { Quality: string; count: number }[] }) {
  const option = {
    title: { text: "近14日空气质量等级分布", left: "center", textStyle: { fontSize: 15 } },
    tooltip: { trigger: "item", formatter: "{b}：{c} 天（{d}%）" },
    legend: { bottom: 0, type: "scroll" },
    series: [
      {
        type: "pie",
        radius: ["38%", "66%"],
        center: ["50%", "52%"],
        data: data.map((d) => ({
          name: d.Quality,
          value: d.count,
          itemStyle: { color: LevelColors[QualityLevels.indexOf(d.Quality)] ?? "#94a3b8" },
        })),
        label: { formatter: "{b}\n{d}%" },
      },
    ],
  };
  return <EChart option={option} height={320} />;
}
