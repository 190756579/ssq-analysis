# -*- coding: utf-8 -*-
"""双色球概率分析 - 定时任务脚本
每周一/三/五运行，自动抓取最新数据、分析概率、发送邮件到 190756579@qq.com
适配本地 Windows 和 GitHub Actions Linux 环境
"""
import json
import smtplib
import urllib.request
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from collections import Counter
import random
import os
from datetime import datetime, timezone, timedelta

# =========== SMTP 配置（优先读环境变量，本地用默认值）============
SMTP_USER = os.environ.get('SMTP_USER', '190756579@qq.com')
SMTP_PASS = os.environ.get('SMTP_PASS', 'mbvvsscxcgykbiei')
SMTP_SERVER = 'smtp.qq.com'
SMTP_PORT = 465  # SSL

REPORT_PATH = 'ssq_report.html'  # GitHub Actions 用相对路径

# =========== 1. 抓取最新开奖数据 ===========
def fetch_ssq_data():
    """从500彩票网抓取双色球近100期数据"""
    url = "http://datachart.500star.com/ssq/history/history.shtml"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("gbk", errors="ignore")
    except Exception as e:
        print(f"抓取失败: {e}")
        return None

    # 解析开奖号码 - 修正正则：期号后跟6个红球1个蓝球
    # 500彩票网格式：期号  红球1 红球2 ... 红球6  蓝球
    pattern = r'(\d{7})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})'
    matches = re.findall(pattern, html)

    data = []
    for m in matches[:100]:
        period = m[0]
        reds = [int(m[i]) for i in range(1, 7)]
        blue = int(m[7])
        data.append((period, reds, blue))

    return data

# =========== 2. 概率分析 ===========
def analyze(data):
    """分析概率，生成5组推荐号码"""
    red_counter = Counter()
    blue_counter = Counter()
    for period, reds, blue in data:
        red_counter.update(reds)
        blue_counter.update([blue])

    # 近20期
    recent = data[:20]
    recent_red = Counter()
    recent_blue = Counter()
    for period, reds, blue in recent:
        recent_red.update(reds)
        recent_blue.update([blue])

    # 综合评分
    red_scores = {}
    for num in range(1, 34):
        gf = red_counter.get(num, 0) / len(data)
        rf = recent_red.get(num, 0) / len(recent)
        red_scores[num] = gf * 0.4 + rf * 0.6

    blue_scores = {}
    for num in range(1, 17):
        gf = blue_counter.get(num, 0) / len(data)
        rf = recent_blue.get(num, 0) / len(recent)
        blue_scores[num] = gf * 0.4 + rf * 0.6

    red_ranked = sorted(red_scores.items(), key=lambda x: x[1], reverse=True)
    blue_ranked = sorted(blue_scores.items(), key=lambda x: x[1], reverse=True)

    random.seed()
    recommendations = []

    hot = [num for num, _ in red_ranked[:8]]
    warm = [num for num, _ in red_ranked[8:16]]
    cold = [num for num, _ in red_ranked[16:]]

    # 第1组：高频优先
    r1 = sorted([num for num, _ in red_ranked[:6]])
    recommendations.append(("高频优先", r1, blue_ranked[0][0]))

    # 第2组：热温混合
    pool = [num for num, _ in red_ranked[:12]]
    r2 = sorted(list(set(random.sample(pool[:7], 3) + random.sample(pool[4:12], 3))))
    while len(r2) < 6:
        r2.append(random.choice([n for n in pool if n not in r2]))
        r2 = sorted(list(set(r2)))
    recommendations.append(("热温混合", r2[:6], blue_ranked[1][0]))

    # 第3组：均衡分布
    pool_big = [num for num, _ in red_ranked[:15]]
    r3 = sorted(list(set(random.sample(pool_big[:6], 3) + random.sample(pool_big[6:12], 2) + random.sample(pool_big[12:15], 1))))
    while len(r3) < 6:
        r3.append(random.choice([n for n in pool_big if n not in r3]))
        r3 = sorted(list(set(r3)))
    recommendations.append(("均衡分布", r3[:6], blue_ranked[2][0]))

    # 第4组：冷热交替
    r4 = sorted(list(set(random.sample(hot, 3) + random.sample(warm, 3))))
    while len(r4) < 6:
        r4.append(random.choice([n for n in hot + warm if n not in r4]))
        r4 = sorted(list(set(r4)))
    recommendations.append(("冷热交替", r4[:6], blue_ranked[3][0]))

    # 第5组：趋势回补
    r5 = sorted(list(set(random.sample(hot[:5], 2) + random.sample(warm[:6], 2) + random.sample(cold[:10], 2))))
    while len(r5) < 6:
        r5.append(random.choice([n for n in hot + warm + cold if n not in r5]))
        r5 = sorted(list(set(r5)))
    recommendations.append(("趋势回补", r5[:6], blue_ranked[0][0]))

    return recommendations, red_counter, blue_counter

