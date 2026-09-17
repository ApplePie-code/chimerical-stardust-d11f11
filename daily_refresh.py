"""
每日数据刷新脚本 daily_refresh.py
- 抓取沪深成交额
- 更新 index.html 里的日期标签、section-head desc、topbar 沪深成交额
- 更新 opinions.json 的 updated 字段
- chip 数字由前端 JSONP 实时刷新,这里不动
- 晨观 5 分钟要点为手写要点,本脚本不动(每周人工更新)
运行: python daily_refresh.py
"""
import json, urllib.request, datetime, re, sys

def fetch_amount():
    """抓上证+深证成交额"""
    SECIDS = ['1.000001', '0.399001']
    url = ("https://push2.eastmoney.com/api/qt/ulist.np/get?fltt=2"
           "&fields=f2,f3,f6,f12,f13,f14&secids=" + ",".join(SECIDS))
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print(f"[warn] fetch_amount failed: {e}", file=sys.stderr)
        return 0, 0
    sh = sz = 0
    if data and data.get("data") and data["data"].get("diff"):
        for d in data["data"]["diff"]:
            key = str(d.get("f13")) + "." + str(d.get("f12"))
            amt = d.get("f6") or 0
            if key == "1.000001": sh = amt
            elif key == "0.399001": sz = amt
    return sh, sz

def latest_dates():
    """计算最近交易日: A股昨日 + 美股隔夜"""
    today = datetime.date.today()
    w = today.weekday()  # 0=Mon, 6=Sun
    if w == 0:       # 周一:A股上周五,美股上周五
        a = today - datetime.timedelta(days=3)
        u = today - datetime.timedelta(days=3)
    elif w == 6:     # 周日:A股上周五,美股上周五(周六凌晨)
        a = today - datetime.timedelta(days=2)
        u = today - datetime.timedelta(days=1)
    else:
        a = today - datetime.timedelta(days=1)
        u = today - datetime.timedelta(days=1)
    return a, u

def update_html(sh_amount, sz_amount):
    with open("index.html", "r", encoding="utf-8") as f:
        html = f.read()

    today_str = datetime.date.today().strftime("%Y-%m-%d")
    a_day, u_day = latest_dates()
    a_str = a_day.strftime("%Y-%m-%d")
    u_str = u_day.strftime("%m-%d")
    total_wan = (sh_amount + sz_amount) / 1e8 / 10000  # 元 → 亿 → 万亿
    amount_str = f'{total_wan:.3f}'

    # 1. nav-foot 数据更新于
    html = re.sub(r'数据更新于 \d{4}-\d{2}-\d{2}',
                  f'数据更新于 {today_str}', html)
    # 2. section-head desc(形如 2026-09-14 / 09-15 隔夜及昨日收盘)
    html = re.sub(r'\d{4}-\d{2}-\d{2} / \d{2}-\d{2} 隔夜及昨日收盘',
                  f'{a_str} / {u_str} 隔夜及昨日收盘', html)
    # 3. topbar 沪深 X.XXX万亿
    html = re.sub(r'沪深 [\d\.]+万亿', f'沪深 {amount_str}万亿', html)

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  [HTML] 日期={today_str} | desc={a_str}/{u_str} | 沪深={amount_str}万亿")

def update_opinions():
    with open("opinions.json", "r", encoding="utf-8") as f:
        d = json.load(f)
    d["updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    with open("opinions.json", "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    print(f"  [opinions.json] updated={d['updated']}")

def main():
    print("[1/3] 抓取沪深成交额…")
    sh, sz = fetch_amount()
    print(f"  [OK] 上证={sh/1e8:,.2f}亿 深证={sz/1e8:,.2f}亿 合计={(sh+sz)/1e8:,.2f}亿")
    print("[2/3] 更新 index.html 日期与成交额…")
    update_html(sh, sz)
    print("[3/3] 更新 opinions.json updated 字段…")
    update_opinions()
    print("\n✓ 完成")

if __name__ == "__main__":
    main()
