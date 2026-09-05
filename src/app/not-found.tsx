import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <div className="text-6xl font-bold text-slate-200">404</div>
      <p className="mt-4 text-slate-500">未找到该页面（省份简称或城市编码不存在 / 级别不匹配）</p>
      <Link href="/" className="mt-6 rounded-lg bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700">
        返回首页
      </Link>
    </div>
  );
}
