import Link from "next/link";

export function Breadcrumb({ items }: { items: { label: string; href?: string }[] }) {
  return (
    <nav className="mb-4 text-sm text-slate-500">
      {items.map((it, i) => (
        <span key={i}>
          {i > 0 && <span className="mx-2 text-slate-300">/</span>}
          {it.href ? (
            <Link href={it.href} className="hover:text-slate-900 hover:underline">
              {it.label}
            </Link>
          ) : (
            <span className="text-slate-900 font-medium">{it.label}</span>
          )}
        </span>
      ))}
    </nav>
  );
}
