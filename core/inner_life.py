from __future__ import annotations

from typing import Any, Dict, List, Tuple
from core.models import GameState, SystemEvent


def default_inner_life() -> Dict[str, Any]:
    return {
        "被看见的渴望": 45,
        "亲密需求": 35,
        "比较敏感": 35,
        "自我羞耻感": 25,
        "秘密重量": 10,
        "日记倾向": 35,
        "身体自我意识": 30,
        "心动值": 0,
        "对未来的幻想": 45,
    }


def _add(diff: Dict[str, int], key: str, value: int) -> None:
    diff[key] = diff.get(key, 0) + value


def _event(code: str, title: str, desc: str, severity: str = "info", diff: Dict[str, int] | None = None, flags: List[str] | None = None) -> SystemEvent:
    return SystemEvent(
        code=code,
        title=title,
        severity=severity,
        description=desc,
        source_system="inner_life",
        suggested_diff=diff or {},
        new_flags=flags or [title],
        tags=["inner_life"],
    )


def add_secret(state: GameState, secret_type: str, target: str, intensity: int, source: str, outlets: List[str] | None = None) -> None:
    outlets = outlets or ["日记", "深夜谈心", "歌词", "舞台表现"]
    # Merge similar secret if exists.
    for s in state.inner_secrets:
        if s.get("type") == secret_type and s.get("target") == target and not s.get("spoken", False):
            s["intensity"] = min(100, int(s.get("intensity", 0)) + intensity)
            s["source"] = source
            return
    state.inner_secrets.append({
        "id": f"secret_{len(state.inner_secrets)+1:03d}",
        "type": secret_type,
        "target": target,
        "intensity": max(0, min(100, intensity)),
        "spoken": False,
        "source": source,
        "outlets": outlets,
    })