# =========== 3. 生成邮件内容 ===========
def build_email(recommendations, red_counter, blue_counter, data):
    """构建邮件HTML内容"""
    total = len(data)
    tz_cst = timezone(timedelta(hours=8))
    now_str = datetime.now(tz_cst).strftime('%Y-%m-%d %H:%M')

    # 红球TOP10
    red_top = red_counter.most_common(10)
    # 蓝球TOP5
    blue_top = blue_counter.most_common(5)

    html = f"""
    <html><head><meta charset="utf-8"></head><body style="font-family: 'Microsoft YaHei', sans-serif; color: #333;">
    <h2 style="color: #e74c3c;">🎱 双色球概率分析报告</h2>
    <p style="color: #888;">数据范围：近{total}期 | 分析时间：{now_str}（自动生成）</p>

    <h3 style="color: #e74c3c;">📊 5组推荐号码</h3>
    <table style="border-collapse: collapse; width: 100%; margin-bottom: 20px;">
    <tr style="background: #e74c3c; color: white;">
        <th style="padding: 8px; border: 1px solid #ddd;">组别</th>
        <th style="padding: 8px; border: 1px solid #ddd;">策略</th>
        <th style="padding: 8px; border: 1px solid #ddd;">红球</th>
        <th style="padding: 8px; border: 1px solid #ddd;">蓝球</th>
    </tr>
    """

    for i, (strategy, reds, blue) in enumerate(recommendations, 1):
        red_str = " ".join(f'<span style="background: #e74c3c; color: white; padding: 2px 6px; border-radius: 3px; margin: 2px; display: inline-block;">{x:02d}</span>' for x in reds)
        blue_html = f'<span style="background: #3498db; color: white; padding: 2px 8px; border-radius: 3px;">{blue:02d}</span>'
        bg = "#fff5f5" if i % 2 == 1 else "white"
        html += f"""
        <tr style="background: {bg};">
            <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">第{i}组</td>
            <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{strategy}</td>
            <td style="padding: 8px; border: 1px solid #ddd;">{red_str}</td>
            <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{blue_html}</td>
        </tr>
        """

    html += "</table>"

    # 红球TOP10
    html += '<h3 style="color: #e74c3c;">🔥 红球高频TOP10</h3><table style="border-collapse: collapse; margin-bottom: 20px;">'
    html += '<tr style="background: #e74c3c; color: white;"><th style="padding: 6px 12px; border: 1px solid #ddd;">号码</th><th style="padding: 6px 12px; border: 1px solid #ddd;">次数</th><th style="padding: 6px 12px; border: 1px solid #ddd;">频率</th></tr>'
    for num, count in red_top:
        freq = count / total * 100
        html += f'<tr><td style="padding: 6px 12px; border: 1px solid #ddd; text-align: center;">{num:02d}</td><td style="padding: 6px 12px; border: 1px solid #ddd; text-align: center;">{count}</td><td style="padding: 6px 12px; border: 1px solid #ddd; text-align: center;">{freq:.1f}%</td></tr>'
    html += '</table>'

    # 蓝球TOP5
    html += '<h3 style="color: #3498db;">💧 蓝球高频TOP5</h3><table style="border-collapse: collapse; margin-bottom: 20px;">'
    html += '<tr style="background: #3498db; color: white;"><th style="padding: 6px 12px; border: 1px solid #ddd;">号码</th><th style="padding: 6px 12px; border: 1px solid #ddd;">次数</th><th style="padding: 6px 12px; border: 1px solid #ddd;">频率</th></tr>'
    for num, count in blue_top:
        freq = count / total * 100
        html += f'<tr><td style="padding: 6px 12px; border: 1px solid #ddd; text-align: center;">{num:02d}</td><td style="padding: 6px 12px; border: 1px solid #ddd; text-align: center;">{count}</td><td style="padding: 6px 12px; border: 1px solid #ddd; text-align: center;">{freq:.1f}%</td></tr>'
    html += '</table>'

    html += '<p style="color: #999; font-size: 12px; margin-top: 30px;">⚠️ 免责声明：以上推荐仅基于历史数据概率分析，彩票开奖为随机事件，任何分析都无法预测开奖结果，请理性购彩，量力而行。</p>'
    html += '</body></html>'

    return html

