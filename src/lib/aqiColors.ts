/** HJ 633 空气质量等级与国标色板 */

export const QualityLevels = ["优", "良", "轻度污染", "中度污染", "重度污染", "严重污染"];

export const LevelColors = ["#00e400", "#f6ec20", "#ff7e00", "#ff0000", "#8f083a", "#7e0023"];

const BREAKS = [0, 50, 100, 150, 200, 300, Infinity];

export function levelIndex(aqi: number): number {
  for (let i = 0; i < BREAKS.length - 1; i++) {
    if (aqi >= BREAKS[i] && aqi < BREAKS[i + 1]) return i;
  }
  return 5;
}

export function qualityOf(aqi: number): string {
  return QualityLevels[levelIndex(aqi)];
}

export function colorOf(aqi: number): string {
  return LevelColors[levelIndex(aqi)];
}