def evaluate_inner_life(state: GameState, action: str) -> Tuple[List[SystemEvent], Dict[str, int]]:
    events: List[SystemEvent] = []
    diff: Dict[str, int] = {}
    inner = state.inner_life

    wants_seen = any(w in action for w in ["被看见", "被忽视", "后排", "老师没有夸", "想证明", "想被注意", "不想边缘"])
    comparison = any(w in action for w in ["羡慕", "嫉妒", "队友被夸", "别人进步", "比较"])
    body_awareness = any(w in action for w in ["脸肿", "身材", "体重", "镜子", "服装", "水肿", "身体"])
    diary = any(w in action for w in ["日记", "写下来", "歌词本", "写进歌词", "写歌", "demo"])
    talk = any(w in action for w in ["谈心", "告诉队友", "倾诉", "说出口"])
    crush = any(w in action for w in ["在意", "心动", "喜欢", "暗恋", "想靠近", "她看我", "他看我"])
    swallow = any(w in action for w in ["咽回去", "不说", "装没事", "算了", "忍住"])

    if wants_seen:
        inner["被看见的渴望"] = min(100, int(inner.get("被看见的渴望", 45)) + 8)
        inner["秘密重量"] = min(100, int(inner.get("秘密重量", 10)) + 3)
        add_secret(state, "被看见的渴望", "舞台/老师/公司", 25, "玩家表达了被看见或不想边缘化的心事")
        events.append(_event(
            "inner_visible_desire",
            "少女心事：被看见的渴望",
            "你不只是想赢。你想被看见，想让别人知道你也在努力、也有亮起来的部分。",
            "info",
            {"心理状态.自我认同": 1, "心理状态.精神压力": 1},
            ["心事：被看见的渴望"],
        ))

    if comparison:
        inner["比较敏感"] = min(100, int(inner.get("比较敏感", 35)) + 8)
        inner["秘密重量"] = min(100, int(inner.get("秘密重量", 10)) + 4)
        add_secret(state, "比较与羡慕", "队友/同期", 22, "玩家对他人的进步或表扬产生酸涩")
        events.append(_event(
            "inner_comparison",
            "少女心事：比较与酸涩",
            "你替别人高兴，也在心里酸了一下。这种感觉不体面，但很真实。",
            "info",
            {"心理状态.心情": -1, "团队关系.真实关系温度": -1},
            ["心事：比较与酸涩"],
        ))

    if body_awareness:
        inner["身体自我意识"] = min(100, int(inner.get("身体自我意识", 30)) + 6)
        inner["自我羞耻感"] = min(100, int(inner.get("自我羞耻感", 25)) + 3)
        add_secret(state, "身体自我意识", "镜子/服装/镜头", 20, "玩家开始强烈注意身体和镜头里的自己")
        events.append(_event(
            "inner_body_awareness",
            "少女心事：身体自我意识",
            "镜子、服装和镜头把身体变成了被审视的对象。你开始更在意自己是不是安全、是不是好看、是不是会被误读。",
            "warning",
            {"身体状态.体重管理压力": 2, "心理状态.精神压力": 1},
            ["心事：身体自我意识"],
        ))

    if crush:
        inner["心动值"] = min(100, int(inner.get("心动值", 0)) + 8)
        inner["亲密需求"] = min(100, int(inner.get("亲密需求", 35)) + 4)
        state.crush_threads.append({
            "id": f"crush_{len(state.crush_threads)+1:03d}",
            "target": "未明确对象",
            "intensity": inner["心动值"],
            "certainty": 15,
            "notes": "玩家出现了心动/在意相关表达，但对象态度与性取向未知。",
        })
        add_secret(state, "心动线索", "未明确对象", 18, "玩家表达了在意或心动")
        events.append(_event(
            "inner_crush_signal",
            "少女心事：心动线索",
            "这不是恋爱结论，只是一点被你自己先察觉到的在意。对方怎么想、边界在哪里，都还不知道。",
            "info",
            {"心理状态.心情": 1, "风险.恋爱风险": 1},
            ["心事：心动线索"],
        ))

    if diary:
        inner["日记倾向"] = min(100, int(inner.get("日记倾向", 35)) + 5)
        inner["秘密重量"] = max(0, int(inner.get("秘密重量", 10)) - 6)
        _add(diff, "心理状态.精神压力", -3)
        if state.career.get("创作能力", 0) >= 8:
            _add(diff, "职业属性.创作能力", 1)
        # Lower active secret intensities.
        for s in state.inner_secrets[-5:]:
            s["intensity"] = max(0, int(s.get("intensity", 0)) - 8)
        events.append(_event(
            "inner_diary_outlet",
            "心事出口：写下来",
            "你没有立刻把话说给别人听，而是把它写下来。那些说不出口的东西暂时有了容器。",
            "info",
            diff.copy(),
            ["心事出口：日记/歌词"],
        ))

    if talk:
        inner["秘密重量"] = max(0, int(inner.get("秘密重量", 10)) - 8)
        _add(diff, "团队关系.真实关系温度", 2)
        _add(diff, "心理状态.孤独感", -3)
        for s in state.inner_secrets[-5:]:
            s["spoken"] = True
            s["intensity"] = max(0, int(s.get("intensity", 0)) - 12)
        events.append(_event(
            "inner_talk_outlet",
            "心事出口：说出口",
            "你把一部分心事说了出来。关系不会因此立刻变完美，但秘密的重量减轻了一点。",
            "info",
            diff.copy(),
            ["心事出口：深夜谈心"],
        ))

    if swallow:
        inner["秘密重量"] = min(100, int(inner.get("秘密重量", 10)) + 5)
        _add(diff, "心理状态.精神压力", 2)
        _add(diff, "心理状态.孤独感", 2)
        events.append(_event(
            "inner_swallowed_words",
            "少女心事：把话咽回去",
            "你把话又咽了回去。表面上什么都没有发生，心里的重量却增加了。",
            "warning",
            diff.copy(),
            ["心事：把话咽回去"],
        ))

    # Passive triggers from state
    if int(inner.get("被看见的渴望", 0)) > 75 and state.mind.get("自我认同", 100) < 45:
        events.append(_event(
            "inner_desire_threshold",
            "心事阈值：想被看见",
            "你越来越难接受自己总是被轻轻放过。不是被批评，而是被忽略，这更慢地消耗你。",
            "warning",
            {"心理状态.精神压力": 2},
            ["心事阈值：想被看见"],
        ))

    if int(inner.get("秘密重量", 0)) > 70:
        events.append(_event(
            "inner_secret_weight_high",
            "秘密重量过高",
            "未说出口的东西积得太多，开始影响睡眠、表达和关系判断。",
            "warning",
            {"心理状态.睡眠质量": -1} if False else {"心理状态.精神压力": 2, "心理状态.孤独感": 2},
            ["秘密重量过高"],
        ))

    return events, diff
