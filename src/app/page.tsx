import Link from "next/link";
import { qNational } from "@/lib/queries";
import { StatCard } from "@/components/ui/StatCard";
import { LevelBadge } from "@/components/ui/LevelBadge";
import { ChinaMap } from "@/components/chart/ChinaMap";
import { QualityPie } from "@/components/chart/QualityPie";
import { TrendChart } from "@/components/chart/TrendChart";
import { colorOf, qualityOf } from "@/lib/aqiColors";
import { fmt } from "@/lib/utils";

export default function HomePage() {
  const d = qNational();
  const aqi = d.avg.AQI;
  const q = qualityOf(aqi);

  return (
    <div className="space-y-6">
      {/* KPI 行 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="全国 AQI 均值（近14日，城市等权）" value={fmt(aqi)} sub={q} />
        <StatCard label="明日 AQI 预测" value={fmt(d.avg.next_predicted)} sub="最小二乘线性外推" />
        <StatCard
          label="预测 95% 区间"
          value={`${fmt(d.avg.next_lower95)} ~ ${fmt(d.avg.next_upper95)}`}
          sub={`r² = ${fmt(d.avg.next_r2, 2)}`}
        />
        <StatCard
          label="数据窗口"
          value={`${d.data_range[0].slice(5)} ~ ${d.data_range[1].slice(5)}`}
          sub={`${d.quality[0]?.count ?? 0} 天次优 | 338 城市`}
        />
      </div>

      {/* 地图 + 饼图 + 趋势 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <ChinaMap data={d.province_rank} />
        </div>
        <div className="flex flex-col gap-4">
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <QualityPie data={d.quality} />
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <TrendChart
              daily={d.daily.map((x) => ({ date: x.date, value: x.AQI }))}
              predict={{ predicted: d.avg.next_predicted, lower95: d.avg.next_lower95, upper95: d.avg.next_upper95 }}
              title="全国每日 AQI（城市等权）"
              lineColor={colorOf(aqi)}
            />
          </div>
        </div>
      </div>

      {/* 省排名 */}
      <div className="rounded-xl border border-slate-200 bg-white p-4">
        <h2 className="mb-3 font-semibold text-slate-800">各省 AQI 均值排名（近14日，城市等权）</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-slate-500">
                <th className="py-2 pr-4">#</th>
                <th className="py-2 pr-4">省份</th>
                <th className="py-2 pr-4">AQI 均值</th>
                <th className="py-2">等级</th>
              </tr>
            </thead>
            <tbody>
              {d.province_rank.map((p, i) => (
                <tr key={p.ProvinceJC} className="border-b border-slate-100 last:border-0 hover:bg-slate-50">
                  <td className="py-2 pr-4 text-slate-400">{i + 1}</td>
                  <td className="py-2 pr-4">
                    <Link href={`/${p.ProvinceJC}`} className="hover:text-blue-600 hover:underline">{p.ProvinceName}</Link>
                  </td>
                  <td className="py-2 pr-4">{fmt(p.AQI_mean)}</td>
                  <td className="py-2">
                    <LevelBadge text={qualityOf(p.AQI_mean)} color={colorOf(p.AQI_mean)} small />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
