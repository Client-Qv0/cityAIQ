"use client";

import ReactECharts from "echarts-for-react";

interface Props {
  option: object;
  height?: number;
  onEvents?: Record<string, (params: unknown) => void>;
}

export function EChart({ option, height = 360, onEvents }: Props) {
  return (
    <ReactECharts
      option={option}
      notMerge
      style={{ height, width: "100%" }}
      onEvents={onEvents}
    />
  );
}
