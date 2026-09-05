import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: string;
  sub?: string;
  themeClass?: string;
}

export function StatCard({ label, value, sub, themeClass }: StatCardProps) {
  return (
    <div
      className={cn(
        "rounded-xl border border-slate-200 bg-white p-4 shadow-sm",
        themeClass && "border-transparent"
      )}
    >
      <div className="text-xs text-slate-500">{label}</div>
      <div className={cn("mt-1 text-2xl font-bold", themeClass ? "text-white" : "text-slate-900")}>
        {value}
      </div>
      {sub && <div className={cn("mt-1 text-xs", themeClass ? "text-white/80" : "text-slate-400")}>{sub}</div>}
    </div>
  );
}
