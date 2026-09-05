/** 最小二乘线性外推预测（与 script/analysis/predict.py 同公式）
 *
 * 模型：y = a + b·t，t = 0..n-1，预测 t = n；
 * 区间：pred ± t(0.975, n-2)·s·sqrt(1 + 1/n + (t_n−t̄)²/Sxx)
 */

const T_VALUE: Record<number, number> = {
  5: 2.571,
  6: 2.447,
  7: 2.365,
  8: 2.306,
  9: 2.262,
  10: 2.228,
  11: 2.201,
  12: 2.179,
};

export interface PredictResult {
  predicted: number;
  lower95: number;
  upper95: number;
  slope: number;
  intercept: number;
  r2: number;
  n_points: number;
}

export function predictNext(ys: number[], minPoints = 5): PredictResult {
  const y = ys.map(Number);
  if (y.length < minPoints) {
    throw new Error(`数据点不足（${y.length} < ${minPoints}），无法拟合`);
  }
  if (y.some((v) => !Number.isFinite(v))) {
    throw new Error("序列包含空值或无穷值");
  }

  const n = y.length;
  const t = Array.from({ length: n }, (_, i) => i);
  const tBar = t.reduce((a, b) => a + b, 0) / n;
  const yBar = y.reduce((a, b) => a + b, 0) / n;
  const sxx = t.reduce((s, ti) => s + (ti - tBar) ** 2, 0);
  const sxy = t.reduce((s, ti, i) => s + (ti - tBar) * (y[i] - yBar), 0);
  const slope = sxy / sxx;
  const intercept = yBar - slope * tBar;

  const sse = t.reduce((s, ti, i) => s + (y[i] - (intercept + slope * ti)) ** 2, 0);
  const sst = y.reduce((s, vi) => s + (vi - yBar) ** 2, 0);
  const r2 = sst > 0 ? 1 - sse / sst : 1;

  const df = n - 2;
  const stderr = Math.sqrt(sse / df);
  const tval = T_VALUE[df] ?? 1.96;
  const tNext = n;
  const sePred = stderr * Math.sqrt(1 + 1 / n + ((tNext - tBar) ** 2) / sxx);
  const predicted = intercept + slope * tNext;

  return {
    predicted,
    lower95: predicted - tval * sePred,
    upper95: predicted + tval * sePred,
    slope,
    intercept,
    r2,
    n_points: n,
  };
}
