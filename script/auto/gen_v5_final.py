# -*- coding: utf-8 -*-
"""T5 最终版生成：V5 评估页测试2 数值 = 读 T4 结果（无关文件/预测准确性评估.md）动态注入
由 check_and_retry.py 在 T4 成功后自动调用；也可手动运行。"""
import re
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

ROOT = Path(r'F:\_Qv0\opencode\软件开发实践课')
SRC = ROOT / '答辩PPT_V2_九页版.pptx'
OUT = ROOT / '答辩PPT_V5_最终版.pptx'
REPORT = ROOT / '无关文件' / '预测准确性评估.md'

NAVY = RGBColor(0x17, 0x37, 0x5E)
BLUE = RGBColor(0x2E, 0x74, 0xB5)
GRAY = RGBColor(0x59, 0x59, 0x59)
LGRAY = RGBColor(0xE7, 0xE6, 0xE6)
GREEN = RGBColor(0x38, 0x76, 0x1D)


def add_txt(slide, l, t, w, h, text, size=14, bold=False, color=GRAY, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
    tb = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    for i, line in enumerate(text.split('\n')):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        r = p.add_run()
        r.text = line
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.color.rgb = color
        r.font.name = '微软雅黑'
    return tb


def add_card(slide, l, t, w, h, head, body, head_color=BLUE, fill=RGBColor(0xF2, 0xF2, 0xF2)):
    sh = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(l), Inches(t), Inches(w), Inches(h))
    sh.fill.solid()
    sh.fill.fore_color.rgb = fill
    sh.line.color.rgb = LGRAY
    sh.line.width = Pt(0.75)
    tf = sh.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.12)
    tf.margin_right = Inches(0.12)
    tf.margin_top = Inches(0.08)
    p = tf.paragraphs[0]
    r = p.add_run(); r.text = head
    r.font.size = Pt(14); r.font.bold = True; r.font.color.rgb = head_color; r.font.name = '微软雅黑'
    for line in body.split('\n'):
        p2 = tf.add_paragraph()
        r2 = p2.add_run(); r2.text = line
        r2.font.size = Pt(11); r2.font.color.rgb = GRAY; r2.font.name = '微软雅黑'
    return sh


def header(slide, en, cn, sub):
    add_txt(slide, 0.5, 0.35, 12.3, 0.3, en, size=12, bold=True, color=BLUE)
    add_txt(slide, 0.5, 0.62, 12.3, 0.5, cn, size=22, bold=True, color=NAVY)
    add_txt(slide, 0.5, 1.18, 12.3, 0.6, sub, size=12, color=GRAY)


def read_t2_metrics():
    """从预测准确性评估.md 提取测试2（T4）指标，未完成则返回 None"""
    if not REPORT.exists():
        return None
    txt = REPORT.read_text(encoding='utf-8')
    m = re.search(r'## 测试 2（T4 第二次对比）([\s\S]*?)(?=\n##|\Z)', txt)
    if not m:
        return None
    block = m.group(1)
    got = lambda key: (re.search(rf'{key}[：:]\s*\*\*([^*]+)\*\*', block).group(1)
                       if re.search(rf'{key}[：:]\s*\*\*([^*]+)\*\*', block) else '-')
    cnt = re.search(r'可对比城市[：:]\s*\*\*([^*]+)\*\*', block)
    return {
        'mae': got('MAE'),
        'mape': got('MAPE'),
        'n': cnt.group(1) if cnt else '-',
    }


