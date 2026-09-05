"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { NavProvince } from "@/lib/queries";
import { cn } from "@/lib/utils";

function matchText(text: string, q: string): boolean {
  return text.toLowerCase().includes(q.toLowerCase());
}

/** 左侧导航侧边栏：省（一级 / 可展开）→ 城市（二级），支持搜索（名称/拼音简称/编码） */
export function Sidebar({ tree }: { tree: NavProvince[] }) {
  const pathname = usePathname();
  const segs = pathname.split("/").filter(Boolean);
  const curProvince = segs[0] ?? "";
  const curCity = segs[1] ?? "";

  const [q, setQ] = useState("");
  const [expanded, setExpanded] = useState<Set<string>>(() =>
    new Set(curProvince ? [curProvince] : [])
  );

  const searching = q.trim().length > 0;

  // 搜索命中；省份命中则其全部城市通过；城市命中则仅保留命中城市
  const visible = useMemo(() => {
    const list: NavProvince[] = [];
    for (const p of tree) {
      if (!searching) {
        list.push(p);
        continue;
      }
      const provinceHit = matchText(p.ProvinceName, q) || matchText(p.ProvinceJC, q);
      const cities = p.cities.filter(
        (c) => matchText(c.CityName, q) || matchText(c.CityJC, q) || matchText(String(c.CityCode), q)
      );
      if (provinceHit) list.push({ ...p, cities: p.cities });
      else if (cities.length > 0) list.push({ ...p, cities });
    }
    return list;
  }, [tree, q, searching]);

  const toggle = (jc: string) => {
    if (searching) return;
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(jc)) next.delete(jc);
      else next.add(jc);
      return next;
    });
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-3">
      {/* 搜索框 */}
      <input
        type="text"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="搜索省/城市（名称、拼音、编码）"
        className="w-full rounded-md border border-slate-300 px-3 py-1.5 text-sm outline-none focus:border-blue-500"
      />
      <div className="mt-2 max-h-[calc(100vh-13rem)] overflow-y-auto pr-1">
        {searching && visible.length === 0 && (
          <div className="px-2 py-4 text-center text-xs text-slate-400">无匹配结果</div>
        )}
        <ul className="space-y-0.5 text-sm">
          {visible.map((p) => {
            const isOpen = searching || expanded.has(p.ProvinceJC);
            return (
              <li key={p.ProvinceJC}>
                {/* 一级：省份 */}
                <div className="flex items-center">
                  <button
                    onClick={() => toggle(p.ProvinceJC)}
                    className="mr-1 grid h-5 w-5 place-items-center rounded text-slate-400 hover:text-slate-700"
                    aria-label="展开/收起"
                  >
                    <span
                      className={cn(
                        "inline-block transition-transform",
                        isOpen ? "rotate-90" : "rotate-0"
                      )}
                    >
                      ▸
                    </span>
                  </button>
                  <Link
                    href={`/${p.ProvinceJC}`}
                    className={cn(
                      "flex-1 rounded-md px-2 py-1 font-medium hover:bg-slate-100",
                      p.ProvinceJC === curProvince
                        ? "bg-blue-50 text-blue-700"
                        : "text-slate-700"
                    )}
                  >
                    {p.ProvinceName}
                    <span className="ml-1 text-xs font-normal text-slate-400">
                      ({p.cities.length})
                    </span>
                  </Link>
                </div>
                {/* 二级：城市（仅展开/搜索时渲染，控制 DOM 数量） */}
                {isOpen && p.cities.length > 0 && (
                  <ul className="ml-4 border-l border-slate-200 pl-2">
                    {p.cities.map((c) => {
                      const active = p.ProvinceJC === curProvince && String(c.CityCode) === curCity;
                      return (
                        <li key={c.CityCode}>
                          <Link
                            href={`/${p.ProvinceJC}/${c.CityCode}`}
                            className={cn(
                              "block rounded-md px-2 py-1 hover:bg-slate-100",
                              active ? "bg-blue-50 text-blue-700" : "text-slate-600"
                            )}
                          >
                            {c.CityName.replace(/市|自治州|地区|盟|自治县|县$/, "")}
                          </Link>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
