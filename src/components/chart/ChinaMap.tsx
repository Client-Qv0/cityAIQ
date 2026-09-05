"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import * as echarts from "echarts";
import { EChart } from "./EChart";
import { LevelColors, QualityLevels } from "@/lib/aqiColors";
import { SHORT_TO_FULL } from "@/lib/provinceMap";

export interface ProvinceRankItem {
  ProvinceName: string;
  ProvinceJC: string;
  AQI_mean: number;
}

let registered = false;

/** 中国地图：省均值着色（HJ 633 六段色阶），点击省份跳转 */
export function ChinaMap({ data }: { data: ProvinceRankItem[] }) {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (registered) return setReady(true);
    fetch("/geo/china.json")
      .then((r) => r.json())
      .then((geo) => {
        if (geo.features?.length) {
          echarts.registerMap("china", geo);
        }
        registered = true;
        setReady(true);
      })
      .catch(() => setReady(false));
  }, []);

  if (!ready) return <div style={{ height: 420 }} className="flex items-center justify-center text-slate-400">地图加载中…</div>;

  const mapData = data.map((d) => ({
    name: SHORT_TO_FULL[d.ProvinceName] ?? d.ProvinceName,
    value: d.AQI_mean,
    jc: d.ProvinceJC,
  }));

  const option = {
    title: { text: "全国各省 AQI 均值（近14日）", left: "center", textStyle: { fontSize: 15 } },
    tooltip: {
      formatter: (p: { name: string; value?: number; data?: { jc: string } }) =>
        `${p.name}<br/>AQI 均值：${p.value?.toFixed(1) ?? "-"}`,
    },
    visualMap: {
      min: 0,
      max: 150,
      inRange: { color: LevelColors },
      text: ["高", "低"],
      left: 20,
      bottom: 20,
      calculable: true,
    },
    series: [
      {
        type: "map",
        map: "china",
        roam: false,
        zoom: 1.5,
        label: { show: false },
        emphasis: { label: { show: true, fontSize: 11 } },
        itemStyle: { borderColor: "#cbd5e1" },
        data: mapData,
      },
    ],
  };

  return (
    <EChart
      option={option}
      height={430}
      onEvents={{
        click: (p: unknown) => {
          const jc = (p as { data?: { jc?: string } })?.data?.jc;
          if (jc) router.push(`/${jc}`);
        },
      }}
    />
  );
}