def build():
    prs = Presentation(SRC)
    blank = prs.slide_layouts[6]
    m = read_t2_metrics()

    # ---- 页 A：数据自动化（同 V5 初版） ----
    sa = prs.slides.add_slide(blank)
    header(sa, 'DATA AUTOMATION', '数据自动化更新', '网站启动瞬间 + 凌晨 01:00~01:30 双重触发；先查新鲜度，最新则跳过')
    add_card(sa, 0.5, 2.0, 4.0, 2.6, '① 启动瞬间触发',
             'npm run dev / build / start\n→ predev / prestart / prebuild\n→ update_daily.py --once\n立即检查并更新一次，随后退出')
    add_card(sa, 4.65, 2.0, 4.0, 2.6, '② 凌晨定时触发（长期运行）',
             'Windows 计划任务（每日）\nCityAQI-DailyUpdate 01:20\nCityAQI-ChangeCheck  01:40\n数据自动迭代更新')
    add_card(sa, 8.8, 2.0, 4.0, 2.6, '③ 新鲜度检查（跳过机制）',
             '检查库：MAX(DateTime).date()==今天\n是 → 记录 already_fresh 跳过\n否 → 更新链：getAQI 全量爬取\n→ analysis.main.run() 分析与预测')
    add_txt(sa, 0.5, 4.9, 12.3, 0.4, '更新链与状态记录', size=14, bold=True, color=NAVY)
    add_card(sa, 0.5, 5.35, 12.3, 1.5, '',
             '爬取：req/getAQI.py sync_all_city_day_aqi()（338 城，限速 sleep 1.5~3s）→ 分析：analysis.main.run() 统计+预测+污染物分析\n'
             '状态：script/auto/auto_status.json + auto_update.log；前端/API 无需改动，每次请求实时读库')

    # ---- 页 B：预测准确性评估（测试2 数值动态注入） ----
    sb = prs.slides.add_slide(blank)
    header(sb, 'PREDICTION EVALUATION', '最小二乘预测准确性评估', '留一验证 + 前向验证双测试；指标来源：script/auto/compare_prediction.py')
    add_card(sb, 0.5, 2.0, 6.1, 3.2, '测试 1 · 留一验证（338 城）',
             '方法：前 13 天拟合 → 预测第 14 天，与实际对比\n'
             'MAE（平均绝对误差）：18.07 AQI\nMAPE（平均相对误差）：26.18%\n'
             'Pearson r（预测 vs 实际）：0.726\n|误差|≤10 城市占比：37.9%\n平均偏差 bias：-7.62（整体略低估）',
             head_color=NAVY)
    if m:
        t2_body = (f'方法：完整 14 天拟合 → 记录下一天（09-06）预测值\n'
                   f'现已与凌晨更新后的实际值对比：可对比 **{m["n"]}** 城\n'
                   f'MAE：**{m["mae"]}** AQI\nMAPE：**{m["mape"]}%**\n'
                   f'结论与测试 1 交叉校验，详见无关文件/预测准确性评估.md')
    else:
        t2_body = ('方法：完整 14 天拟合 → 记录下一天（09-06）预测值\n'
                   '→ 凌晨数据自动更新后与实际对比\n'
                   '预测记录：无关文件/预测_下一天_记录.json\n'
                   '自动对比链路：01:40 check_and_retry.py\n→ compare_prediction.py --mode t4（数值待更新后回填）')
    add_card(sb, 6.85, 2.0, 6.0, 3.2, '测试 2 · 前向验证（338 城）', t2_body, head_color=NAVY)
    add_card(sb, 0.5, 5.45, 12.3, 1.5, '误差特征与解释',
             '单日 AQI 波动主要由气象驱动，仅 14 日样本的统计外推误差较大，适合反映短期趋势；'
             '区域聚合（全国/省等权）序列波动小、预测更稳（全国 r²≈0.46）；建议报告中标注"仅供参考"。',
             head_color=GREEN)

    # ---- 重排：目标顺序 ----
    def texts(s):
        out = []
        for sh in s.shapes:
            if sh.has_text_frame:
                out.append(sh.text_frame.text)
        return '\n'.join(out)

    lst = prs.slides._sldIdLst
    els = list(lst)
    by_id = {str(e.get('id')): e for e in els}
    markers = ['城市空气污染数据检测', 'PROJECT BACKGROUND', 'Tech Stack', '数据自动化更新',
               'Project Scope', 'DATA ACQUISITION', 'DATA PIPELINE', 'Multi-Dimensional',
               'Data Visualization', '最小二乘预测准确性评估', 'Team Structure']
    used = set()
    order = []
    for mkr in markers:
        for s in prs.slides:
            k = str(s.slide_id)
            if k in used:
                continue
            if mkr in texts(s):
                used.add(k)
                order.append(by_id[k])
                break
    for e in list(lst):
        lst.remove(e)
    for e in order:
        lst.append(e)
    prs.save(OUT)
    print('saved:', OUT, '| slides:', len(prs.slides), '| t2 metrics:', m)


if __name__ == '__main__':
    build()
