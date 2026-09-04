"""省份 / 地市级数据：爬取接口并写入 SQLite（provinces、cities 两张表）

用法：
    1. 数据入库：sync_provinces() / sync_cities(pid) / sync_all_cities()
    2. 数据读取（返回结构与原接口一致的 list[dict]）：
       get_provice_info()            -> 表1 省份信息
       get_city_info(province_id)    -> 表2 某省下的地市级信息
"""
import random
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import get_conn

HEADERS = {
    'Accept': '*/*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
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


def sync_provinces():
    """爬取省份信息并写入 provinces 表（按主键覆盖），返回入库后的省份列表"""
    response = requests.get('https://air.cnemc.cn:18007/CityData/GetProvince', headers=HEADERS)
    data = response.json()
    if not data:
        raise RuntimeError('省份接口返回为空，跳过写入')

    with get_conn() as conn:
        conn.executemany(
            'INSERT OR REPLACE INTO provinces (Id, ProvinceCode, ProvinceJC, ProvinceName) '
            'VALUES (:Id, :ProvinceCode, :ProvinceJC, :ProvinceName)',
            data,
        )
        conn.commit()
    return get_provice_info()


def get_provice_info():
    """
    从 provinces 表读取省份信息
    :return: class `list` object：
    :member:{'Id': 1, 'ProvinceCode': 110000, 'ProvinceJC': 'BJ', 'ProvinceName': '北京'}
    """
    with get_conn() as conn:
        rows = conn.execute(
            'SELECT Id, ProvinceCode, ProvinceJC, ProvinceName FROM provinces ORDER BY ProvinceCode'
        ).fetchall()
    return [dict(r) for r in rows]


def sync_cities(province_id):
    """爬取某省的地市级信息并覆盖写入 cities 表（先删该省旧记录再插入），返回该省城市列表"""
    response = requests.get(
        'https://air.cnemc.cn:18007/CityData/GetCitiesByPid',
        params={'pid': province_id},
        headers=HEADERS,
    )
    data = response.json()
    with get_conn() as conn:
        conn.execute('DELETE FROM cities WHERE ProvinceId = ?', (province_id,))
        if data:
            conn.executemany(
                'INSERT OR REPLACE INTO cities (Id, CityCode, CityName, ProvinceId, CityJC) '
                'VALUES (:Id, :CityCode, :CityName, :ProvinceId, :CityJC)',
                data,
            )
        else:
            print(f'省份 {province_id} 城市接口返回为空（台/港/澳无监测城市）')
        conn.commit()
    return get_city_info(province_id)


def sync_all_cities():
    """逐个省份同步地市级信息，每个请求之间 sleep(1.5~3) 秒"""
    provinces = get_provice_info()
    if not provinces:
        raise RuntimeError('provinces 表为空，请先执行 sync_provinces()')
    failed = []
    for i, p in enumerate(provinces):
        if i > 0:
            time.sleep(random.uniform(1.5, 3))
        try:
            n = len(sync_cities(p['Id']))
            print(f"已同步 {p['ProvinceName']}（{n} 个城市）")
        except Exception as e:
            failed.append(p['ProvinceName'])
            print(f"同步 {p['ProvinceName']} 失败: {e!r}")
    if failed:
        print(f"失败省份 {len(failed)} 个: {failed}")


def get_city_info(province_id):
    """
    从 cities 表读取某省的地市级信息
    :param province_id: 省份id（provinces 表的 Id）
    :return: class `list` object：
    :列表成员:{Id: 20, CityCode: 150100, CityName: "呼和浩特市", ProvinceId: 5, CityJC: "HHHTS"}
    """
    with get_conn() as conn:
        rows = conn.execute(
            'SELECT Id, CityCode, CityName, ProvinceId, CityJC FROM cities '
            'WHERE ProvinceId = ? ORDER BY CityCode',
            (province_id,),
        ).fetchall()
    return [dict(r) for r in rows]


if __name__ == '__main__':
    sync_provinces()
    sync_all_cities()
