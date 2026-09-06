import { notFound } from "next/navigation";
import { parseCityRoute } from "@/lib/jc";
import { cityCodeSchema, metricKeySchema, METRIC_NAME, METRIC_UNIT, type MetricKey } from "@/validations";
import { qCity } from "@/lib/queries";
import { Breadcrumb } from "@/components/ui/Breadcrumb";
import { MetricSwitcher } from "@/components/MetricSwitcher";
import { PollutantCard } from "@/components/PollutantCard";
import { TrendChart } from "@/components/chart/TrendChart";
import { colorOf, qualityOf } from "@/lib/aqiColors";
import { fmt } from "@/lib/utils";

const COLOR_TABLE: Record<MetricKey, string> = {
  AQI: "#2563eb",
  SO2: "#0ea5e9",
  CO: "#10b981",
  NO2: "#f59e0b",
  O3_8h: "#8b5cf6",
  PM10: "#ec4899",
  "PM2.5": "#14b8a6",
};

const THRESHOLDS = ["50", "100", "150"];

export default async function CityPage({
  params,
  searchParams,
}: {
  params: Promise<{ provinceJC: string; cityCode: string }>;
  searchParams: Promise<{ key?: string; threshold?: string }>;
}) {
  // Next 16.3.4 在 Windows 大写段名下：运行时键为大写，而生成类型为小写——两者兼容
  const p = (await params) as { ProvinceJC?: string; provinceJC?: string; CityCode?: string; cityCode?: string };
  const provinceJC = p.ProvinceJC ?? p.provinceJC ?? "";
  const cityCode = p.CityCode ?? p.cityCode ?? "";
  const parsedCode = cityCodeSchema.safeParse(cityCode);
  if (!parsedCode.success) notFound();
  const ref = parseCityRoute(provinceJC, parsedCode.data);
  if (!ref) notFound();

  const sp = await searchParams;
  const { key } = sp;
  const keyParsed = metricKeySchema.safeParse(key ?? undefined);
  const metric: MetricKey = keyParsed.success ? keyParsed.data : "AQI";
  const threshold = THRESHOLDS.includes(sp.threshold ?? "") ? Number(sp.threshold) : 50;

  const d = qCity(ref.cityCode, metric, threshold);
  const lastValue = d.daily[d.daily.length - 1]?.value ?? 0;
  const levelColor = metric === "AQI" ? colorOf(lastValue) : COLOR_TABLE[metric];
  const quality = metric === "AQI" ? qualityOf(lastValue) : undefined;
  const unit = metric === "AQI" ? "" : METRIC_UNIT[metric];

  return (
    <div className="space-y-6">
      <Breadcrumb
        items={[
          { label: "首页", href: "/" },
          { label: d.city.ProvinceName, href: `/${provinceJC}` },
          { label: d.city.CityName },
        ]}
      />

      {/* 指标切换器 */}
      <MetricSwitcher active={metric} />

      {/* KPI 卡 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div
          className="rounded-xl p-4 shadow-sm"
          style={{ backgroundColor: levelColor }}
        >
          <div className="text-xs text-white/80">最新值 · 近14日均值 {fmt(d.summary.mean)}</div>
          <div className="mt-1 text-3xl font-bold text-white">
            {fmt(lastValue)} <span className="text-base font-normal">{unit}</span>
          </div>
          {quality && <div className="mt-1 text-xs text-white/80">{quality}（最后一日）</div>}
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-xs text-slate-500">明日预测</div>
          <div className="mt-1 text-2xl font-bold text-slate-900">
            {fmt(d.predict.predicted)} <span className="text-sm font-normal">{unit}</span>
          </div>
          {quality && <div className="mt-1 text-xs text-slate-400">{quality !== "优" && quality !== "良" ? "趋势预警" : "趋势平稳"} · 仅供参考</div>}
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-xs text-slate-500">预测 95% 区间</div>
          <div className="mt-1 text-2xl font-bold text-slate-900">
            {fmt(d.predict.lower95)} ~ {fmt(d.predict.upper95)}
          </div>
          <div className="mt-1 text-xs text-slate-400">r² = {fmt(d.predict.r2, 2)}</div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-xs text-slate-500">14 日概览</div>
          <div className="mt-1 text-2xl font-bold text-slate-900">{d.summary.max}</div>
          <div className="mt-1 text-xs text-slate-400">
            最大值{d.summary.primary_pollutant ? ` · 首要污染物 ${d.summary.primary_pollutant}` : ""}
          </div>
        </div>
      </div>

      {/* 14+1 折线 */}
      <div className="rounded-xl border border-slate-200 bg-white p-4">
        <TrendChart
          daily={d.daily.map((x) => ({ date: x.date, value: x.value }))}
          predict={{
            predicted: d.predict.predicted,
            lower95: d.predict.lower95,
            upper95: d.predict.upper95,
          }}
          title={`${d.city.CityName} · ${METRIC_NAME[metric]} 近14日与明日预测`}
          unit={unit}
          lineColor={levelColor}
        />
      </div>

      {/* 主要污染物分析与建议 */}
      <PollutantCard result={d.pollutant} />

      {/* 信息卡 */}
      <div className="rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-600">
        <span className="mr-6">城市编码：{d.city.CityCode}</span>
        <span className="mr-6">城市简称：{d.city.CityJC}</span>
        <span className="mr-6">所属：{d.city.ProvinceName}</span>
        <span>数据范围：{d.daily[0]?.date} ~ {d.daily[d.daily.length - 1]?.date}</span>
      </div>
    </div>
  );
}
