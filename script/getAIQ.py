"""城市近 14 日 AQI 数据：爬取接口并覆盖写入 SQLite（city_day_aqi 表）

用法：
    1. 数据入库：sync_city_day_aqi(city_code) / sync_all_city_day_aqi()
    2. 数据读取（返回 list[dict]）：get_city_day_AQI(city_code)
"""
import random
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import get_conn

HEADERS = {
    'Accept': '*/*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Origin': 'https://air.cnemc.cn:18007',
    'Pragma': 'no-cache',
    'Referer': 'https://air.cnemc.cn:18007/',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36 Edg/152.0.0.0',
    'X-Requested-With': 'XMLHttpRequest',
    'sec-ch-ua': '"Chromium";v="152", "Not?A_Brand";v="24", "Microsoft Edge";v="152"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}

_COLUMNS = ['Id', 'CityCode', 'DateTime', 'TimePoint', 'TimePointStr', 'Area',
            'SO2_24h', 'CO_24h', 'NO2_24h', 'O3_8h_24h', 'PM10_24h', 'PM2_5_24h',
            'AQI', 'PrimaryPollutant', 'Quality', 'Measure', 'Unheathful']

BEIJING_TZ = timezone(timedelta(hours=8))


def _to_ms(time_point):
    """'/Date(1787241600000)/' -> 1787241600000"""
    return int(time_point.split('(')[1].split(')')[0])


def _ms_to_str(ms):
    """毫秒时间戳 -> 'YYYY-MM-DD HH:MM:SS'（东八区）"""
    return datetime.fromtimestamp(ms / 1000, tz=BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')


def _to_float(value):
    """接口中的浓度/AQI 为字符串，空值或 '-' 记为 NULL"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def sync_city_day_aqi(city_code):
    """
    爬取某城市近 14 日 AQI 数据，覆盖写入 city_day_aqi 表
    （先删除该城市旧记录再插入，保证库中每城市仅保留最近一次爬取的 14 条）
    :param city_code: 城市编码，如 '140100'
    :return: 入库后从表里读出的 list[dict]
    """
    city_code = int(city_code)
    response = requests.post(
        'https://air.cnemc.cn:18007/HourChangesPublish/GetCityDayAqiHistoryByCondition',
        params={'citycode': city_code},
        headers=HEADERS,
    )
    data = response.json()
    if not data:
        print(f'城市 {city_code} 的 AQI 接口返回为空，保留库中旧数据')
        return get_city_day_AQI(city_code)
    # 接口返回约 14 条，按需求截断为最近 14 日
    data = sorted(data, key=lambda item: _to_ms(item['TimePoint']))[-14:]

    records = []
    for item in data:
        ms = _to_ms(item['TimePoint'])
        records.append({
            'Id': item['Id'],
            'CityCode': city_code,
            'DateTime': _ms_to_str(ms),
            'TimePoint': ms,
            'TimePointStr': item['TimePointStr'],
            'Area': item['Area'],
            'SO2_24h': _to_float(item['SO2_24h']),
            'CO_24h': _to_float(item['CO_24h']),
            'NO2_24h': _to_float(item['NO2_24h']),
            'O3_8h_24h': _to_float(item['O3_8h_24h']),
            'PM10_24h': _to_float(item['PM10_24h']),
            'PM2_5_24h': _to_float(item['PM2_5_24h']),
            'AQI': _to_float(item['AQI']),
            'PrimaryPollutant': item['PrimaryPollutant'],
            'Quality': item['Quality'],
            'Measure': item['Measure'],
            'Unheathful': item['Unheathful'],
        })

    with get_conn() as conn:
        conn.execute('DELETE FROM city_day_aqi WHERE CityCode = ?', (city_code,))
        conn.executemany(
            f"INSERT OR REPLACE INTO city_day_aqi ({', '.join(_COLUMNS)}) "
            f"VALUES ({', '.join(':' + c for c in _COLUMNS)})",
            records,
        )
        conn.commit()
    return get_city_day_AQI(city_code)


def sync_all_city_day_aqi():
    """同步 cities 表中所有城市的近 14 日数据，每个请求之间 sleep(1.5~3) 秒"""
    with get_conn() as conn:
        codes = [r['CityCode'] for r in conn.execute('SELECT CityCode FROM cities ORDER BY CityCode')]
    if not codes:
        raise RuntimeError('cities 表为空，请先执行 getdata.sync_all_cities()')
    failed = []
    for i, code in enumerate(codes):
        if i > 0:
            time.sleep(random.uniform(1.5, 3))
        try:
            rows = sync_city_day_aqi(code)
            if rows:
                print(f"已同步 {rows[0]['Area']}({code})，{len(rows)} 条")
            else:
                print(f"城市 {code} 无数据（接口返回为空且库中无旧数据）")
        except Exception as e:
            failed.append(code)
            print(f"同步 {code} 失败: {e!r}")
    if failed:
        print(f"失败城市 {len(failed)} 个: {failed}")


def get_city_day_AQI(city_code):
    """
    从 city_day_aqi 表读取某城市近 14 日 AQI 数据（按时间升序）
    :param city_code: 城市编码
    :return: class `list` object：
    :列表成员:{'Id': ..., 'CityCode': ..., 'DateTime': '2026-08-29 00:00:00',
              'TimePoint': 1787932800000, 'TimePointStr': ...,
              'Area': ..., 'SO2_24h': ..., ..., 'AQI': ..., 'PrimaryPollutant': ..., 'Quality': ...,
              'Measure': ..., 'Unheathful': ...}（浓度与 AQI 存为 REAL，缺失为 None）
    """
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT {', '.join(_COLUMNS)} FROM city_day_aqi WHERE CityCode = ? ORDER BY DateTime",
            (int(city_code),),
        ).fetchall()
    return [dict(r) for r in rows]


if __name__ == '__main__':
    # 直接运行本文件 = 爬取 cities 表中所有城市的近 14 日数据（约 338 城，15~20 分钟）
    sync_all_city_day_aqi()
