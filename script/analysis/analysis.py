"""统计分析模块：描述统计、排名、等级、趋势、省份聚合、相关性

输入统一为 data_loader.load_aqi_df() 的宽表；纯函数，无副作用。
"""
import pandas as pd

METRIC_COLS = ['SO2_24h', 'CO_24h', 'NO2_24h', 'O3_8h_24h', 'PM10_24h',
               'PM2_5_24h', 'AQI']
CN_KEYS = {'SO2_24h': 'SO2', 'CO_24h': 'CO', 'NO2_24h': 'NO2',
           'O3_8h_24h': 'O3_8h', 'PM10_24h': 'PM10', 'PM2_5_24h': 'PM2.5',
           'AQI': 'AQI'}


def descriptive_summary(df):
    """7 项指标的 count/mean/std/min/分位数/max；索引用 CN_KEYS"""
    st = df[METRIC_COLS].describe(percentiles=[.25, .5, .75]).T
    st = st.rename(index=CN_KEYS)
    return st.reindex(columns=['count', 'mean', 'std', 'min',
                               '25%', '50%', '75%', 'max'])


def city_aqi_ranking(df):
    """每城 14 日 AQI 均值排名（降序前 10），含等级占比与达标天数"""
    df_ = df.copy()
    df_['is_good'] = df_['Quality'].isin(['优', '良'])
    g = df_.groupby(['CityName', 'ProvinceName']).agg(
        AQI_mean=('AQI', 'mean'), AQI_max=('AQI', 'max'),
        AQI_min=('AQI', 'min'), good_days=('is_good', 'sum'))
    return g.sort_values('AQI_mean', ascending=False).head(10).reset_index()


def quality_distribution(df):
    """AQI 等级数量统计：优/良/轻度污染/中度污染/重度污染/严重污染"""
    out = df['Quality'].value_counts().rename('count').reset_index()
    return out.rename(columns={'index': 'Quality'})


def daily_trend(df, city_code=None):
    """全国（或单城市）每日 AQI 均值趋势"""
    if city_code is not None:
        df = df[df['CityCode'] == city_code]
    return (df.groupby('DateTime')['AQI'].mean()
            .rename('AQI_mean').reset_index())


def province_summary(df):
    """各省 AQI 均值（城市等权后按省平均）、最大值与监测城市数"""
    city_mean = (df.groupby(['ProvinceName', 'CityName'])['AQI']
                 .agg(['mean', 'max'])
                 .rename(columns={'mean': 'AQI_mean', 'max': 'AQI_max'}))
    out = (city_mean.reset_index()
           .groupby('ProvinceName', as_index=False)
           .agg(AQI_mean=('AQI_mean', 'mean'),
                AQI_max=('AQI_max', 'max'),
                city_count=('CityName', 'nunique')))
    return out.sort_values('AQI_mean', ascending=False).reset_index(drop=True)


def correlation_matrix(df):
    """7 项指标皮尔逊相关矩阵（索引/列用 CN_KEYS）"""
    corr = df[METRIC_COLS].corr(method='pearson')
    corr.index = [CN_KEYS[c] for c in corr.index]
    corr.columns = [CN_KEYS[c] for c in corr.columns]
    return corr


def area_average(df, province_name=None):
    """某省（province_name）或全国（None）的 7 项指标平均（城市等权）

    计算口径：先求每座城市全部日子的指标均值，再对城市求平均——
    避免城市数量不同的省份/地区被样本数加权。7 项指标索引为 CN_KEYS。
    """
    if province_name is not None:
        df = df[df['ProvinceName'] == province_name]
    if df.empty:
        raise ValueError(f'未找到省份: {province_name}')
    city_mean = df.groupby('CityName')[METRIC_COLS].mean()
    out = city_mean.mean()
    out.index = [CN_KEYS[c] for c in out.index]
    return out


def area_daily_aqi(df, province_name=None):
    """某省/全国每日区域平均 AQI（城市等权），用于时间序列与明日预测

    每日本区域内：先城市日均，再对城市求平均，保证与 area_average 同口径。
    返回 DataFrame[DateTime, AQI]（DateTime 升序）。
    """
    if province_name is not None:
        df = df[df['ProvinceName'] == province_name]
    if df.empty:
        raise ValueError(f'未找到省份: {province_name}')
    daily = (df.groupby(['DateTime', 'CityName'])['AQI'].mean()
             .groupby('DateTime').mean())
    return daily.rename('AQI').reset_index().sort_values('DateTime')
import json

"""===== 主要污染物分析（HJ 633 IAQI 主控因子法 + 建议模板）====="""

# 国标断点：IAQI 档（第 1 个列表）↔ 浓度档（第 2 个列表），24h / O3 8h
_POLLUTANT_BREAKS = {
    'SO2_24h': ([0, 50, 100, 150, 200, 300, 500], [0, 50, 150, 475, 800, 1600, 2620]),
    'CO_24h':  ([0, 50, 100, 150, 200, 300, 500], [0, 2, 4, 14, 24, 36, 48]),
    'NO2_24h': ([0, 50, 100, 150, 200, 300, 500], [0, 40, 80, 180, 280, 565, 750]),
    'O3_8h_24h': ([0, 50, 100, 150, 200, 300], [0, 100, 160, 215, 265, 800]),
    'PM10_24h': ([0, 50, 100, 150, 200, 300, 500], [0, 50, 150, 250, 350, 420, 500]),
    'PM2_5_24h': ([0, 50, 100, 150, 200, 300, 500], [0, 35, 75, 115, 150, 250, 350]),
}

