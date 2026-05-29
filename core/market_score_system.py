from __future__ import annotations

import hashlib
from typing import Dict, List, Tuple

from core.models import GameState, SystemEvent


def _event(
    code: str,
    title: str,
    desc: str,
    severity: str = "info",
    diff: Dict[str, int] | None = None,
    flags: List[str] | None = None,
) -> SystemEvent:
    return SystemEvent(
        code=code,
        title=title,
        severity=severity,
        description=desc,
        source_system="market_score",
        suggested_diff=diff or {},
        new_flags=flags or [title],
        tags=["market_score"],
    )


def _stable_variance(seed: str, span: int = 12) -> int:
    h = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return int(h[:8], 16) % (span * 2 + 1) - span


def clamp(v: int, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, int(v)))


def ensure_market_score_state(state: GameState) -> None:
    if not isinstance(getattr(state, "market_scores", None), dict):
        state.market_scores = {}
    ms = state.market_scores
    ms.setdefault("音源成绩", 0)
    ms.setdefault("专辑销量指数", 0)
    ms.setdefault("首日销量", 0)
    ms.setdefault("首周销量", 0)
    ms.setdefault("MV播放指数", 0)
    ms.setdefault("短视频传播力", int(state.market.get("短视频传播力", 25)))
    ms.setdefault("直拍传播力", int(state.market.get("直拍传播力", 20)))
    ms.setdefault("投票动员力", 0)
    ms.setdefault("音乐节目分数", 0)
    ms.setdefault("一位概率", 0)
    ms.setdefault("年度奖项积分", 0)
    ms.setdefault("本土热度", int(state.market.get("韩国本土影响力", 0)))
    ms.setdefault("海外流媒", int(state.market.get("海外流媒潜力", 0)))
    ms.setdefault("品牌询盘量", 0)
    ms.setdefault("路人盘", int(state.fans.get("路人好感", 40)))
    ms.setdefault("核心粉购买力", 0)
    ms.setdefault("last_market_result", "")
    ms.setdefault("history", [])


def _is_market_action(action: str) -> bool:
    return any(w in action for w in ["回归", "打歌", "一位", "榜单", "音源", "销量", "MV", "直拍", "投票", "颁奖", "获奖", "舞台成绩"])


