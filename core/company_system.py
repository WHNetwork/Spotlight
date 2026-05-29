from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Tuple

from core.models import GameState, SystemEvent


COMPANY_STYLES = ["舞台型", "音源型", "视觉概念型", "海外市场导向", "综艺营销型", "数据导向"]


def _stable_pick(seed: str, options: List[str]) -> str:
    if not options:
        return ""
    h = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return options[int(h[:8], 16) % len(options)]


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
        source_system="company",
        suggested_diff=diff or {},
        new_flags=flags or [title],
        tags=["company"],
    )


def _size_label(state: GameState) -> str:
    return str(state.company.get("公司规模") or "中型公司")


def _style_from_character(state: GameState) -> str:
    character = state.character if isinstance(state.character, dict) else {}
    raw = str(character.get("公司风格") or character.get("公司路线") or "").strip()
    if raw in COMPANY_STYLES:
        return raw
    seed = f"{state.save_name}|{character.get('身份', '')}|{character.get('特长', '')}|{_size_label(state)}"
    return _stable_pick(seed, COMPANY_STYLES)


def ensure_company_profile(state: GameState) -> None:
    if not isinstance(getattr(state, "company", None), dict):
        state.company = {}
    comp = state.company
    size = str(comp.get("公司规模") or "中型公司")
    comp.setdefault("公司名称", "未命名娱乐公司")
    comp.setdefault("公司规模", size)
    comp.setdefault("公司风格", _style_from_character(state))
    comp.setdefault("财务状况", 58 if size == "中型公司" else 74 if size == "大型公司" else 36)
    comp.setdefault("现役团体资源", 62 if size == "大型公司" else 45 if size == "中型公司" else 24)
    comp.setdefault("练习生人数", 72 if size == "大型公司" else 34 if size == "中型公司" else 14)
    comp.setdefault("内部派系", ["经纪组", "制作组", "宣传组", "法务", "造型团队"])
    comp.setdefault("母公司项目优先级", 50 if size != "大厂子公司" else 38)
    comp.setdefault("新团准备度", 25)
    comp.setdefault("内部培养方向", "未公开")


def evaluate_company_system(state: GameState, action: str) -> Tuple[List[SystemEvent], Dict[str, int]]:
    ensure_company_profile(state)
    events: List[SystemEvent] = []
    diff: Dict[str, int] = {}
    comp = state.company
    style = str(comp.get("公司风格", ""))
    resource_pool = int(comp.get("资源池", 50))
    launch_pressure = int(comp.get("出道窗口压力", 45))
    company_attention = any(w in action for w in ["公司", "会议", "资源", "老师", "经纪人", "主管", "代表", "考核", "评估"])

    if company_attention and resource_pool <= 35:
        events.append(_event(
            "company_low_resource_pressure",
            "公司资源池偏低",
            "公司资源池偏低，课程、宣传、妆造或展示机会会更容易被压缩。争取资源会同步抬高竞争和心理压力。",
            "warning",
            {"团队关系.队内竞争度": 2, "心理状态.精神压力": 2, "公司与合约.公司满意度": -1},
            ["低资源公司压力"],
        ))

    if state.is_trainee_stage() and launch_pressure >= 68 and any(w in action for w in ["出道", "考核", "月末", "评估", "出道组"]):
        events.append(_event(
            "company_debut_window_pressure",
            "出道窗口压力上升",
            "公司正在用出道窗口倒逼练习生竞争。能力提升会更快被看见，但宿舍和练习室里的摩擦也会变多。",
            "warning",
            {"团队关系.队内竞争度": 3, "风险.霸凌排挤风险": 2, "公司与合约.主推指数": 1},
            ["出道窗口压力可见"],
        ))

    style_diff = {
        "舞台型": {"职业属性.舞蹈实力": 1, "身体状态.肌肉疲劳": 1},
        "音源型": {"职业属性.声乐实力": 1, "市场.音源潜力": 1},
        "视觉概念型": {"职业属性.形象指数": 1, "市场.短视频传播力": 1},
        "海外市场导向": {"职业属性.语言能力": 1, "市场.海外流媒潜力": 1},
        "综艺营销型": {"职业属性.综艺感": 1, "市场.话题度": 1},
        "数据导向": {"市场.直拍传播力": 1, "粉丝与舆论.唯粉攻击性": 1},
    }
    if company_attention and style in style_diff:
        events.append(_event(
            "company_style_bias",
            f"公司风格偏向：{style}",
            "公司风格会影响老师、制作组和宣传组看重的指标。模型叙事需要把它写成具体安排，而不是抽象说明。",
            "info",
            style_diff[style],
            [f"公司风格偏向：{style}"],
        ))

    for ev in events:
        for key, value in ev.suggested_diff.items():
            diff[key] = diff.get(key, 0) + value
    return events, diff
