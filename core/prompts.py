from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Any
from loguru import logger
from core.models import GameState, RouteInfo, SystemEvent
from core.rules import threshold_warnings
from core.action_validator import ActionValidationResult

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SYSTEM_PROMPT_PATH = DATA_DIR / "system_prompt.md"
MODULES_DIR = DATA_DIR / "modules"

def _read_md(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()

def load_system_prompt() -> str:
    sections: list[str] = []
    if SYSTEM_PROMPT_PATH.exists():
        sections.append(_read_md(SYSTEM_PROMPT_PATH))
    if MODULES_DIR.exists():
        for path in sorted(MODULES_DIR.glob("*.md")):
            sections.append(f"\n---\n\n<!-- MODULE: {path.name} -->\n\n{_read_md(path)}")
    return "\n\n".join(section for section in sections if section.strip())

def list_prompt_modules() -> List[str]:
    if not MODULES_DIR.exists():
        return []
    return [path.name for path in sorted(MODULES_DIR.glob("*.md"))]

def backend_rule_contract() -> Dict[str, object]:
    return {
        "response_schema": "TurnResponse JSON only: narrative, npc_reactions, choices, suggested_diff, new_flags, resolved_flags, public_summary, private_notes.",
        "python_owned_systems": [
            "company_system: 公司规模、公司风格、资源池、出道窗口、公司偏向。",
            "trainee_life_system: 每周时间格、练习生排挤/冷处理、宿舍与练习室压力。",
            "relationship_system: 新人物解锁后建档，关系值、CP资格、职业边界。",
            "market_score_system: 音源、销量、MV、直拍、投票、打歌一位概率和奖项积分。",
            "career_branch_system: 演员、Solo/Unit、创作、暂停/维权/退出等职业分岔。",
            "brand_contract_system: 商业安全度、品牌机会、个人收入、续约谈判条款。",
        ],
        "model_rules": [
            "不要直接宣布 Python 判定型结果必然成功，例如一位、获奖、续约成功、转型成功；需要依据 system_events 和 game_state 写成候补、机会、谈判或后果。",
            "suggested_diff 只能补充叙事造成的小幅变化；核心结算以 base_diff_calculated_by_python 与 system_diff_calculated_by_python 为准；所有 suggested_diff 数值必须是整数，不要输出 0.5、1.5 这类小数。",
            "如果玩家行动包含【本周安排】，本回合时间跨度是一周。普通事件写成周常训练/生活推进；重点事件写成这一周中的关键场景；危机事件写成危机在本周内爆发与处理；主线事件写成阶段节点在这一周内推进。",
            "npc_reactions 可以带 role 和 age 字段；出现新人物时必须写明完整韩国姓名（如金多贤、李瑞渊），不得用外型描述（如短发女生、戴眼镜的前辈、高个子男生）代替姓名。后端会根据姓名建立关系档案，无名NPC不会被记录。",
            "不要凭空塞固定默认人物；若出现新 NPC，必须让 ta 在剧情、反应或事件里自然登场。",
            "公司真实意图、NPC隐藏心动、内部培养方向等隐藏信息只能通过场景暗示，不要上帝视角直说。",
            "如果 action_validation.normalized_action 与 original_action 不同，剧情必须执行 normalized_action，不能执行 original_action。",
            "如果 system_events 中出现 warning 或 crisis，正文必须体现对应代价、限制或余波。",
            "如果 market_scores/contract_terms/career_branches 显示的是候补、测试、观察或谈判阶段，不得写成最终成功。",
        ],
        "narrative_checks": [
            "必须使用第二人称“你”。",
            "必须包含具体场景细节。",
            "必须体现至少一个状态后果或系统事件。",
            "包含【本周安排】时，正文需要体现一周内的安排消耗、重点场景和结算余波，不能只写成一个瞬间动作。",
            "不得在 JSON 外输出文字或 Markdown 代码块。",
        ],
        "diff_categories": [
            "职业属性",
            "身体状态",
            "心理状态",
            "公司与合约",
            "团队关系",
            "粉丝与舆论",
            "市场",
            "风险",
            "回归",
            "练习生日常",
            "市场成绩",
            "商业资源",
            "合约条款",
        ],
    }

POLISH_SYSTEM_PROMPT = """请只对下面文字做文风润色，不改变剧情、不改变人物关系、不新增事件。

润色目标：去除 AI 味，让文字更自然、细腻、真实、有温度。

具体要求：
1. 删除剧情总结式句子，改成具体场景和动作。
2. 删除模板化抒情（尤其是"这一刻、终于明白、像被击中、心脏漏拍、救赎、破碎、命运、光、全世界安静"等表达）。
3. 降低对话解释功能，不要让人物把内心和主题直接说透。
4. 增加生活细节和身体细节（衣角、汗、灯光、手机、鞋带、镜子、走廊声音、呼吸、停顿）。
5. 保持克制，不要过度煽情，不要频繁哭、抱、崩溃。
6. 保持原文信息量，只优化语言质感和叙事流动性。

请直接输出润色后的正文，不要解释修改原因。"""


def polish_narrative(original: str, provider, flash_model: str) -> str:
    """对已生成的叙事文本进行文风润色，去除 AI 味。失败则返回原文。"""
    if not original or not original.strip():
        return original
    try:
        messages = [
            {"role": "system", "content": POLISH_SYSTEM_PROMPT},
            {"role": "user", "content": original},
        ]
        result = provider.generate(messages, model=flash_model, json_mode=False)
        if result and result.strip():
            return result.strip()
    except Exception:
        logger.exception("polish_narrative failed")
    return original


def build_messages(
    state: GameState,
    player_action: str,
    base_diff: Dict[str, int],
    system_diff: Dict[str, int],
    system_events: List[SystemEvent],
    route_info: RouteInfo,
    validation: ActionValidationResult,
) -> List[Dict[str, str]]:
    ch = state.character if isinstance(state.character, dict) else {}
    user_payload = {
        "instruction": "请根据当前 GameState、玩家行动、行动合法性检查、Python 规则事件和 diff 生成下一回合。只返回 JSON。",
        "turn_time_contract": {
            "has_weekly_plan": "【本周安排】" in validation.normalized_action,
            "rule": "包含【本周安排】时，本回合按一周生成；route_info.turn_kind 只决定叙事重心和模型层级，不缩短这一周。",
            "ordinary": "普通事件：写周常训练、生活、恢复和小摩擦的推进。",
            "focus": "重点事件：写一周安排中被镜头放大的关键场景，同时交代其他安排的消耗。",
            "crisis": "危机事件：写危机在这一周内爆发、处理和留下的余波。",
            "mainline": "主线事件：写职业阶段节点在这一周内推进，但不越过 Python 尚未确认的结果。",
        },
        "personality_guidance": {
            "mbti": ch.get("MBTI"),
            "mbti_profile": ch.get("MBTI人格倾向"),
            "rule": "MBTI只作为角色反应倾向、关系节奏、压力表达和日记语气的稳定器；不要写成人格测试说明，不要让角色刻板化。"
        },
        "prompt_mode": "phase2_1_action_gated_systems",
        "loaded_modules": list_prompt_modules(),
        "backend_rule_contract": backend_rule_contract(),
        "route_info": route_info.model_dump(),
        "action_validation": validation.model_dump(),
        "player_action_original": validation.original_action,
        "player_action_normalized": validation.normalized_action,
        "base_diff_calculated_by_python": base_diff,
        "system_diff_calculated_by_python": system_diff,
        "system_events": [e.model_dump() for e in system_events],
        "threshold_warnings": threshold_warnings(state),
        "game_state": state.as_prompt_dict(),
    }
    return [
        {"role": "system", "content": load_system_prompt()},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False, indent=2)},
    ]
