"""AQI 最小二乘预测：线性趋势外推 + 95% 预测区间

模型：AQI(t) = intercept + slope * t，t = 0..n-1；预测 t = n。
区间公式：pred ± t(0.975, n-2) * s * sqrt(1 + 1/n + (t_n-t_bar)^2/Sxx)
"""
import math

import numpy as np
import pandas as pd

# t 分布双侧 0.975 分位数表（df = n-2 ∈ 1..12），其余 df 用 1.96 近似
_T_VALUE = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571,
            6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
            11: 2.201, 12: 2.179}


def predict_next_aqi(aqi_series, min_points=5):
    """对一维 AQI 序列做最小二乘线性外推，预测下一天值

    :param aqi_series: pd.Series / list，长度 >= min_points，不允许空值
    :return: dict:
        predicted 下一天 AQI 预测值
        lower95/upper95 95% 预测区间
        slope/intercept 拟合系数
        r2 决定系数
        stderr 残差标准误差
    """
    y = pd.Series(aqi_series).astype(float).reset_index(drop=True)
    if len(y) < min_points:
        raise ValueError(f'数据点不足（{len(y)} < {min_points}），无法拟合')
    if y.isna().any() or np.isinf(y).any():
        raise ValueError('AQI 序列包含空值或无穷值')

    n = len(y)
    t = np.arange(n, dtype=float)
    t_bar = t.mean()
    y_bar = y.mean()
    sxx = ((t - t_bar) ** 2).sum()
    sxy = ((t - t_bar) * (y - y_bar)).sum()
    slope = sxy / sxx
    intercept = y_bar - slope * t_bar

    y_fit = intercept + slope * t
    sse = ((y - y_fit) ** 2).sum()
    sst = ((y - y_bar) ** 2).sum()
    r2 = 1 - sse / sst if sst > 0 else 1.0
    stderr = math.sqrt(sse / (n - 2)) if n > 2 else float('nan')

    df = n - 2
    tval = _T_VALUE.get(df, 1.96)
    t_next = float(n)  # 序号 n 即明天
    se_pred = stderr * math.sqrt(1 + 1 / n + (t_next - t_bar) ** 2 / sxx)
    predicted = intercept + slope * t_next

    return {
        'predicted': float(predicted),
        'lower95': float(predicted - tval * se_pred),
        'upper95': float(predicted + tval * se_pred),
        'slope': float(slope),
        'intercept': float(intercept),
        'r2': float(r2),
        'stderr': float(stderr),
        'n_points': int(n),
    }