GOV_ACTIONS = {
    'PM2.5': ['加强施工扬尘与道路扬尘管控', '开展机动车排放抽检与限行', '督导涉尘企业错峰生产'],
    'PM10':  ['强化施工工地抑尘措施检查', '加大道路机械化清扫与洒水频次', '加强矿山及物料堆场覆盖管理'],
    'O3_8h': ['推进 VOC 与 NOx 协同管控', '鼓励加油站错峰卸油与夜间作业', '强化沥青涂装等挥发性工序错时施工'],
    'NO2':   ['优化交通组织并扩大公共交通运力', '严格柴油货车限行与排放检查', '加强机动车尾气遥感监测执法'],
    'SO2':   ['督促燃煤设施稳定达标排放', '推进清洁能源替代与煤改气工程', '强化工业窑炉在线监控'],
    'CO':    ['治理机动车尾气与怠速排放', '强化冬季取暖燃煤监管', '排查密闭空间与工业锅炉一氧化碳隐患'],
}

PERSONAL_ACTIONS = {
    'PM2.5': ['减少户外活动', '外出佩戴 KN95 级别口罩', '关闭门窗并开启空气净化器'],
    'PM10':  ['户外活动做好防护', '避免剧烈运动', '回家后及时清洗面部与鼻腔'],
    'O3_8h': ['午后时段减少户外停留', '通风优先选择清晨', '敏感人群避免长时间户外'],
    'NO2':   ['减少私家车出行', '避开主干道等拥堵路段', '骑行或步行时远离车流'],
    'SO2':   ['减少户外活动', '敏感人群做好呼吸防护', '居家及时关闭门窗'],
    'CO':    ['保持室内通风', '不在密闭空间使用燃油设备', '避免吸入二手烟'],
}

_GOOD_NOTE = '空气质量佳，适宜外出游玩'


def _iaqi(conc, pairs):
    """浓度 → IAQI（线性插值）；None/非有限返回 None；超出档顶按最高档 IAQI 封顶"""
    if conc is None or pd.isna(conc) or conc <= 0:
        return None
    levels, caps = pairs
    for i in range(len(levels) - 1):
        if conc <= caps[i + 1]:
            lo_c, hi_c = caps[i], caps[i + 1]
            lo_i, hi_i = levels[i], levels[i + 1]
            if hi_c == lo_c:
                return float(hi_i)
            return float(hi_i - (hi_i - lo_i) * (hi_c - conc) / (hi_c - lo_c))
    return float(levels[-1])


def _judge(day_row, threshold):
    """某一天（Series）：返回 (main_list, good, note)"""
    iaqis = {}
    for col in ['SO2_24h', 'CO_24h', 'NO2_24h', 'O3_8h_24h', 'PM10_24h', 'PM2_5_24h']:
        iaqis[col] = _iaqi(day_row[col], _POLLUTANT_BREAKS[col])
    aqi = float(day_row['AQI'])
    if aqi <= threshold:
        return [], True, _GOOD_NOTE
    values = {col: v for col, v in iaqis.items() if v is not None and v > 0}
    if not values:
        return [], True, _GOOD_NOTE
    mx = max(values.values())
    mains = [CN_KEYS[col] for col, v in values.items() if v == mx]
    return mains, False, ''


def pollutant_analysis(df, aqi_threshold=50.0):
    """每城市双粒度：最近 1 天主控因子判定（主要）+ 近 7 天频次参照（次要）

    返回 DataFrame（每城一行）：CityCode CityName DateTime AQI main_pollutant
    good note day1_gov day1_personal week7（后三个为 JSON 字符串）
    week7 = {avg_aqi, good_days, freq{污染物:次数}, dominant, good}
    """
    rows = []
    for city_code, g in df.groupby('CityCode'):
        g = g.sort_values('DateTime')
        latest = g.iloc[-1]
        mains, good, note = _judge(latest, aqi_threshold)
        day1_gov = [x for m in mains for x in GOV_ACTIONS[m]]
        day1_personal = [x for m in mains for x in PERSONAL_ACTIONS[m]]
        if not mains:
            day1_gov, day1_personal = [], []

        tail = g.tail(7)
        freq = {}
        avg_aqi = float(tail['AQI'].mean()) if len(tail) else 0.0
        good_days = 0
        for _, day in tail.iterrows():
            m, is_good, _ = _judge(day, aqi_threshold)
            if is_good:
                good_days += 1
            for x in m:
                freq[x] = freq.get(x, 0) + 1
        dominant = max(freq, key=freq.get) if freq else None
        week7 = {
            'avg_aqi': round(avg_aqi, 2),
            'good_days': int(good_days),
            'freq': freq,
            'dominant': dominant,
            'good': good_days == len(tail),
        }

        rows.append({
            'CityCode': int(city_code),
            'CityName': latest['CityName'],
            'DateTime': str(latest['DateTime']),
            'AQI': round(float(latest['AQI']), 1),
            'main_pollutant': '+'.join(mains) if mains else '-',
            'good': 1 if good else 0,
            'note': note,
            'day1_gov': json.dumps(day1_gov, ensure_ascii=False),
            'day1_personal': json.dumps(day1_personal, ensure_ascii=False),
            'week7': json.dumps(week7, ensure_ascii=False),
        })
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=[
        'CityCode', 'CityName', 'DateTime', 'AQI', 'main_pollutant',
        'good', 'note', 'day1_gov', 'day1_personal', 'week7'])
