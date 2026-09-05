"use client";

import { usePathname, useRouter } from "next/navigation";
import { METRIC_NAME, METRIC_KEYS, type MetricKey } from "@/validations";
import { cn } from "@/lib/utils";

/** 城市页指标切换器：AQI/SO2/CO/NO2/O3_8h/PM10/PM2.5，URL ?key= 同步 */
export function MetricSwitcher({ active }: { active: MetricKey }) {
  const router = useRouter();
  const pathname = usePathname();

  return (
    <div className="flex flex-wrap gap-2">
      {METRIC_KEYS.map((k) => (
        <button
          key={k}
          onClick={() => router.replace(k === "AQI" ? pathname : `${pathname}?key=${k}`)}
          className={cn(
            "rounded-full px-3 py-1 text-sm border transition-colors",
            active === k
              ? "bg-blue-600 text-white border-blue-600"
              : "bg-white text-slate-600 border-slate-300 hover:border-blue-400 hover:text-blue-600"
          )}
        >
          {METRIC_NAME[k]}
        </button>
      ))}
    </div>
  );
}
