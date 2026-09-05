/** classNames 合并工具 */
export function cn(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(" ");
}

/** 数值格式化：空/NaN 显示 '-' */
export function fmt(value: number | undefined | null, digits = 1): string {
  if (value === undefined || value === null || !Number.isFinite(value)) return "-";
  return value.toFixed(digits);
}

/** 每日等权 AQI 序列的日期转短标签 */
export function shortDate(date: string): string {
  return date.slice(5); // YYYY-MM-DD -> MM-DD
}
