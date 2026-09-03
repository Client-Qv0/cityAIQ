import json
import requests


with open("./api/city.json", "r", encoding="utf-8") as f:
    city_data = json.load(f)

def get_city_day_AQI(city_code):
    """
        获取最近13天内，城市AQI数据，保存为json，返回list
        :param city_code: 城市编码
        :return: class `list` object
        :列表成员:
        {
        'AQI': '117', --> str
        'Area': '太原市', --> str
        'CO_24h': '0.7', --> str
        'CityCode': 140100, --> int
        'Id': 1763814, --> int
        'Measure': '青少年儿童、老年人及心血管系统疾病、呼吸系统疾病患者应减少长时间、高强度的户外锻炼', --> str
        'NO2_24h': '18', --> str
        'O3_8h_24h': '178', --> str
        'PM10_24h': '47', --> str
        'PM2_5_24h': '24', --> str
        'PrimaryPollutant': '臭氧8小时(O3_8h)', --> str
        'Quality': '轻度污染', --> str
        'SO2_24h': '12', --> str
        'TimePoint': '/Date(1788278400000)/', --> str
        'TimePointStr': '02日', --> str
        'Unheathful': '敏感人群症状有轻度加剧，健康人群出现刺激症状' --> str
        } 
    """

    headers = {
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        # 'Content-Length': '0',
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

    params = {
        'citycode': city_code,
    }

    response = requests.post(
        'https://air.cnemc.cn:18007/HourChangesPublish/GetCityDayAqiHistoryByCondition',
        params=params,
        headers=headers,
    )

    return response.json()

# import pprint

# pprint.pprint(get_city_AQI("140100"))