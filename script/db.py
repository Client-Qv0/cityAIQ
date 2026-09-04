"""SQLite 连接与建表管理

三张表：
    provinces      省份信息（get_provice_info 接口的返回值）
    cities         省份下的地市级信息（get_city_info 接口的返回值，格式参考 city.json）
    city_day_aqi   某城市近 14 日 AQI 数据（get_city_day_AQI 接口的返回值，限 14 条/城市）
"""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "prisma" / "weather.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS provinces (
    Id           INTEGER PRIMARY KEY,
    ProvinceCode INTEGER UNIQUE NOT NULL,
    ProvinceJC   TEXT,
    ProvinceName TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cities (
    Id         INTEGER PRIMARY KEY,
    CityCode   INTEGER UNIQUE NOT NULL,
    CityName   TEXT NOT NULL,
    ProvinceId INTEGER NOT NULL REFERENCES provinces(Id),
    CityJC     TEXT
);

CREATE TABLE IF NOT EXISTS city_day_aqi (
    Id               INTEGER PRIMARY KEY,  -- 接口 Id
    CityCode         INTEGER NOT NULL REFERENCES cities(CityCode),
    DateTime         TEXT NOT NULL,        -- 毫秒时间戳换算的可读时间 'YYYY-MM-DD HH:MM:SS'（东八区）
    TimePoint        INTEGER,              -- 原始毫秒时间戳，如 1787932800000
    TimePointStr     TEXT,                 -- 原始 '02日' 字符串
    Area             TEXT,
    SO2_24h          REAL,
    CO_24h           REAL,
    NO2_24h          REAL,
    O3_8h_24h        REAL,
    PM10_24h         REAL,
    PM2_5_24h        REAL,
    AQI              REAL,
    PrimaryPollutant TEXT,
    Quality          TEXT,
    Measure          TEXT,
    Unheathful       TEXT,                 -- 保留接口原始拼写
    UNIQUE (CityCode, DateTime)            -- 同一城市同一时刻只保留一条
);
"""


@contextmanager
def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(SCHEMA)
        yield conn
    finally:
        conn.close()
