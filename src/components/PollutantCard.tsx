"use client";

import { usePathname, useSearchParams } from "next/navigation";
import { useRouter } from "next/navigation";
import type { PollutantResult } from "@/lib/pollutant";
import { METRIC_NAME } from "@/validations";
import { cn } from "@/lib/utils";
import { colorOf } from "@/lib/aqiColors";

const THRESHOLDS = [50, 100, 150];

/** 主要污染物分析与建议卡：当日（主要）+ 近 7 日（参照），阈值可切换 */
export function PollutantCard({ result }: { result: PollutantResult }) {
  const router = useRouter();
  const pathname = usePathname();
  const search = useSearchParams();
  const threshold = Number(search.get("threshold") ?? "50");

  const switchThreshold = (t: number) => {
    const params = new URLSearchParams(search.toString());
    params.set("threshold", String(t));
    router.replace(`${pathname}?${params.toString()}`);
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h2 className="font-semibold text-slate-800">主要污染物分析与建议</h2>
        <div className="flex items-center gap-1 text-xs">
          <span className="mr-1 text-slate-500">AQI 阈值：</span>
          {THRESHOLDS.map((t) => (
            <button
              key={t}
              onClick={() => switchThreshold(t)}
              className={cn(
                "rounded-full border px-2 py-0.5",
                threshold === t
                  ? "bg-blue-600 text-white border-blue-600"
                  : "bg-white text-slate-600 border-slate-300 hover:border-blue-400"
              )}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {result.good ? (
        <div className="rounded-lg bg-emerald-50 px-4 py-6 text-center">
          <div className="text-lg font-semibold text-emerald-700">{result.note}</div>
          <div className="mt-1 text-xs text-emerald-600">
            当日 AQI = {result.AQI}（≤ 阈值 {threshold}）
          </div>
        </div>
      ) : (
        <>
          {/* 当日（主要） */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm text-slate-500">当日主要污染物：</span>
            {result.main.map((m) => (
              <span
                key={m}
                className="rounded-full px-3 py-1 text-sm font-medium text-white"
                style={{ backgroundColor: colorOf(result.AQI) }}
              >
                {METRIC_NAME[m]}
              </span>
            ))}
            <span className="text-sm text-slate-600">
              当日 AQI <b>{result.AQI}</b> (&gt; 阈值 {threshold})
            </span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="rounded-lg bg-slate-50 p-3">
              <div className="mb-2 text-sm font-medium text-slate-700">政府建议</div>
              <ul className="space-y-1.5 text-sm text-slate-600">
                {result.government.map((a, i) => (
                  <li key={i}>· {a}</li>
                ))}
              </ul>
            </div>
            <div className="rounded-lg bg-slate-50 p-3">
              <div className="mb-2 text-sm font-medium text-slate-700">个人建议</div>
              <ul className="space-y-1.5 text-sm text-slate-600">
                {result.personal.map((a, i) => (
                  <li key={i}>· {a}</li>
                ))}
              </ul>
            </div>
          </div>
        </>
      )}

      {/* 近 7 日（参照） */}
      <div className="rounded-lg border border-slate-100 p-3">
        <div className="mb-2 text-sm font-medium text-slate-700">近 7 日参照</div>
        <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm text-slate-600">
          <span>7 日 AQI 均值：<b>{result.week7.avg_aqi}</b></span>
          <span>优良天数：<b>{result.week7.good_days}/7</b></span>
          <span>
            主要污染物出现频次：
            {Object.entries(result.week7.freq).length === 0 ? (
              <b className="text-emerald-700"> 无（7 日均优）</b>
            ) : (
              Object.entries(result.week7.freq).map(([k, v]) => (
                <b key={k} className="ml-1 text-orange-600">
                  {METRIC_NAME[k as keyof typeof METRIC_NAME]} ×{v}
                </b>
              ))
            )}
          </span>
        </div>
        {result.week7.dominant && (
          <div className="mt-1 text-xs text-slate-400">
            提示：主要污染物在近 7 日出现 {result.week7.freq[result.week7.dominant]} 次，属持续性特征
          </div>
        )}
      </div>
    </div>
  );
}
