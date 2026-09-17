"""
产业主体追踪引擎 tracker.py
- 抓取东方财富研报中心近 30 天研报标题
- 用细分产业词典在标题中精确匹配
- 输出 Top 30 候选 → beta.json (HTML 里 fetch 这个文件名)
运行: python tracker.py
"""
import json, urllib.request, urllib.parse, datetime, re, sys, os
from collections import Counter
import jieba

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

KNOWN = set("""碳化硅 氮化镓 电子布 电子特种气体 PPO树脂 OCS光交换机 6G 光纤光缆
HBM 1.6T光模块 800G CPO 共封装光学 硅光 固态电池 钠离子电池 一体化压铸
工业母机 五轴联动 人形机器人 低空经济 eVTOL TOPCon HJT BC 光伏 算力 AI服务器""".split())

STOP = set("""的 了 和 与 或 在 为 是 对 等 中 上 下 个 来 去 到 把 被 让
我们 你们 他们 这个 那个 哪个 这些 那些 什么 怎么 为何 为什么
可以 应该 需要 可能 有 无 进行 通过 关于 对于 根据 截至 自从
但 但是 而且 然后 不仅 既 既不 也 还 又 又如 比如 例如 包括 以及 等等
之 于 其 此 该 各 每 某 本 此一 一些 一切 任何 所有 全部
报告 研报 分析 研究 公司 上市 股份 集团 控股 集团 公司
业绩 财报 半年报 年报 季报 一季度 二季度 三季度 四季度 中报 一季报 三季报
点评 深度 推荐 跟踪 评级 维持 买入 增持 持有 减持 卖出 覆盖 给予 首次
行业 板块 个股 标的 龙头 股票 沪深 创业板 科创板 主板 计算机 计算机行业
全球 国内 国外 海外 国际 中国 美国 日本 韩国 欧洲
周二 周三 周四 周五 周一 周六 周日 今天 昨天 明天 本周 下周 上周
万 亿 元 角 分 个 只 条 篇
看 看好 看空 关注 提示 风险 机会 趋势
具有 一定 程度 上 自身 相应 相关
周报 月报 季报 年报 总结 持续 加速 景气 展望 回顾 动态 跟踪
更新 评估 调整 上涨 下跌 反弹 回落 走势 表现 涨跌 涨幅 跌幅
系列 专题 框架 思路 路径 演绎 演化
增长 需求 消费 发布 中报 周期 落地 市场 预期 分化 投资 价格 驱动
产业 发展 产能 销量 收入 利润 供给 未来 空间 规模 节奏 概率
地产 房地产 政策 事件 催化 影响 因素 占比 同比 环比 降幅 增速
渗透 渗透率 国产 替代 突破 进展 推进 启动 发力 加码 布局 探索
建设 投产 量产 交付 出货 拿单 中标 拿点
变化 提升 优化 完善 升级 转型 重构 重塑 修复
头部 龙头 公司 企业 厂商 制造商 供应商 服务商 平台
主线 逻辑 主题 热点 高潮 切换 轮动 共振
价值 估值 涨价 提价 调价 让利 毛利 毛利率 净利
底部 复苏 触底 反转 拐点 见底 见顶 高点 低点 新高 新低""".split())

