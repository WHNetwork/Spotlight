from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List


class CharacterValidationError(Exception):
    def __init__(self, errors: List[str]) -> None:
        self.errors = errors
        super().__init__("\n".join(errors))


@dataclass
class NormalizedCharacter:
    data: Dict[str, Any]
    warnings: List[str]


def _to_int(value: Any, field_name: str, errors: List[str], min_v: int, max_v: int) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    m = re.search(r"\d+", text)
    if not m:
        errors.append(f"{field_name} 必须包含数字。")
        return None
    num = int(m.group())
    if not (min_v <= num <= max_v):
        errors.append(f"{field_name} 应在 {min_v}—{max_v} 之间。")
        return None
    return num


def validate_character_input(raw: Dict[str, Any]) -> NormalizedCharacter:
    errors: List[str] = []
    warnings: List[str] = []
    data = dict(raw)

    art_name = str(data.get("艺名", "")).strip()
    real_name = str(data.get("本名", "")).strip()
    if not art_name and not real_name:
        errors.append("艺名和本名至少填写一个。")

    age = _to_int(data.get("年龄"), "年龄", errors, 10, 45)
    height = _to_int(data.get("身高"), "身高", errors, 120, 210)
    if age is not None:
        data["年龄"] = age
    if height is not None:
        data["身高"] = height

    identity = str(data.get("身份", "")).strip()
    timeline = str(data.get("时间线", "")).strip()
    if not identity:
        errors.append("必须选择身份。")
    if not timeline:
        errors.append("必须选择时间线。")

    speciality = str(data.get("特长", "")).strip()
    weakness = str(data.get("弱项", "")).strip()
    if speciality and weakness and speciality == weakness:
        errors.append("特长和弱项不能完全相同。")
    if not speciality:
        warnings.append("未填写特长，初始属性会更平均。")
    if not weakness:
        warnings.append("未填写弱项，初始短板会由系统轻量生成。")

    # 限制过长字段，避免角色创建阶段污染 prompt。
    for key, value in list(data.items()):
        if isinstance(value, str) and len(value) > 400:
            data[key] = value[:400]
            warnings.append(f"{key} 内容过长，已截断到 400 字。")

    tags = data.get("出身来源标签", [])
    if isinstance(tags, str):
        data["出身来源标签"] = [s.strip() for s in tags.split(",") if s.strip()]
    elif not isinstance(tags, list):
        data["出身来源标签"] = []

    if errors:
        raise CharacterValidationError(errors)

    return NormalizedCharacter(data=data, warnings=warnings)
