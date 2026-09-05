import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";
import { qNavTree } from "@/lib/queries";

export const metadata: Metadata = {
  title: "城市空气质量数据可视化",
  description: "基于中国环境监测总站数据的城市空气质量数据分析与可视化",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const tree = qNavTree();
  return (
    <html lang="zh-CN">
      <body>
        <header className="bg-white border-b border-slate-200">
          <div className="mx-auto max-w-7xl px-4 py-3 flex items-center justify-between">
            <Link href="/" className="font-bold text-lg text-slate-900">
              城市空气质量数据可视化
            </Link>
            <span className="text-sm text-slate-500">
              数据源：中国环境监测总站 · 近 14 日滚动
            </span>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-6 flex flex-col md:flex-row gap-6">
          <aside className="md:w-64 shrink-0 md:sticky md:top-6 md:max-h-[calc(100vh-4rem)] md:self-start md:overflow-hidden">
            <Sidebar tree={tree} />
          </aside>
          <div className="flex-1 min-w-0">{children}</div>
        </main>
        <footer className="mx-auto max-w-7xl px-4 py-6 text-center text-xs text-slate-400">
          课程项目：城市天气质量的数据检测分析与可视化
        </footer>
      </body>
    </html>
  );
}
