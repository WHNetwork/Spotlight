from __future__ import annotations

import hashlib
from typing import Dict
from core.models import GameState


TALENT_KEYS = [
    "舞蹈天赋", "声乐天赋", "RAP天赋", "镜头天赋", "综艺天赋",
    "语言天赋", "演技天赋", "创作天赋", "体能天赋", "抗压天赋", "社交天赋"
]


def _stable_int(seed: str, low: int = 35, high: int = 75) -> int:
    h = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    val = int(h[:8], 16)
    return low + (val % (high - low + 1))


def generate_talents(character: Dict[str, object]) -> Dict[str, int]:
    base_seed = "|".join(str(character.get(k, "")) for k in ["艺名", "本名", "身份", "特长", "弱项"])
    talents = {k: _stable_int(base_seed + k) for k in TALENT_KEYS}

    identity = str(character.get("身份", ""))
    speciality = str(character.get("特长", ""))
    weakness = str(character.get("弱项", ""))

    def boost(key: str, amount: int) -> None:
        talents[key] = max(0, min(100, talents[key] + amount))

    if "运动员" in identity:
        boost("体能天赋", 18)
        boost("舞蹈天赋", 8)
        boost("抗压天赋", 8)
    if "海外" in identity:
        boost("语言天赋", 12)
        boost("抗压天赋", 6)
    if "选秀" in identity:
        boost("镜头天赋", 10)
        boost("舞台天赋" if "舞台天赋" in talents else "镜头天赋", 0)
    if "富二代" in identity or "优渥" in identity:
        boost("声乐天赋", 5)
        boost("创作天赋", 5)

    mapping = [
        ("舞", "舞蹈天赋"),
        ("声乐", "声乐天赋"),
        ("唱", "声乐天赋"),
        ("rap", "RAP天赋"),
        ("RAP", "RAP天赋"),
        ("语言", "语言天赋"),
        ("演技", "演技天赋"),
        ("作词", "创作天赋"),
        ("作曲", "创作天赋"),
        ("综艺", "综艺天赋"),
    ]

    for word, key in mapping:
        if word in speciality:
            boost(key, 12)
        if word in weakness:
            boost(key, -12)

    return talents


def apply_talent_modifiers(state: GameState, action: str, diff: Dict[str, int]) -> Dict[str, int]:
    text = action.lower()
    out = dict(diff)

    def add(key: str, value: int) -> None:
        out[key] = out.get(key, 0) + value

    if ("舞" in action or "练习" in action) and state.talents.get("舞蹈天赋", 50) >= 75:
        add("职业属性.舞蹈实力", 1)
    if ("声乐" in action or "唱" in action) and state.talents.get("声乐天赋", 50) >= 75:
        add("职业属性.声乐实力", 1)
    if ("作词" in action or "作曲" in action or "demo" in text) and state.talents.get("创作天赋", 50) >= 75:
        add("职业属性.创作能力", 1)

    if state.talents.get("体能天赋", 50) >= 75 and any(w in action for w in ["练舞", "舞蹈", "高强度"]):
        add("身体状态.肌肉疲劳", -1)
        add("身体状态.体力", 1)

    if state.talents.get("抗压天赋", 50) >= 75 and any(w in action for w in ["回应", "考核", "面谈", "公关"]):
        add("心理状态.精神压力", -1)

    return out