# =========== 4. 发送邮件 ===========
def send_email(html_content):
    """发送邮件到 190756579@qq.com"""
    msg = MIMEMultipart('alternative')
    msg['Subject'] = '双色球概率分析 - 5组推荐号码'
    msg['From'] = SMTP_USER
    msg['To'] = '190756579@qq.com'

    html_part = MIMEText(html_content, 'html', 'utf-8')
    msg.attach(html_part)

    # 保存报告文件
    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"Report saved to {REPORT_PATH}")

    # 发送邮件
    try:
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=30)
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, ['190756579@qq.com'], msg.as_string())
        server.quit()
        print("Email sent successfully!")
        return True
    except Exception as e:
        print(f"Email send failed: {e}")
        return False

# =========== 主流程 ===========
if __name__ == '__main__':
    print("Fetching SSQ data...")
    data = fetch_ssq_data()

    if not data or len(data) < 10:
        print("Failed to fetch enough data, using fallback...")
        # 内置近99期数据作为可靠备用（2025099-2026046期）
        data = [
            ("2026050", [6, 11, 16, 17, 18, 26], 16),
            ("2026047", [1, 6, 11, 16, 21, 31], 6),
            ("2026046", [2, 9, 10, 24, 31, 33], 16),
            ("2026045", [4, 11, 15, 17, 24, 30], 15),
            ("2026044", [2, 14, 17, 18, 22, 30], 1),
            ("2026043", [6, 9, 14, 16, 25, 32], 16),
            ("2026042", [2, 7, 12, 19, 24, 31], 10),
            ("2026041", [2, 8, 10, 17, 19, 24], 13),
            ("2026040", [3, 4, 14, 22, 23, 33], 4),
            ("2026039", [8, 17, 18, 21, 25, 30], 5),
            ("2026038", [1, 2, 13, 23, 25, 27], 5),
            ("2026037", [11, 22, 27, 29, 31, 33], 12),
            ("2026036", [6, 10, 12, 15, 22, 28], 8),
            ("2026035", [2, 6, 12, 24, 25, 32], 2),
            ("2026034", [1, 3, 7, 13, 22, 23], 7),
            ("2026033", [3, 6, 13, 21, 28, 29], 6),
            ("2026032", [1, 3, 11, 18, 31, 33], 2),
            ("2026031", [3, 10, 12, 13, 18, 33], 8),
            ("2026030", [10, 11, 14, 19, 22, 24], 4),
            ("2026029", [6, 19, 22, 23, 28, 31], 5),
            ("2026028", [2, 6, 9, 17, 25, 28], 15),
            ("2026027", [2, 13, 17, 18, 25, 26], 13),
            ("2026026", [2, 9, 16, 22, 25, 29], 3),
            ("2026025", [2, 3, 15, 20, 23, 24], 10),
            ("2026024", [1, 2, 13, 21, 23, 29], 14),
            ("2026023", [1, 3, 8, 10, 23, 29], 6),
            ("2026022", [15, 18, 23, 25, 28, 32], 11),
            ("2026021", [3, 13, 25, 26, 30, 31], 4),
            ("2026020", [1, 13, 14, 21, 24, 30], 2),
            ("2026019", [7, 8, 16, 17, 18, 30], 1),
            ("2026018", [11, 15, 17, 22, 25, 30], 7),
            ("2026017", [1, 3, 5, 18, 29, 32], 4),
            ("2026016", [4, 5, 9, 10, 27, 30], 13),
            ("2026015", [7, 10, 13, 22, 27, 31], 12),
            ("2026014", [7, 13, 19, 22, 26, 32], 1),
            ("2026013", [4, 9, 12, 13, 16, 20], 1),
            ("2026012", [3, 5, 7, 16, 20, 24], 8),
            ("2026011", [2, 3, 4, 20, 31, 32], 4),
            ("2026010", [4, 9, 10, 15, 19, 26], 12),
            ("2026009", [3, 6, 13, 19, 23, 25], 10),
            ("2026008", [6, 9, 16, 27, 31, 33], 10),
            ("2026007", [9, 13, 19, 27, 29, 30], 1),
            ("2026006", [2, 6, 22, 23, 24, 28], 15),
            ("2026005", [1, 20, 22, 27, 30, 33], 10),
            ("2026004", [3, 7, 8, 9, 18, 32], 10),
            ("2026003", [5, 6, 9, 21, 28, 30], 16),
            ("2026002", [1, 5, 7, 18, 30, 32], 2),
            ("2026001", [2, 6, 11, 12, 13, 33], 15),
            ("2025151", [8, 9, 14, 22, 28, 30], 4),
            ("2025150", [6, 13, 17, 19, 24, 31], 8),
            ("2025149", [1, 2, 4, 6, 22, 30], 10),
            ("2025148", [3, 4, 9, 10, 15, 22], 16),
            ("2025147", [1, 3, 5, 8, 22, 33], 8),
            ("2025146", [5, 7, 12, 24, 26, 28], 2),
            ("2025145", [11, 12, 15, 18, 25, 32], 14),
            ("2025144", [1, 8, 15, 20, 26, 33], 13),
            ("2025143", [2, 9, 12, 13, 15, 24], 3),
            ("2025142", [2, 13, 15, 23, 27, 31], 16),
            ("2025141", [2, 4, 5, 10, 12, 13], 6),
            ("2025140", [1, 3, 4, 12, 18, 24], 5),
            ("2025139", [2, 5, 17, 22, 30, 33], 6),
            ("2025138", [10, 13, 14, 23, 24, 27], 15),
            ("2025137", [2, 8, 11, 23, 27, 29], 5),
            ("2025136", [8, 10, 14, 23, 28, 32], 12),
            ("2025135", [1, 2, 5, 9, 25, 32], 10),
            ("2025134", [3, 5, 9, 13, 26, 29], 12),
            ("2025133", [5, 14, 17, 19, 20, 33], 7),
            ("2025132", [4, 8, 10, 21, 23, 32], 11),
            ("2025131", [3, 13, 14, 18, 24, 31], 3),
            ("2025130", [1, 5, 8, 14, 19, 23], 6),
            ("2025129", [3, 4, 7, 13, 20, 30], 3),
            ("2025128", [2, 10, 18, 19, 24, 27], 1),
            ("2025127", [3, 9, 15, 17, 19, 28], 3),
            ("2025126", [2, 12, 13, 16, 19, 25], 10),
            ("2025125", [3, 9, 12, 13, 26, 32], 5),
            ("2025124", [1, 2, 18, 19, 21, 33], 13),
            ("2025123", [7, 9, 23, 24, 25, 26], 10),
            ("2025122", [16, 18, 19, 20, 25, 31], 13),
            ("2025121", [6, 8, 10, 25, 29, 30], 8),
            ("2025120", [1, 2, 4, 7, 13, 32], 7),
            ("2025119", [6, 9, 23, 26, 28, 32], 11),
            ("2025118", [1, 10, 11, 16, 24, 26], 3),
            ("2025117", [6, 8, 17, 20, 25, 33], 10),
            ("2025116", [2, 4, 8, 24, 28, 31], 9),
            ("2025115", [2, 3, 8, 19, 24, 30], 2),
            ("2025114", [1, 20, 21, 25, 26, 27], 10),
            ("2025113", [8, 10, 13, 15, 24, 31], 16),
            ("2025112", [3, 9, 11, 13, 20, 32], 2),
            ("2025111", [9, 14, 18, 28, 31, 33], 12),
            ("2025110", [1, 5, 11, 14, 16, 19], 8),
            ("2025109", [5, 6, 9, 17, 18, 31], 3),
            ("2025108", [1, 9, 14, 17, 22, 33], 7),
            ("2025107", [2, 3, 10, 15, 25, 33], 13),
            ("2025106", [4, 5, 17, 22, 26, 30], 4),
            ("2025105", [4, 7, 18, 24, 26, 28], 8),
            ("2025104", [2, 5, 15, 16, 24, 32], 16),
            ("2025103", [13, 16, 21, 25, 28, 31], 16),
            ("2025102", [4, 9, 16, 17, 18, 31], 7),
            ("2025101", [5, 8, 9, 10, 16, 21], 5),
            ("2025100", [12, 16, 17, 25, 30, 31], 16),
            ("2025099", [9, 11, 15, 17, 22, 26], 14),
        ]

    print(f"Got {len(data)} periods data")

    recommendations, red_counter, blue_counter = analyze(data)

    print("\n5 Groups of Recommendations:")
    for i, (strategy, reds, blue) in enumerate(recommendations, 1):
        red_str = " ".join(f"{x:02d}" for x in reds)
        print(f"  Group {i} [{strategy}]: Red={red_str} Blue={blue:02d}")

    html = build_email(recommendations, red_counter, blue_counter, data)
    success = send_email(html)
    
    if success:
        print("\nDone! Email sent and report saved.")
    else:
        print("\nDone! Report saved but email failed.")
