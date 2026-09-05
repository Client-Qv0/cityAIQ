import Link from "next/link";
import { notFound } from "next/navigation";
import { parseProvinceJC } from "@/lib/jc";
import { qProvince } from "@/lib/queries";
import { Breadcrumb } from "@/components/ui/Breadcrumb";
import { StatCard } from "@/components/ui/StatCard";
import { LevelBadge } from "@/components/ui/LevelBadge";
import { TrendChart } from "@/components/chart/TrendChart";
import { ProvinceCompare } from "@/components/ProvinceCompare";
import { colorOf, qualityOf } from "@/lib/aqiColors";
import { fmt } from "@/lib/utils";

export default async function ProvincePage({ params }: { params: Promise<{ provinceJC: string }> }) {
  // Next 16.3.4 在 Windows 大写段名下：运行时键为大写 ProvinceJC，而生成类型为小写 provinceJC——两者兼容
  const p = (await params) as { ProvinceJC?: string; provinceJC?: string };
  const provinceJC = p.ProvinceJC ?? p.provinceJC ?? "";
  const ref = parseProvinceJC(provinceJC);
  if (!ref) notFound();
  const d = qProvince(ref.provinceCode);
  const aqi = d.avg.AQI;

  return (
    <div className="space-y-6">
      <Breadcrumb items={[{ label: "首页", href: "/" }, { label: d.province.ProvinceName }]} />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="省内 AQI 均值（城市等权）" value={fmt(aqi)} sub={qualityOf(aqi)} />
        <StatCard label="明日 AQI 预测" value={fmt(d.avg.next_predicted)} sub="最小二乘外推" />
        <StatCard
          label="预测 95% 区间"
          value={`${fmt(d.avg.next_lower95)} ~ ${fmt(d.avg.next_upper95)}`}
          sub={`r² = ${fmt(d.avg.next_r2, 2)}`}
        />
        <StatCard label="监测城市数" value={String(d.cities.length)} sub="地市级" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="mb-3 font-semibold text-slate-800">省内城市 AQI 均值与预测</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left text-slate-500">
                  <th className="py-2 pr-4">城市</th>
                  <th className="py-2 pr-4">AQI 均值</th>
                  <th className="py-2 pr-4">明日预测</th>
                  <th className="py-2">良好天数</th>
                </tr>
              </thead>
              <tbody>
                {d.cities.map((c) => (
                  <tr key={c.CityCode} className="border-b border-slate-100 last:border-0 hover:bg-slate-50">
                    <td className="py-2 pr-4">
                      <Link
                        href={`/${d.province.ProvinceJC}/${c.CityCode}`}
                        className="hover:text-blue-600 hover:underline"
                      >
                        {c.CityName}
                      </Link>
                    </td>
                    <td className="py-2 pr-4">{fmt(c.AQI_mean)}</td>
                    <td className="py-2 pr-4">{fmt(c.next_predicted)}</td>
                    <td className="py-2">{c.good_days}/14 天</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <TrendChart
            daily={d.daily.map((x) => ({ date: x.date, value: x.AQI }))}
            predict={{
              predicted: d.avg.next_predicted,
              lower95: d.avg.next_lower95,
              upper95: d.avg.next_upper95,
            }}
            title={`${d.province.ProvinceName}每日 AQI（城市等权）`}
            lineColor={colorOf(aqi)}
          />
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-4">
        <h2 className="mb-3 font-semibold text-slate-800">7 项指标：本省 vs 全国（城市等权均值）</h2>
        <ProvinceCompare
          provinceAvg={d.avg}
          nationalAvg={d.national_compare[0]}
        />
      </div>
    </div>
  );
}
