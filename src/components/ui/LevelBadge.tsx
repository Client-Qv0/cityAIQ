import { cn } from "@/lib/utils";

/** 等级徽章（AQI 国标色） */
export function LevelBadge({ text, color, small }: { text: string; color: string; small?: boolean }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full font-medium text-white",
        small ? "px-2 py-0.5 text-xs" : "px-3 py-1 text-sm"
      )}
      style={{ backgroundColor: color }}
    >
      {text}
    </span>
  );
}
