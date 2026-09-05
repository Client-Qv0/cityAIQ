"""读取 prisma/weather.db 为 pandas DataFrame（分析模块唯一数据来源）

每次运行直接读库，不缓存；getAQI.py 刷新后重跑即得最新数据。
"""
import sys
from pathlib import Path

import pandas as pd
import sqlite3

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db import DB_PATH

_AQI_COLS = ['SO2_24h', 'CO_24h', 'NO2_24h', 'O3_8h_24h', 'PM10_24h', 'PM2_5_24h']


def _connect():
    return sqlite3.connect(DB_PATH)


def load_cities_df():
    """cities JOIN provinces，返回行政区划清单（前端城市下拉框数据源）"""
    with _connect() as conn:
        return pd.read_sql_query(
            "SELECT c.CityCode, c.CityName, p.ProvinceName "
            "FROM cities c JOIN provinces p ON c.ProvinceId = p.Id "
            "ORDER BY p.ProvinceCode, c.CityCode",
            conn,
        )


def load_aqi_df():
    """city_day_aqi JOIN cities JOIN provinces 的宽表

    列：CityCode CityName ProvinceName DateTime + 6 项浓度 + AQI + Quality +
        PrimaryPollutant；DateTime 已截断为 YYYY-MM-DD（天粒度）
    """
    with _connect() as conn:
        df = pd.read_sql_query(
            "SELECT a.CityCode, c.CityName, p.ProvinceName, a.DateTime, "
            + ", ".join(f"a.{col}" for col in _AQI_COLS)
            + ", a.AQI, a.Quality, a.PrimaryPollutant "
            "FROM city_day_aqi a "
            "JOIN cities c ON a.CityCode = c.CityCode "
            "JOIN provinces p ON c.ProvinceId = p.Id",
            conn,
        )
    df['DateTime'] = pd.to_datetime(df['DateTime']).dt.strftime('%Y-%m-%d')
    return df
