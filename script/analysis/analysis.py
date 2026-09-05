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