def evaluate_market_score_system(state: GameState, action: str) -> Tuple[List[SystemEvent], Dict[str, int]]:
    ensure_market_score_state(state)
    events: List[SystemEvent] = []
    diff: Dict[str, int] = {}
    if state.is_trainee_stage() or not _is_market_action(action):
        return events, diff

    c = state.career
    m = state.market
    fans = state.fans
    comp = state.company
    risks = state.risks
    comeback = state.comeback
    ms = state.market_scores

    controversy_penalty = int(risks.get("公关危机风险", 0)) // 4 + int(comp.get("危机关注度", 0)) // 5
    company_boost = int(comp.get("资源池", 50)) // 5 + int(comp.get("资源倾斜度", 30)) // 6
    fan_base = min(100, int(fans.get("团体粉丝数", 0)) // 5000 + int(fans.get("个人粉丝数", 0)) // 3500)
    song_fit = int(comeback.get("风格适配度", 50))
    variance = _stable_variance(f"{state.save_name}|{state.turn}|{action}", 10)

    audio = clamp(0.32 * song_fit + 0.20 * int(m.get("音源潜力", 30)) + 0.18 * int(fans.get("路人好感", 40)) + 0.15 * int(m.get("韩国本土影响力", 0)) + 0.15 * company_boost - controversy_penalty + variance)
    sales = clamp(0.35 * fan_base + 0.25 * int(fans.get("团粉稳定度", 50)) + 0.20 * int(fans.get("唯粉规模", 0)) + 0.20 * company_boost - controversy_penalty + variance)
    mv = clamp(0.25 * int(m.get("话题度", 15)) + 0.22 * int(c.get("形象指数", 5)) + 0.20 * int(c.get("舞蹈实力", 0)) + 0.18 * int(m.get("短视频传播力", 25)) + 0.15 * company_boost + variance)
    fancam = clamp(0.32 * int(c.get("舞台感染力", 0)) + 0.24 * int(c.get("舞蹈实力", 0)) + 0.18 * int(c.get("形象指数", 0)) + 0.16 * int(m.get("话题度", 15)) + 0.10 * fan_base + variance)
    voting = clamp(0.45 * fan_base + 0.28 * int(fans.get("粉丝信任基础", 50)) + 0.27 * int(fans.get("站姐稳定度", 50)) - int(fans.get("粉圈撕裂度", 0)) // 3)
    music_show = clamp(0.30 * audio + 0.25 * sales + 0.20 * voting + 0.15 * mv + 0.10 * int(m.get("话题度", 15)) - controversy_penalty)
    first_win = clamp((music_show - 45) * 2)

    ms.update({
        "音源成绩": int(audio),
        "专辑销量指数": int(sales),
        "首日销量": max(0, int(sales * 900 + fan_base * 120)),
        "首周销量": max(0, int(sales * 5200 + fan_base * 680)),
        "MV播放指数": int(mv),
        "短视频传播力": int(m.get("短视频传播力", 25)),
        "直拍传播力": int(fancam),
        "投票动员力": int(voting),
        "音乐节目分数": int(music_show),
        "一位概率": int(first_win),
        "本土热度": int(m.get("韩国本土影响力", 0)),
        "海外流媒": int(m.get("海外流媒潜力", m.get("欧美市场影响力", 0))),
        "路人盘": int(fans.get("路人好感", 40)),
        "核心粉购买力": int(sales),
    })

    result = "一位候补" if 40 <= first_win < 65 else "一位强候补" if first_win >= 65 else "成绩观察期"
    ms["last_market_result"] = result
    ms["年度奖项积分"] = clamp(int(ms.get("年度奖项积分", 0)) + int((audio + sales + music_show) / 24))
    ms["品牌询盘量"] = clamp(int(ms.get("品牌询盘量", 0)) + int((audio + mv + fancam) / 30))
    ms["history"].append({"turn": state.turn + 1, "result": result, "music_show": int(music_show), "first_win_probability": int(first_win)})
    ms["history"] = ms["history"][-12:]

    if first_win >= 65:
        events.append(_event(
            "market_first_win_strong_candidate",
            "打歌一位强候补",
            "本回合综合成绩进入一位强候补区间。是否真正获奖仍要看同期对手、节目权重和粉丝动员。",
            "crisis",
            {"市场.话题度": 4, "粉丝与舆论.粉丝信任基础": 2, "公司与合约.主推指数": 2},
            ["一位强候补"],
        ))
    elif first_win >= 40:
        events.append(_event(
            "market_first_win_candidate",
            "打歌一位候补",
            "综合成绩接近一位区间，但优势不稳。叙事应写成候补和焦灼数据，而不是直接获奖。",
            "warning",
            {"市场.话题度": 2, "心理状态.精神压力": 1},
            ["一位候补"],
        ))
    else:
        events.append(_event(
            "market_result_under_observation",
            "成绩进入观察期",
            "成绩没有形成压倒性优势。它可以打开瓶颈、概念调整、海外路线或个人路线测试，而不是直接失败。",
            "info",
            {"心理状态.精神压力": 2},
            ["成绩观察期"],
        ))

    if fancam >= 68:
        events.append(_event(
            "market_fancam_breakout",
            "直拍传播上升",
            "个人直拍开始变成资源信号。它会提高主推指数和唯粉规模，也可能推高队内资源落差。",
            "warning",
            {"公司与合约.主推指数": 3, "粉丝与舆论.唯粉规模": 2, "团队关系.队内竞争度": 2},
            ["直拍传播上升"],
        ))

    for ev in events:
        for key, value in ev.suggested_diff.items():
            diff[key] = diff.get(key, 0) + value
    return events, diff
