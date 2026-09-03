import requests
import time
import json


def get_provide_info():
    """
    获取省份信息，保存为json，返回列表
    :return: class `list` object：
    :member:{'Id': 1, 'ProvinceCode': 110000, 'ProvinceJC': 'BJ', 'ProvinceName': '北京'}
    """
    headers = {
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

    response = requests.get('https://air.cnemc.cn:18007/CityData/GetProvince', headers=headers)
    return response.json()


def get_city_info(province_code):
    """
    获取城市信息，保存为json，返回list
    :param province_code: 省份编码list
    :return: class `list` object：
    :列表成员:{Id: 20, CityCode: 150100, CityName: "呼和浩特市", ProvinceId: 5, CityJC: "HHHTS"}
    """
    headers = {
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

    data = []

    for province in province_code:
        time.sleep(3)  # Add a delay of 3 seconds between requests to avoid overwhelming the server
        params = {
            'pid': province['Id'],
        }

        response = requests.get('https://air.cnemc.cn:18007/CityData/GetCitiesByPid', params=params, headers=headers)
        province["cities"] = response.json()
        data.append(province)
    data = json.dumps(data, ensure_ascii=False, indent=4)
    return data

# if __name__ == "__main__":
#     province_info = get_provide_info()
#     city_info = get_city_info(province_info)
#     with open('city_info.json', 'w', encoding='utf-8') as f:
#         f.write(city_info)