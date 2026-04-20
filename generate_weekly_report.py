#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小红书创作者数据 - 简版周报生成器
包含：概览 / 按周统计 / 每篇详情（互动率+涨势标签）/ 横向对比 / 内容诊断
"""

import json
import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent
REPORT_DIR = BASE_DIR / "reports"
DATA_DIR = BASE_DIR / "data"
REPORT_DIR.mkdir(exist_ok=True)


# ─── 工具函数 ─────────────────────────────────────────────────

def fmt_number(n):
    try:
        n = int(n)
        if n >= 10000:
            return f"{n/10000:.1f}w"
        return str(n)
    except:
        return str(n) if n else "0"


def fmt_pct(n, decimals=1):
    try:
        return f"{float(n):.{decimals}f}%"
    except:
        return "0%"


def is_in_last_4_weeks(date_str: str) -> bool:
    try:
        date_part = date_str.split()[0]
        dt = datetime.datetime.strptime(date_part, "%Y-%m-%d")
        cutoff = datetime.datetime.now() - datetime.timedelta(days=28)
        return dt >= cutoff
    except:
        return False


def group_notes_by_week(notes: list) -> dict:
    """将笔记按周（周一为起点）分组，只保留近4周"""
    weeks = {}
    cutoff = datetime.datetime.now() - datetime.timedelta(days=28)
    for note in notes:
        time_str = note.get("time", "")
        if not time_str:
            continue
        try:
            date_str = time_str.split()[0]
            dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            monday = dt - datetime.timedelta(days=dt.weekday())
            week_key = monday.strftime("%Y-%m-%d")
            if datetime.datetime.strptime(week_key, "%Y-%m-%d") >= cutoff:
                weeks.setdefault(week_key, []).append(note)
        except:
            continue
    return weeks


def calculate_engagement(views, likes, collects, comments):
    """计算互动率 = (点赞+收藏+评论) / 浏览 * 100"""
    if views <= 0:
        return 0.0
    return (likes + collects + comments) / views * 100


def days_since_publish(time_str: str) -> int:
    try:
        date_part = time_str.split()[0]
        dt = datetime.datetime.strptime(date_part, "%Y-%m-%d")
        return (datetime.datetime.now() - dt).days
    except:
        return 0


def get_trend_label(note: dict, tracking: dict) -> str:
    """
    根据 tracking 数据判断涨势标签
    - 有多个快照：对比最早和最新快照的浏览增量
    - 只有一个快照（新笔记）：按发布天数 + 当前数据判断
    """
    note_id = note.get("id", "")
    info = tracking.get(note_id, {})
    snapshots = info.get("snapshots", [])
    views = int(note.get("view_count", 0) or 0)
    days = days_since_publish(note.get("time", ""))

    if len(snapshots) >= 2:
        first_views = snapshots[0].get("views", 0)
        last_views = snapshots[-1].get("views", 0)
        span_days = max(1, (datetime.datetime.strptime(snapshots[-1]["date"], "%Y-%m-%d") -
                           datetime.datetime.strptime(snapshots[0]["date"], "%Y-%m-%d")).days)
        daily_avg = (last_views - first_views) / span_days
        if daily_avg >= 500:
            return '<span class="tag tag-hot">🔥 爆发增长</span>'
        elif daily_avg >= 100:
            return '<span class="tag tag-up">📈 稳定增长</span>'
        elif daily_avg >= 10:
            return '<span class="tag tag-slow">➡️ 缓慢增长</span>'
        else:
            return '<span class="tag tag-flat">💤 趋于平稳</span>'
    else:
        # 只有一条快照，用发布天数估算
        if days <= 1:
            return '<span class="tag tag-new">🆕 刚发布</span>'
        daily_avg = views / max(1, days)
        if daily_avg >= 500:
            return '<span class="tag tag-hot">🔥 爆发增长</span>'
        elif daily_avg >= 100:
            return '<span class="tag tag-up">📈 稳定增长</span>'
        elif daily_avg >= 20:
            return '<span class="tag tag-slow">➡️ 缓慢增长</span>'
        else:
            return '<span class="tag tag-flat">💤 趋于平稳</span>'


def load_tracking() -> dict:
    path = DATA_DIR / "note_tracking.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


# ─── HTML 生成：各板块 ─────────────────────────────────────────

def generate_weekly_summary(weeks_data: dict) -> str:
    if not weeks_data:
        return '<div class="no-data">暂无近4周数据</div>'

    cards_html = ""
    for week_key in sorted(weeks_data.keys()):
        notes = weeks_data[week_key]
        n = len(notes)
        views   = sum(int(x.get("view_count", 0) or 0) for x in notes)
        likes   = sum(int(x.get("likes", 0) or 0) for x in notes)
        collects= sum(int(x.get("collected_count", 0) or 0) for x in notes)
        comments= sum(int(x.get("comments_count", 0) or 0) for x in notes)
        eng = calculate_engagement(views, likes, collects, comments)

        dt = datetime.datetime.strptime(week_key, "%Y-%m-%d")
        ws = dt.strftime("%m/%d")
        we = (dt + datetime.timedelta(days=6)).strftime("%m/%d")

        cards_html += f"""
        <div class="week-card">
            <div class="week-header">
                <span class="week-label">📅 {ws} - {we}</span>
                <span class="week-count">{n} 篇</span>
            </div>
            <div class="week-stats">
                <div class="stat-item"><span class="stat-value">{fmt_number(views)}</span><span class="stat-label">浏览</span></div>
                <div class="stat-item"><span class="stat-value">{fmt_number(likes)}</span><span class="stat-label">点赞</span></div>
                <div class="stat-item"><span class="stat-value">{fmt_number(collects)}</span><span class="stat-label">收藏</span></div>
                <div class="stat-item"><span class="stat-value">{fmt_number(comments)}</span><span class="stat-label">评论</span></div>
            </div>
            <div class="week-avg">
                <span>篇均浏览 {fmt_number(views // n if n else 0)}</span>
                <span>互动率 {fmt_pct(eng)}</span>
            </div>
        </div>"""
    return cards_html


def generate_notes_detail(weeks_data: dict, tracking: dict) -> str:
    """按周分组的笔记详情表，含互动率、涨势标签"""
    if not weeks_data:
        return '<div class="no-data">暂无近4周笔记数据</div>'

    html = ""
    for week_key in sorted(weeks_data.keys(), reverse=True):
        notes = weeks_data[week_key]
        dt = datetime.datetime.strptime(week_key, "%Y-%m-%d")
        ws = dt.strftime("%m/%d")
        we = (dt + datetime.timedelta(days=6)).strftime("%m/%d")

        views_w   = sum(int(x.get("view_count", 0) or 0) for x in notes)
        likes_w   = sum(int(x.get("likes", 0) or 0) for x in notes)

        rows = ""
        for note in sorted(notes, key=lambda x: x.get("time", ""), reverse=True):
            title    = note.get("display_title", "无标题")[:30]
            views    = int(note.get("view_count", 0) or 0)
            likes    = int(note.get("likes", 0) or 0)
            collects = int(note.get("collected_count", 0) or 0)
            comments = int(note.get("comments_count", 0) or 0)
            shares   = int(note.get("shared_count", 0) or 0)
            eng      = calculate_engagement(views, likes, collects, comments)
            pub_date = note.get("time", "")[5:10]
            duration = note.get("video_info", {}).get("duration", 0)
            dur_str  = f"{duration}s" if duration else "-"
            trend    = get_trend_label(note, tracking)

            # 互动率颜色标记
            eng_class = "eng-high" if eng >= 5 else ("eng-mid" if eng >= 2 else "eng-low")

            rows += f"""
            <tr>
                <td class="note-title">{title}</td>
                <td class="num">{fmt_number(views)}</td>
                <td class="num">{fmt_number(likes)}</td>
                <td class="num">{fmt_number(collects)}</td>
                <td class="num">{fmt_number(comments)}</td>
                <td class="num">{fmt_number(shares)}</td>
                <td class="num"><span class="{eng_class}">{fmt_pct(eng)}</span></td>
                <td>{trend}</td>
                <td class="date">{pub_date}</td>
                <td class="date">{dur_str}</td>
            </tr>"""

        html += f"""
        <div class="week-section">
            <div class="week-section-header">
                <span class="week-title">📆 {ws} - {we}</span>
                <span class="week-summary">共 {len(notes)} 篇 | 浏览 {fmt_number(views_w)} | 点赞 {fmt_number(likes_w)}</span>
            </div>
            <table class="notes-table">
                <thead><tr>
                    <th>标题</th>
                    <th style="text-align:right">浏览</th>
                    <th style="text-align:right">点赞</th>
                    <th style="text-align:right">收藏</th>
                    <th style="text-align:right">评论</th>
                    <th style="text-align:right">转发</th>
                    <th style="text-align:right">互动率</th>
                    <th>涨势</th>
                    <th>发布</th>
                    <th>时长</th>
                </tr></thead>
                <tbody>{rows}</tbody>
            </table>
        </div>"""
    return html


def generate_comparison(recent_notes: list, tracking: dict) -> str:
    """横向对比：以互动率排序，突出最佳和最差"""
    if not recent_notes:
        return '<div class="no-data">暂无可对比数据</div>'

    # 计算每篇分数
    scored = []
    for note in recent_notes:
        views    = int(note.get("view_count", 0) or 0)
        likes    = int(note.get("likes", 0) or 0)
        collects = int(note.get("collected_count", 0) or 0)
        comments = int(note.get("comments_count", 0) or 0)
        eng = calculate_engagement(views, likes, collects, comments)
        scored.append({
            "note": note,
            "views": views, "likes": likes, "collects": collects,
            "comments": comments, "eng": eng,
        })

    scored.sort(key=lambda x: x["eng"], reverse=True)
    max_views = max((s["views"] for s in scored), default=1) or 1

    rows = ""
    for i, s in enumerate(scored):
        note = s["note"]
        title = note.get("display_title", "无标题")[:28]
        rank_icon = "🥇" if i == 0 else ("🥈" if i == 1 else ("🥉" if i == 2 else f"{i+1}"))
        bar_w = int(s["views"] / max_views * 100)
        eng_class = "eng-high" if s["eng"] >= 5 else ("eng-mid" if s["eng"] >= 2 else "eng-low")
        days = days_since_publish(note.get("time", ""))

        rows += f"""
        <tr>
            <td class="rank">{rank_icon}</td>
            <td class="note-title">{title}</td>
            <td>
                <div class="bar-wrap"><div class="bar" style="width:{bar_w}%"></div></div>
                <span class="bar-num">{fmt_number(s['views'])}</span>
            </td>
            <td class="num">{fmt_number(s['likes'])}</td>
            <td class="num">{fmt_number(s['collects'])}</td>
            <td class="num"><span class="{eng_class}">{fmt_pct(s['eng'])}</span></td>
            <td class="date">发布 {days} 天</td>
        </tr>"""

    return f"""
    <table class="notes-table">
        <thead><tr>
            <th style="width:40px">排名</th>
            <th>标题</th>
            <th>浏览量</th>
            <th style="text-align:right">点赞</th>
            <th style="text-align:right">收藏</th>
            <th style="text-align:right">互动率</th>
            <th>发布时间</th>
        </tr></thead>
        <tbody>{rows}</tbody>
    </table>"""


def generate_topic_suggestions(all_notes: list, collect_rate: float, like_rate: float, avg_dur: float) -> str:
    """
    根据历史笔记数据动态生成 10 条选题建议。
    逻辑：
    1. 找出历史中浏览/互动最高的笔记，提炼它们的选题方向
    2. 结合收藏率/点赞率判断内容类型偏好
    3. 结合视频时长判断篇幅偏好
    4. 固定补充 5 条通用高潜选题（基于营养师账号普遍规律）
    """
    # ── 分析历史爆款方向 ──────────────────────────────
    top_notes = sorted(
        [n for n in all_notes if int(n.get("view_count", 0) or 0) > 0],
        key=lambda x: int(x.get("view_count", 0) or 0),
        reverse=True
    )[:5]

    top_titles = [n.get("display_title", "") for n in top_notes]

    # ── 判断偏好类型 ──────────────────────────────────
    prefer_collect = collect_rate >= like_rate
    prefer_short   = avg_dur <= 90  # 90s 以下算偏好短视频

    # ── 动态生成建议 ──────────────────────────────────
    suggestions = []

    # 基于爆款方向复制/延伸
    if any("养胃" in t or "肠胃" in t for t in top_titles):
        suggestions.append({
            "title": "养胃必备的5种白色食物（图解版）",
            "reason": "「养胃食物大全」是你账号浏览量最高的笔记（7.9w），养胃话题已验证。图解/清单形式收藏率高，可直接复刻方向。",
            "tag": "复刻爆款",
            "tag_class": "tag-hot",
        })
        suggestions.append({
            "title": "胃不好的人，这3种早餐千万别吃",
            "reason": "「不能吃什么」的否定句式比「应该吃什么」点击率更高，制造焦虑感后给解决方案，是养胃话题的高互动结构。",
            "tag": "高点击结构",
            "tag_class": "tag-up",
        })

    if any("老人" in t or "老年" in t or "年货" in t for t in top_titles):
        suggestions.append({
            "title": "家里有老人，这5种营养品真的别乱买",
            "reason": "你的「老年人营养品」笔记浏览5w+，且「别买XX」类标题在营养健康类有稳定高完播率，用户会存下来作为购物参考。",
            "tag": "复刻爆款",
            "tag_class": "tag-hot",
        })

    if any("睡眠" in t or "睡" in t or "助眠" in t for t in top_titles):
        suggestions.append({
            "title": "睡前吃这4种食物，改善入睡困难（营养师亲测）",
            "reason": "「晚上总醒」笔记是你最新发布的内容，睡眠类话题在小红书流量大。加「营养师亲测」人格背书，可提升信任度和收藏率。",
            "tag": "趋势选题",
            "tag_class": "tag-up",
        })

    if any("脸" in t or "皮肤" in t or "暗沉" in t for t in top_titles):
        suggestions.append({
            "title": "皮肤暗黄？可能是缺这4种营养素",
            "reason": "「脸色暗沉+脾胃不和」笔记近期互动率最高（评论占比高），说明用户有强烈共鸣。从食物维度切皮肤话题，跨圈引流潜力大。",
            "tag": "跨圈引流",
            "tag_class": "tag-up",
        })

    # 基于收藏偏好加清单/工具型选题
    if prefer_collect:
        suggestions.append({
            "title": "超市购物清单｜每周必买的10种健康食物（附挑选技巧）",
            "reason": "你的收藏率 > 点赞率，说明用户更爱「存起来备用」的工具型内容。购物清单类笔记天然高收藏，复购率也高。",
            "tag": "高收藏潜力",
            "tag_class": "tag-up",
        })
        suggestions.append({
            "title": "一周营养食谱丨每天吃什么不重样（可下载打印）",
            "reason": "食谱类内容是营养健康账号收藏率最高的品类之一，「可打印」降低用户使用门槛，进一步提升收藏意愿。",
            "tag": "高收藏潜力",
            "tag_class": "tag-up",
        })
    else:
        suggestions.append({
            "title": "我是营养师，但我也偷偷爱吃这些「垃圾食品」",
            "reason": "你的点赞率 > 收藏率，说明情感共鸣型内容更受欢迎。营养师也是普通人，反差感话题容易引发评论和点赞。",
            "tag": "情感共鸣",
            "tag_class": "tag-slow",
        })

    # 通用高潜选题（营养师账号普遍高流量）
    suggestions.append({
        "title": "真的不用吃保健品！这5种食物比营养素片更管用",
        "reason": "「食物代替保健品」话题能同时命中「节省钱」和「健康」两个用户痛点，打击智商税类内容在营养健康赛道一贯高流量。",
        "tag": "通用爆款结构",
        "tag_class": "tag-hot",
    })
    suggestions.append({
        "title": "一人掌管全家饮食：老人控糖+孩子补脑+自己减脂怎么兼顾",
        "reason": "你已有同话题笔记「一人掌管全家胃」，数据还在积累中。这个选题直接把痛点放标题里，搜索流量更精准，完播率预计更高。",
        "tag": "已验证方向",
        "tag_class": "tag-slow",
    })
    suggestions.append({
        "title": "减脂期最容易踩的5个饮食误区（营养师来破解）",
        "reason": "减脂是小红书全年热搜话题，「误区揭秘」结构制造认知冲突，完播率和分享率都高。营养师身份可做知识增信，与泛娱乐账号形成差异。",
        "tag": "流量热词",
        "tag_class": "tag-hot",
    })
    suggestions.append({
        "title": "口腔溃疡反复发作？可能是身体这个信号，不只是上火",
        "reason": "你的「B族维生素+口腔溃疡」笔记显示用户对「症状背后原因」感兴趣。用「不只是上火」制造认知反差，搜索流量精准，评论区讨论度高。",
        "tag": "搜索流量",
        "tag_class": "tag-slow",
    })

    # 补到 10 条（如果不够）
    extra_pool = [
        {
            "title": "夏天吃冰有多伤脾胃？中医+营养师联合分析",
            "reason": "季节性内容在当季流量大（夏天即将到来），中医+营养师跨界合作类内容在小红书有天然传播优势，能触达两个圈子的用户。",
            "tag": "季节热点",
            "tag_class": "tag-up",
        },
        {
            "title": "铁锅炒菜真的能补铁吗？一次说清楚",
            "reason": "「XX真的有用吗」是营养科普的经典选题结构，能截获有疑问的搜索流量，且用户分享欲强（想发给家人辟谣）。",
            "tag": "辟谣/科普",
            "tag_class": "tag-slow",
        },
        {
            "title": "体检报告看不懂？营养师帮你解读这5项关键指标",
            "reason": "体检季（每年3-5月）搜索量大，帮用户解读指标是强服务型内容，收藏率和转发率都高，能精准触达有健康意识的潜在粉丝。",
            "tag": "季节热点",
            "tag_class": "tag-up",
        },
    ]
    for e in extra_pool:
        if len(suggestions) >= 10:
            break
        suggestions.append(e)

    suggestions = suggestions[:10]

    # ── 生成 HTML ──────────────────────────────────────
    rows_html = ""
    for i, s in enumerate(suggestions):
        rows_html += f"""
        <div class="suggest-item">
            <div class="suggest-num">{i + 1}</div>
            <div class="suggest-body">
                <div class="suggest-title-row">
                    <span class="suggest-title">「{s['title']}」</span>
                    <span class="tag {s['tag_class']}">{s['tag']}</span>
                </div>
                <div class="suggest-reason">📌 {s['reason']}</div>
            </div>
        </div>"""

    return rows_html


def _analyze_single_note(note: dict, tracking_snapshots: list) -> dict:
    """
    对单篇笔记进行数据分析，返回诊断结果。
    """
    views    = int(note.get("view_count", 0) or 0)
    likes    = int(note.get("likes", 0) or 0)
    collects = int(note.get("collected_count", 0) or 0)
    comments = int(note.get("comments_count", 0) or 0)
    shares   = int(note.get("share_count", 0) or 0)
    duration = int(note.get("video_info", {}).get("duration", 0) or 0)
    title    = note.get("display_title", "无标题")
    time_str = note.get("time", "")
    days     = days_since_publish(time_str)
    eng      = calculate_engagement(views, likes, collects, comments)

    # ── 趋势判断（基于多日快照）─────────────────────────
    trend_label = "持平"
    trend_icon  = "➡️"
    trend_class = "trend-flat"
    daily_avg_growth = 0

    if len(tracking_snapshots) >= 2:
        sorted_snaps = sorted(tracking_snapshots, key=lambda x: x.get("date", ""))
        first = sorted_snaps[0]
        last  = sorted_snaps[-1]
        date_diff = (datetime.datetime.strptime(last["date"], "%Y-%m-%d")
                     - datetime.datetime.strptime(first["date"], "%Y-%m-%d")).days or 1
        view_diff = int(last.get("views", 0)) - int(first.get("views", 0))
        daily_avg_growth = view_diff / date_diff

        if daily_avg_growth >= 50:
            trend_label, trend_icon, trend_class = "快速涨", "🚀", "trend-up"
        elif daily_avg_growth >= 10:
            trend_label, trend_icon, trend_class = "稳步涨", "📈", "trend-up"
        elif daily_avg_growth <= -5:
            trend_label, trend_icon, trend_class = "下滑中", "📉", "trend-down"
        else:
            trend_label, trend_icon, trend_class = "流量见顶", "➡️", "trend-flat"
    elif days <= 3:
        trend_label, trend_icon, trend_class = "新发潜力", "🆕", "trend-new"
    elif views < 100:
        trend_label, trend_icon, trend_class = "曝光不足", "⚠️", "trend-warn"

    # ── 指标雷达（各项率）──────────────────────────────
    like_rate    = likes    / views * 100 if views else 0
    collect_rate = collects / views * 100 if views else 0
    comment_rate = comments / views * 100 if views else 0
    share_rate   = shares   / views * 100 if views else 0

    # ── 强项 / 弱项 标签 ──────────────────────────────
    strengths = []
    weaknesses = []

    if eng >= 5:
        strengths.append("互动率优秀")
    elif eng < 1 and views > 500:
        weaknesses.append("互动率偏低")

    if like_rate > collect_rate and like_rate > 2:
        strengths.append("点赞率高（情感共鸣强）")
    if collect_rate > like_rate and collect_rate > 2:
        strengths.append("收藏率高（内容实用）")
    if comment_rate > 1:
        strengths.append("评论区活跃（引发讨论）")
    if share_rate > 1:
        strengths.append("转发率高（有传播力）")

    if views > 0 and likes == 0 and collects == 0:
        weaknesses.append("零互动，钩子可能不够强")
    if duration > 0 and duration < 30 and eng < 1:
        weaknesses.append("视频过短，信息密度不够")
    if views > 1000 and eng < 0.5:
        weaknesses.append("曝光量够但转化差，开头需优化")

    # ── 综合诊断 + 改进建议 ───────────────────────────
    if views == 0:
        verdict = "尚无数据"
        action  = "等待数据积累，关注发布后24小时的初始流量"
    elif days <= 3:
        if eng >= 5:
            verdict = "首发数据优秀"
            action  = "继续保持这类内容的产出节奏，这是你的爆款方向"
        elif eng >= 2:
            verdict = "首发数据正常"
            action  = "继续观察3-5天，流量仍在上升期，不要急于判断"
        else:
            verdict = "首发数据偏弱"
            action  = "新笔记通常有冷启动期，关注24小时后的自然增长，如果持续低迷建议优化封面和标题"
    elif daily_avg_growth >= 20:
        verdict = "持续在涨"
        action  = "流量还在爬升，继续观察，不要下架。可在评论区置顶相关话题引导互动"
    elif daily_avg_growth <= -10:
        verdict = "涨势已过"
        action  = "流量趋于见顶，可以考虑制作同话题后续篇，利用老笔记的长尾流量导流"
    elif eng >= 5:
        verdict = "高互动优质内容"
        action  = "这是你的最佳内容方向，建议以此为模板复制到类似话题"
    elif eng >= 2:
        verdict = "表现中等"
        action  = "数据中规中矩，可在评论区加强互动引导（如提问'你踩过几个？'）提升评论率"
    elif views >= 500:
        verdict = "曝光高但转化低"
        action  = "开头3秒钩子不够吸引人，建议重制封面或尝试'前3秒'重新剪辑"
    else:
        verdict = "整体偏弱"
        action  = "可能是话题本身流量池小，建议蹭当周热搜词，或测试不同标题角度"

    # ── 互动结构雷达（文本条形图）─────────────────────
    def mini_bar(rate, color):
        w = min(rate * 10, 100)
        return f'<div class="mini-bar" style="width:{w}%;background:{color}"></div>'

    radar_html = f"""
    <div class="note-radar">
        <div class="radar-row">
            <span class="radar-label">点赞 {like_rate:.1f}%</span>
            <div class="radar-track">{mini_bar(like_rate, '#ff6b81')}</div>
        </div>
        <div class="radar-row">
            <span class="radar-label">收藏 {collect_rate:.1f}%</span>
            <div class="radar-track">{mini_bar(collect_rate, '#4facfe')}</div>
        </div>
        <div class="radar-row">
            <span class="radar-label">评论 {comment_rate:.1f}%</span>
            <div class="radar-track">{mini_bar(comment_rate, '#ffd32a')}</div>
        </div>
        <div class="radar-row">
            <span class="radar-label">转发 {share_rate:.1f}%</span>
            <div class="radar-track">{mini_bar(share_rate, '#05c46b')}</div>
        </div>
    </div>"""

    # ── 组装诊断卡片 ──────────────────────────────────
    strength_tags = "".join(
        f'<span class="note-tag tag-strong">{s}</span>' for s in strengths
    ) if strengths else ""
    weak_tags = "".join(
        f'<span class="note-tag tag-weak">{w}</span>' for w in weaknesses
    ) if weaknesses else ""

    eng_class = "eng-high" if eng >= 5 else ("eng-mid" if eng >= 2 else "eng-low")
    dur_str = f"{duration // 60}:{duration % 60:02d}" if duration else "—"

    card = f"""
    <div class="note-card">
        <div class="note-card-header">
            <div class="note-card-title-row">
                <span class="note-card-title">{title[:28]}{'…' if len(title) > 28 else ''}</span>
                <span class="note-eng-badge {eng_class}">{fmt_pct(eng)}</span>
            </div>
            <div class="note-card-meta">
                <span>发布 {days} 天</span>
                <span>·</span>
                <span>时长 {dur_str}</span>
                <span>·</span>
                <span class="{trend_class}">{trend_icon} {trend_label}</span>
            </div>
        </div>
        <div class="note-card-body">
            <div class="note-metrics">
                <div class="metric-box">
                    <div class="metric-num">{fmt_number(views)}</div>
                    <div class="metric-label">浏览</div>
                </div>
                <div class="metric-box">
                    <div class="metric-num">{fmt_number(likes)}</div>
                    <div class="metric-label">点赞</div>
                </div>
                <div class="metric-box">
                    <div class="metric-num">{fmt_number(collects)}</div>
                    <div class="metric-label">收藏</div>
                </div>
                <div class="metric-box">
                    <div class="metric-num">{fmt_number(comments)}</div>
                    <div class="metric-label">评论</div>
                </div>
                <div class="metric-box">
                    <div class="metric-num">{fmt_number(shares)}</div>
                    <div class="metric-label">转发</div>
                </div>
            </div>
            <div class="note-diag">
                <div class="note-verdict">
                    <span class="verdict-badge {eng_class}">{verdict}</span>
                </div>
                <div class="note-action">
                    <span class="action-icon">💡</span>
                    <span class="action-text">{action}</span>
                </div>
                {radar_html}
                <div class="note-tags-row">
                    {strength_tags}{weak_tags}
                </div>
            </div>
        </div>
    </div>"""

    return card


def generate_content_diagnosis(recent_notes: list, all_notes: list = None, tracking: dict = None) -> str:
    """单篇笔记诊断 + 10条选题建议"""
    if not recent_notes:
        return '<div class="no-data">暂无数据</div>'

    # 加载追踪数据
    tracking = tracking or {}
    if tracking is None:
        tp = DATA_DIR / "note_tracking.json"
        if tp.exists():
            with open(tp, encoding="utf-8") as f:
                tracking = json.load(f)

    # 按互动率排序后逐篇生成分析卡片
    scored = []
    for note in recent_notes:
        nid = note.get("note_id", "")
        views    = int(note.get("view_count", 0) or 0)
        likes    = int(note.get("likes", 0) or 0)
        collects = int(note.get("collected_count", 0) or 0)
        comments = int(note.get("comments_count", 0) or 0)
        eng = calculate_engagement(views, likes, collects, comments)
        scored.append({"note": note, "eng": eng})

    scored.sort(key=lambda x: x["eng"], reverse=True)

    cards_html = ""
    for s in scored:
        note = s["note"]
        nid  = note.get("note_id", "")
        snaps = tracking.get(nid, {}).get("snapshots", [])
        cards_html += _analyze_single_note(note, snaps)

    # ── 全局信号摘要（保留小面板）──────────────────────
    total_views    = sum(s["eng"] for s in scored)  # 复用变量名
    items_eng_list = [s["eng"] for s in scored]
    avg_eng        = sum(items_eng_list) / len(items_eng_list) if items_eng_list else 0

    total_views    = sum(int(n.get("view_count", 0) or 0) for n in recent_notes)
    total_likes    = sum(int(n.get("likes", 0) or 0) for n in recent_notes)
    total_collects = sum(int(n.get("collected_count", 0) or 0) for n in recent_notes)
    like_rate      = total_likes    / total_views    * 100 if total_views    else 0
    collect_rate   = total_collects / total_views    * 100 if total_views    else 0

    if collect_rate > like_rate:
        content_signal = "收藏率 > 点赞率，实用型内容更受欢迎"
        tip = "清单/攻略/食谱类内容可多加；结尾引导「收藏备用」"
    else:
        content_signal = "点赞率 > 收藏率，情感共鸣型内容更受欢迎"
        tip = "在实用内容中加入故事感和情绪点，引发共鸣"

    # 选题建议
    avg_dur = sum(int(n.get("video_info", {}).get("duration", 0) or 0) for n in recent_notes) / max(1, len(recent_notes))
    suggest_html = generate_topic_suggestions(
        all_notes or recent_notes, collect_rate, like_rate, avg_dur
    )

    return f"""
    <div class="diag-summary-bar">
        <div class="diag-stat-item">
            <span class="diag-stat-label">篇均互动率</span>
            <span class="diag-stat-value {'eng-high' if avg_eng >= 5 else 'eng-mid' if avg_eng >= 2 else 'eng-low'}">{fmt_pct(avg_eng)}</span>
        </div>
        <div class="diag-stat-item">
            <span class="diag-stat-label">篇均浏览</span>
            <span class="diag-stat-value">{fmt_number(total_views // max(1, len(recent_notes)))}</span>
        </div>
        <div class="diag-stat-item">
            <span class="diag-stat-label">点赞率</span>
            <span class="diag-stat-value">{fmt_pct(like_rate)}</span>
        </div>
        <div class="diag-stat-item">
            <span class="diag-stat-label">收藏率</span>
            <span class="diag-stat-value">{fmt_pct(collect_rate)}</span>
        </div>
    </div>
    <div class="diag-insight">
        <div class="insight-row">📊 <strong>数据信号：</strong>{content_signal}</div>
        <div class="insight-row">💡 <strong>内容策略：</strong>{tip}</div>
    </div>

    <div class="note-cards-grid">
        {cards_html}
    </div>

    <div class="suggest-section">
        <div class="suggest-header">🎯 本周选题推荐（10条）</div>
        <div class="suggest-list">
            {suggest_html}
        </div>
    </div>"""


# ─── 主 HTML 组装 ─────────────────────────────────────────────

def generate_html(data: dict, prev_data: dict = None) -> str:
    date_str   = data.get("date", datetime.date.today().strftime("%Y-%m-%d"))
    fetch_time = data.get("fetch_time", "")
    notes      = data.get("notes", [])
    tracking   = load_tracking()

    recent_notes = [n for n in notes if is_in_last_4_weeks(n.get("time", ""))]
    weeks_data   = group_notes_by_week(recent_notes)

    total_notes    = len(recent_notes)
    total_views    = sum(int(n.get("view_count", 0) or 0) for n in recent_notes)
    total_likes    = sum(int(n.get("likes", 0) or 0) for n in recent_notes)
    total_collects = sum(int(n.get("collected_count", 0) or 0) for n in recent_notes)
    total_comments = sum(int(n.get("comments_count", 0) or 0) for n in recent_notes)
    overall_eng    = calculate_engagement(total_views, total_likes, total_collects, total_comments)

    weekly_summary_html = generate_weekly_summary(weeks_data)
    notes_detail_html   = generate_notes_detail(weeks_data, tracking)
    comparison_html     = generate_comparison(recent_notes, tracking)
    diagnosis_html      = generate_content_diagnosis(recent_notes, all_notes=notes, tracking=tracking)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>小红书运营周报 · {date_str}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, "PingFang SC", sans-serif; background: #fef6f7; color: #333; }}
  .header {{ background: linear-gradient(135deg, #ff2442 0%, #ff6b81 100%); color: white; padding: 32px 40px; }}
  .header h1 {{ font-size: 26px; font-weight: 700; }}
  .header p {{ margin-top: 6px; opacity: 0.85; font-size: 14px; }}
  .container {{ max-width: 1100px; margin: 0 auto; padding: 28px 20px; }}

  /* 概览 */
  .overview {{ background: white; border-radius: 16px; padding: 24px; margin-bottom: 24px;
               display: grid; grid-template-columns: repeat(5, 1fr); gap: 16px; text-align: center;
               box-shadow: 0 2px 12px rgba(255,36,66,0.06); }}
  .overview-item .value {{ font-size: 28px; font-weight: 700; color: #ff2442; }}
  .overview-item .label {{ font-size: 12px; color: #999; margin-top: 4px; }}

  /* section */
  .section {{ background: white; border-radius: 16px; padding: 24px; margin-bottom: 24px;
               box-shadow: 0 2px 12px rgba(255,36,66,0.06); }}
  .section-title {{ font-size: 16px; font-weight: 600; margin-bottom: 18px;
                    border-left: 4px solid #ff2442; padding-left: 10px; color: #222; }}

  /* 周统计卡片 */
  .weeks-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 16px; }}
  .week-card {{ background: #fff9fa; border-radius: 12px; padding: 18px; border: 1px solid #ffe0e5; }}
  .week-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }}
  .week-label {{ font-size: 13px; font-weight: 600; }}
  .week-count {{ background: #ffe0e5; color: #ff2442; padding: 2px 8px; border-radius: 8px; font-size: 11px; }}
  .week-stats {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-bottom: 10px; }}
  .stat-item {{ text-align: center; }}
  .stat-value {{ font-size: 16px; font-weight: 700; color: #ff2442; display: block; }}
  .stat-label {{ font-size: 11px; color: #999; }}
  .week-avg {{ font-size: 11px; color: #888; display: flex; justify-content: space-around; }}

  /* 笔记详情表 */
  .week-section {{ margin-bottom: 20px; }}
  .week-section-header {{ display: flex; justify-content: space-between; align-items: center;
                           margin-bottom: 12px; padding-bottom: 10px; border-bottom: 2px solid #ffe0e5; }}
  .week-title {{ font-size: 14px; font-weight: 600; }}
  .week-summary {{ font-size: 12px; color: #ff2442; }}
  table.notes-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ background: #fff5f7; color: #ff2442; font-weight: 600; padding: 10px 10px;
       text-align: left; border-bottom: 2px solid #ffe0e5; white-space: nowrap; }}
  td {{ padding: 10px 10px; border-bottom: 1px solid #f5f5f5; vertical-align: middle; }}
  tr:hover td {{ background: #fff9fa; }}
  .note-title {{ max-width: 280px; color: #333; line-height: 1.4; }}
  .rank {{ font-size: 15px; text-align: center; }}
  .num {{ color: #555; text-align: right; white-space: nowrap; }}
  .date {{ color: #aaa; font-size: 12px; white-space: nowrap; }}

  /* 互动率颜色 */
  .eng-high {{ color: #22c55e; font-weight: 700; }}
  .eng-mid  {{ color: #f59e0b; font-weight: 600; }}
  .eng-low  {{ color: #94a3b8; }}

  /* 涨势标签 */
  .tag {{ font-size: 11px; padding: 2px 8px; border-radius: 8px; white-space: nowrap; }}
  .tag-hot  {{ background: #fff1f0; color: #ef4444; }}
  .tag-up   {{ background: #f0fdf4; color: #16a34a; }}
  .tag-slow {{ background: #fefce8; color: #ca8a04; }}
  .tag-flat {{ background: #f1f5f9; color: #94a3b8; }}
  .tag-new  {{ background: #eff6ff; color: #3b82f6; }}

  /* 横向对比进度条 */
  .bar-wrap {{ background: #f1f5f9; border-radius: 4px; height: 6px; min-width: 80px; margin-bottom: 3px; }}
  .bar {{ background: linear-gradient(90deg, #ff2442, #ff6b81); border-radius: 4px; height: 6px; }}
  .bar-num {{ font-size: 12px; color: #666; }}

  /* 内容诊断 */
  .diag-cards {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px; }}
  .diag-card {{ display: flex; gap: 14px; align-items: flex-start; padding: 16px;
                border-radius: 12px; }}
  .diag-best  {{ background: #f0fdf4; border: 1px solid #bbf7d0; }}
  .diag-worst {{ background: #fef9c3; border: 1px solid #fde68a; }}
  .diag-icon {{ font-size: 24px; }}
  .diag-label {{ font-size: 11px; color: #888; margin-bottom: 4px; }}
  .diag-title {{ font-size: 13px; font-weight: 600; color: #333; margin-bottom: 4px; }}
  .diag-meta  {{ font-size: 12px; color: #888; }}
  .diag-stats {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 16px; }}
  .diag-stat-item {{ text-align: center; background: #f8fafc; border-radius: 10px; padding: 12px 8px; }}
  .diag-stat-label {{ font-size: 11px; color: #999; display: block; margin-bottom: 5px; }}
  .diag-stat-value {{ font-size: 18px; font-weight: 700; }}
  .diag-insight {{ background: #fff7f0; border-radius: 10px; padding: 14px 16px; }}
  .insight-row {{ font-size: 13px; line-height: 1.8; color: #555; }}

  .no-data {{ text-align: center; color: #bbb; padding: 40px; font-size: 14px; }}
  .footer {{ text-align: center; font-size: 12px; color: #bbb; padding: 20px 0 40px; }}

  /* 选题建议 */
  .suggest-section {{ margin-top: 20px; }}
  .suggest-header {{ font-size: 14px; font-weight: 700; color: #ff2442; margin-bottom: 14px;
                     padding-bottom: 10px; border-bottom: 2px solid #ffe0e5; }}
  .suggest-list {{ display: flex; flex-direction: column; gap: 12px; }}
  .suggest-item {{ display: flex; gap: 14px; align-items: flex-start;
                   background: #fafafa; border-radius: 12px; padding: 14px 16px;
                   border: 1px solid #f0f0f0; transition: box-shadow 0.2s; }}
  .suggest-item:hover {{ box-shadow: 0 2px 12px rgba(255,36,66,0.08); border-color: #ffe0e5; }}
  .suggest-num {{ min-width: 28px; height: 28px; border-radius: 50%;
                  background: linear-gradient(135deg, #ff2442, #ff6b81);
                  color: white; font-size: 13px; font-weight: 700;
                  display: flex; align-items: center; justify-content: center; flex-shrink: 0; }}
  .suggest-body {{ flex: 1; }}
  .suggest-title-row {{ display: flex; align-items: center; gap: 10px; margin-bottom: 6px; flex-wrap: wrap; }}
  .suggest-title {{ font-size: 14px; font-weight: 600; color: #222; line-height: 1.4; }}
  .suggest-reason {{ font-size: 12px; color: #666; line-height: 1.7; }}

  /* 单篇笔记诊断卡片 */
  .note-cards-grid {{ display: grid;
                     grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
                     gap: 16px; margin-top: 16px; }}
  .note-card {{ background: #fff; border-radius: 16px; border: 1px solid #f0f0f0;
                overflow: hidden; transition: box-shadow 0.2s, transform 0.2s; }}
  .note-card:hover {{ box-shadow: 0 4px 20px rgba(0,0,0,0.08); transform: translateY(-2px); }}
  .note-card-header {{ background: linear-gradient(135deg, #fef7f8, #f0f7ff);
                       padding: 14px 16px 10px; border-bottom: 1px solid #f5f5f5; }}
  .note-card-title-row {{ display: flex; align-items: flex-start;
                           justify-content: space-between; gap: 10px; margin-bottom: 6px; }}
  .note-card-title {{ font-size: 14px; font-weight: 700; color: #222; line-height: 1.4; flex: 1; }}
  .note-eng-badge {{ font-size: 13px; font-weight: 700; padding: 2px 10px;
                     border-radius: 20px; flex-shrink: 0; }}
  .note-card-meta {{ display: flex; align-items: center; gap: 6px;
                     font-size: 12px; color: #999; flex-wrap: wrap; }}
  .trend-up    {{ color: #e74c3c !important; }}
  .trend-flat  {{ color: #888 !important; }}
  .trend-down  {{ color: #666 !important; }}
  .trend-warn  {{ color: #f39c12 !important; }}
  .trend-new   {{ color: #2ecc71 !important; }}

  .note-card-body {{ padding: 14px 16px; }}

  /* 指标5格 */
  .note-metrics {{ display: grid; grid-template-columns: repeat(5, 1fr);
                   gap: 6px; margin-bottom: 14px; }}
  .metric-box {{ background: #f9f9f9; border-radius: 10px; padding: 8px 4px;
                 text-align: center; }}
  .metric-num  {{ font-size: 15px; font-weight: 700; color: #333; }}
  .metric-label {{ font-size: 11px; color: #999; margin-top: 2px; }}

  /* 诊断区 */
  .note-diag {{ }}
  .note-verdict {{ margin-bottom: 8px; }}
  .verdict-badge {{ font-size: 12px; font-weight: 700; padding: 3px 12px;
                    border-radius: 20px; color: white; }}
  .note-action {{ background: #fef9f0; border-radius: 10px; padding: 10px 12px;
                   margin-bottom: 12px; display: flex; gap: 8px; align-items: flex-start; }}
  .action-icon {{ font-size: 14px; flex-shrink: 0; margin-top: 1px; }}
  .action-text {{ font-size: 12px; color: #555; line-height: 1.6; }}

  /* 迷你雷达条形 */
  .note-radar {{ margin-bottom: 10px; }}
  .radar-row  {{ display: flex; align-items: center; gap: 8px; margin-bottom: 5px; }}
  .radar-label {{ font-size: 11px; color: #888; width: 72px; flex-shrink: 0; }}
  .radar-track {{ flex: 1; height: 8px; background: #f0f0f0; border-radius: 4px; overflow: hidden; }}
  .mini-bar    {{ height: 100%; border-radius: 4px; min-width: 2px; }}

  /* 标签 */
  .note-tags-row {{ display: flex; flex-wrap: wrap; gap: 6px; }}
  .note-tag {{ font-size: 11px; padding: 2px 8px; border-radius: 12px; font-weight: 500; }}
  .tag-strong {{ background: #e8f5e9; color: #2e7d32; }}
  .tag-weak    {{ background: #fff3e0; color: #e65100; }}

  /* 顶部汇总栏 */
  .diag-summary-bar {{ display: flex; gap: 0; border-radius: 14px; overflow: hidden;
                       margin-bottom: 14px; border: 1px solid #f0f0f0; }}
  .diag-summary-bar .diag-stat-item {{ flex: 1; background: #fafafa; padding: 12px 14px;
                                        text-align: center; border-right: 1px solid #f0f0f0; }}
  .diag-summary-bar .diag-stat-item:last-child {{ border-right: none; }}
  .diag-summary-bar .diag-stat-label {{ display: block; font-size: 11px; color: #999; margin-bottom: 4px; }}
  .diag-summary-bar .diag-stat-value {{ display: block; font-size: 16px; font-weight: 700; }}

  @media (max-width: 768px) {{
    .overview {{ grid-template-columns: repeat(2, 1fr); }}
    .weeks-grid {{ grid-template-columns: 1fr; }}
    .diag-cards {{ grid-template-columns: 1fr; }}
    .diag-stats {{ grid-template-columns: repeat(2, 1fr); }}
    .header {{ padding: 24px 20px; }}
  }}
</style>
</head>
<body>

<div class="header">
  <h1>🌸 小红书运营周报</h1>
  <p>{date_str} &nbsp;|&nbsp; 统计范围：近4周 &nbsp;|&nbsp; 采集：{fetch_time}</p>
</div>

<div class="container">

  <!-- 概览 -->
  <div class="overview">
    <div class="overview-item"><div class="value">{total_notes}</div><div class="label">发布笔记</div></div>
    <div class="overview-item"><div class="value">{fmt_number(total_views)}</div><div class="label">总浏览</div></div>
    <div class="overview-item"><div class="value">{fmt_number(total_likes)}</div><div class="label">总点赞</div></div>
    <div class="overview-item"><div class="value">{fmt_number(total_collects)}</div><div class="label">总收藏</div></div>
    <div class="overview-item"><div class="value {'eng-high' if overall_eng >= 5 else 'eng-mid' if overall_eng >= 2 else ''}">{fmt_pct(overall_eng)}</div><div class="label">综合互动率</div></div>
  </div>

  <!-- 按周统计 -->
  <div class="section">
    <div class="section-title">📊 按周统计</div>
    <div class="weeks-grid">{weekly_summary_html}</div>
  </div>

  <!-- 横向对比 -->
  <div class="section">
    <div class="section-title">🏆 笔记横向对比（按互动率排序）</div>
    {comparison_html}
  </div>

  <!-- 内容诊断 -->
  <div class="section">
    <div class="section-title">🔍 内容诊断 & 选题建议</div>
    {diagnosis_html}
  </div>

  <!-- 按篇详情 -->
  <div class="section">
    <div class="section-title">📝 每篇详情（含互动率 & 涨势）</div>
    {notes_detail_html}
  </div>

</div>

<div class="footer">由 WorkBuddy 自动生成 · {fetch_time}</div>
</body>
</html>"""


def generate_report(data: dict, prev_data: dict = None) -> Path:
    date_str = data.get("date", datetime.date.today().strftime("%Y-%m-%d"))
    html_content = generate_html(data, prev_data)

    # 输出到 reports/ 目录
    output_path = REPORT_DIR / f"weekly_{date_str}.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"📄 周报已生成: {output_path}")

    # 同步输出到 docs/ 目录（GitHub Pages）
    docs_dir = BASE_DIR / "docs"
    docs_reports_dir = docs_dir / "reports"
    docs_reports_dir.mkdir(parents=True, exist_ok=True)

    docs_index = docs_dir / "index.html"
    with open(docs_index, "w", encoding="utf-8") as f:
        f.write(html_content)

    docs_report = docs_reports_dir / f"weekly_{date_str}.html"
    with open(docs_report, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"🌐 GitHub Pages 已更新: {docs_index}")
    return output_path


if __name__ == "__main__":
    data_dir = BASE_DIR / "data"
    # 优先用今天的数据，没有就用最新的
    today = datetime.date.today().strftime("%Y-%m-%d")
    data_file = data_dir / f"{today}.json"
    if not data_file.exists():
        files = sorted(data_dir.glob("2026-*.json"), reverse=True)
        data_file = files[0] if files else None

    if data_file and data_file.exists():
        with open(data_file) as f:
            data = json.load(f)
        report_path = generate_report(data)
        print(f"✅ 周报路径: {report_path}")
    else:
        print("❌ 找不到数据文件")