USER_WORDS = """碳化硅 氮化镓 电子布 电子特种气体 PPO树脂 OCS光交换机 光交换机
6G 光纤光缆 光模块 HBM 高带宽存储 1.6T光模块 800G光模块 CPO 共封装光学 硅光
固态电池 半固态电池 钠离子电池 钠电 一体化压铸 工业母机 五轴联动 五轴联动机床
人形机器人 仿生机器人 低空经济 eVTOL 适航 TOPCon HJT BC电池 钙钛矿 钙钛矿电池
光伏组件 算力 AI服务器 智能算力 算力网络 第三代半导体 第二代半导体 半导体设备
半导体材料 光刻机 光刻胶 EDA 先进封装 Chiplet 存储芯片 模拟芯片 功率半导体
碳纤维 复合材料 高温合金 钛合金 算力基础设施 数据中心 交换机
PCB 覆铜板 高速连接器 高速连接 铜缆 液冷 液冷服务器 储能 储能电池 工商储
动力电池 电池正极 电池负极 电解液 隔膜 钴锂 锂矿 锂电 磷酸铁锂 三元材料
机器人 减速器 丝杠 力矩传感器 灵巧手 伺服系统 机器视觉 域控制器
低空 空管 无人机 eVTOL整机 商业航天 卫星互联网 卫星导航 北斗
创新药 CXO ADC GLP-1 创新器械 血液灌流 医疗器械 医疗服务
有色金属 贵金属 黄金 白银 铜 铝 锂 钴 稀土 磁材
煤炭 焦煤 焦炭 钢铁 铁矿石 化工 化纤 农化 氟化工 磷化工
白酒 啤酒 调味品 乳品 速冻 预调酒 零食 休闲食品
家电 白电 厨电 小家电 黑电 清洁电器
整车 乘用车 商用车 新能源车 充电桩 换电 智能驾驶 智能座舱
证券 保险 银行 券商 多元金融 金融科技
游戏 影视 出版 营销 广告 元宇宙
医药 生物制品 中药 创新药 仿制药 医美 养老
半导体 消费电子 元器件 被动元件 面板 玻璃
机械 工程机械 自动化 激光 工业气体
军工 航空航天 兵器 船舶 卫星 通信""".split()

def fetch_reports(days=30, total=600):
    end = datetime.date.today()
    begin = end - datetime.timedelta(days=days)
    base = "https://reportapi.eastmoney.com/report/list?" + urllib.parse.urlencode({
        "qType": 1, "industryCode": "*", "pageSize": 100, "industry": "*",
        "rating": "*", "ratingChange": "*",
        "beginTime": begin.strftime("%Y-%m-%d"),
        "endTime": end.strftime("%Y-%m-%d"),
        "platform": "wyfcw",
    })
    items = []
    for page in range(1, total // 100 + 1):
        u = base + "&pageNo=" + str(page)
        try:
            req = urllib.request.Request(u, headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://data.eastmoney.com/report/",
            })
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read().decode("utf-8"))
        except Exception as e:
            print(f"[warn] page {page} failed: {e}", file=sys.stderr)
            break
        batch = data.get("data") or []
        if not batch:
            break
        items.extend(batch)
        if len(batch) < 100:
            break
    return items

def main():
    for w in USER_WORDS:
        jieba.add_word(w)

    print("[1/3] 抓取研报近 30 天...")
    reports = fetch_reports(days=30, total=600)
    print(f"  [OK] 共 {len(reports)} 篇研报")
    if not reports:
        print("  [X] 无数据", file=sys.stderr)
        return

    candidate_words = [w for w in USER_WORDS if w not in KNOWN and len(w) >= 2]
    items = []
    for kw in candidate_words:
        matched = [r for r in reports if kw in (r.get("title") or "")]
        if not matched:
            continue
        companies = set()
        for r in matched:
            s = (r.get("stockName") or "").replace(" ", "").replace("，", ",")
            if s:
                companies.add(s.split(",")[0])
        latest = matched[0]
        encode_url = latest.get("encodeUrl") or ""
        sample_url = (f"https://data.eastmoney.com/report/zw_stock.jshtml?encodeUrl={encode_url}"
                      if encode_url else "")
        items.append({
            "keyword": kw,
            "count": len(matched),
            "trend": "rising",
            "companies": list(companies)[:5],
            "sampleUrl": sample_url,
            "sampleTitle": latest.get("title", ""),
        })
    items.sort(key=lambda x: -x["count"])
    items = items[:30]

    out = {
        "updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "东方财富研报中心",
        "totalReports": len(reports),
        "items": items,
    }
    out_path = os.path.join(OUT_DIR, "beta.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[2/3] 细分产业词典匹配完成,Top {len(items)} 个候选")
    print(f"[3/3] 输出 {out_path}")
    print(f"\n  Top 10 细分产业活跃度:")
    for it in items[:10]:
        kw = it["keyword"]
        co = "/".join(it["companies"]) or "-"
        print(f"  - {kw:<10} x{it['count']:<3}  关联: {co}")

if __name__ == "__main__":
    main()
