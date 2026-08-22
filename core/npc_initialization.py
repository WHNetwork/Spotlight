from __future__ import annotations

import hashlib
import random
from typing import Dict, List, Tuple

from core.models import (
    CompanyCourse,
    CompanySize,
    GameState,
    NPCProfile,
    NPCRole,
)
from core.npc_character import build_npc_character_facts
from core.npc_names import (
    CHINESE_STYLE_NAMES,
    INTERNATIONAL_STYLE_NAMES,
    JAPANESE_STYLE_NAMES,
    KOREAN_STYLE_NAMES,
)
from core.relationships import register_npc


# ---------------------------------------------------------------------------
# NPC Initialization / Company Local Roster (Step 12)
#
# 只回答：“玩家刚进入公司时，周围有哪些长期存在、可以认识和互动的人？”
# 只建立 NPCProfile + RelationshipState（通过 Step 9 register_npc），
# 不建立 NPC AI / schedule / skills / condition / personality / memory /
# availability / NPC-to-NPC 关系等任何扩展。
#
# 规则：
# - 只用于新世界初始化一次（npcs / relationships 必须为空，否则失败）；
# - CompanySize 是唯一 roster scale 输入（style / management / resource /
#   intensity 均不影响人数与初始关系）；
# - 生成完全确定性：独立 namespace `npc-roster-bootstrap:{rng_seed}`；
# - 通过 register_npc 注册（关系初始值完全沿用 Step 9：fam=5/close=0/trust=0/tension=0）；
# - Teacher 基础硬覆盖：DANCE/VOCAL/STAGE 各至少 1 位。
# ---------------------------------------------------------------------------


class NPCInitializationError(ValueError):
    """NPC roster 初始化失败（重复初始化 / 状态非法 / 姓名池不足 / invariant 失败）。"""


_ROSTER_RULES: Dict[CompanySize, Dict[str, Tuple[int, int]]] = {
    CompanySize.SMALL: {"trainee": (4, 6), "teacher": (3, 4), "manager": (1, 1), "staff": (1, 1)},
    CompanySize.MEDIUM: {"trainee": (6, 9), "teacher": (4, 6), "manager": (1, 1), "staff": (1, 2)},
    CompanySize.LARGE: {"trainee": (8, 12), "teacher": (5, 7), "manager": (1, 1), "staff": (2, 2)},
}

# Teacher 基础硬覆盖：无论规模，至少各 1 位。
_BASE_TEACHER_SPECIALTIES: Tuple[CompanyCourse, ...] = (
    CompanyCourse.DANCE,
    CompanyCourse.VOCAL,
    CompanyCourse.STAGE,
)

# 额外老师 specialty 优先级：第一轮优先覆盖尚未出现的方向。
_EXTRA_TEACHER_SPECIALTIES: Tuple[CompanyCourse, ...] = (
    CompanyCourse.RAP,
    CompanyCourse.CAMERA,
    CompanyCourse.LANGUAGE,
    CompanyCourse.FITNESS,
    CompanyCourse.DANCE,
    CompanyCourse.VOCAL,
    CompanyCourse.STAGE,
)

_ROLE_ORDER: Tuple[NPCRole, ...] = (NPCRole.TRAINEE, NPCRole.TEACHER, NPCRole.MANAGER, NPCRole.STAFF)


def _bootstrap_rng(rng_seed: int) -> random.Random:
    """独立 bootstrap RNG：不污染 Talent / Company 等其它随机序列。"""
    namespace = f"npc-roster-bootstrap:{rng_seed}"
    derived = int(hashlib.sha256(namespace.encode("utf-8")).hexdigest()[:8], 16)
    return random.Random(derived)


def _pick_name(rng: random.Random, used_names: set, pools: List[Tuple[str, ...]]) -> str:
    """从多个池按顺序取样一个未使用、且不与玩家名冲突的名字。"""
    for pool in pools:
        for _ in range(50):
            name = pool[rng.randrange(len(pool))]
            if name not in used_names:
                return name
    raise NPCInitializationError("NPC 静态姓名池不足，无法生成唯一 display name。")


def initialize_npc_roster(game_state: GameState) -> None:
    """新世界初始化：根据 CompanySize 生成 Company Local Roster 并注册。

    前置：game_state.npcs 与 relationships 必须都为空（一次性 bootstrap，
    重复调用明确失败；load_save 不会调用本函数）。
    前置：meta.rng_seed 与 company.size 已由 allocator 设置。
    """
    if game_state.npcs or game_state.relationships:
        raise NPCInitializationError("NPC roster 已经存在，禁止重复初始化（一次性 world bootstrap）。")

    size = game_state.company.size
    if size not in _ROSTER_RULES:
        raise NPCInitializationError(f"非法 CompanySize：{size!r}，无法生成 roster。")

    rng = _bootstrap_rng(game_state.meta.rng_seed)
    rules = _ROSTER_RULES[size]

    trainee_count = rng.randint(*rules["trainee"])
    teacher_count = rng.randint(*rules["teacher"])
    manager_count = rules["manager"][0]
    staff_count = rng.randint(*rules["staff"])

    counts: Dict[NPCRole, int] = {
        NPCRole.TRAINEE: trainee_count,
        NPCRole.TEACHER: teacher_count,
        NPCRole.MANAGER: manager_count,
        NPCRole.STAFF: staff_count,
    }

    used_names: set = set()
    player = game_state.player
    for conflict in (player.name, player.stage_name):
        if conflict:
            used_names.add(conflict)

    index_by_role: Dict[NPCRole, int] = {role: 0 for role in _ROLE_ORDER}

    def make_profile(npc_id: str, name: str, role: NPCRole, specialty=None) -> NPCProfile:
        # Character Facts 使用独立 per-NPC RNG，不消耗 roster bootstrap RNG 序列。
        return NPCProfile(
            npc_id=npc_id,
            name=name,
            role=role,
            specialty=specialty,
            character_facts=build_npc_character_facts(state.meta.rng_seed, npc_id, role),
        )

    # ---- TRAINEE：Korean 为主，混入少量其他风格 ----
    for _ in range(trainee_count):
        index_by_role[NPCRole.TRAINEE] += 1
        name = _pick_name(rng, used_names, [
            KOREAN_STYLE_NAMES, CHINESE_STYLE_NAMES,
            JAPANESE_STYLE_NAMES, INTERNATIONAL_STYLE_NAMES,
        ])
        used_names.add(name)
        register_npc(game_state, make_profile(
            f"trainee_{index_by_role[NPCRole.TRAINEE]:02d}", name, NPCRole.TRAINEE,
        ))

    # ---- TEACHER：基础三位 DANCE/VOCAL/STAGE，其余按优先级覆盖 ----
    teacher_specialties: List[CompanyCourse] = []
    seen: set = set()
    for base in _BASE_TEACHER_SPECIALTIES:
        teacher_specialties.append(base)
        seen.add(base)
    for _ in range(teacher_count - len(_BASE_TEACHER_SPECIALTIES)):
        chosen = None
        for candidate in _EXTRA_TEACHER_SPECIALTIES:
            if candidate not in seen:
                chosen = candidate
                break
        if chosen is None:
            chosen = _EXTRA_TEACHER_SPECIALTIES[rng.randrange(len(_EXTRA_TEACHER_SPECIALTIES))]
        teacher_specialties.append(chosen)
        seen.add(chosen)
    for specialty in teacher_specialties:
        index_by_role[NPCRole.TEACHER] += 1
        name = _pick_name(rng, used_names, [KOREAN_STYLE_NAMES])
        used_names.add(name)
        register_npc(game_state, make_profile(
            f"teacher_{index_by_role[NPCRole.TEACHER]:02d}", name, NPCRole.TEACHER, specialty,
        ))

    # ---- MANAGER / STAFF ----
    for _ in range(manager_count):
        index_by_role[NPCRole.MANAGER] += 1
        name = _pick_name(rng, used_names, [KOREAN_STYLE_NAMES])
        used_names.add(name)
        register_npc(game_state, make_profile(
            f"manager_{index_by_role[NPCRole.MANAGER]:02d}", name, NPCRole.MANAGER,
        ))
    for _ in range(staff_count):
        index_by_role[NPCRole.STAFF] += 1
        name = _pick_name(rng, used_names, [KOREAN_STYLE_NAMES])
        used_names.add(name)
        register_npc(game_state, make_profile(
            f"staff_{index_by_role[NPCRole.STAFF]:02d}", name, NPCRole.STAFF,
        ))

    _validate_roster(game_state, size, counts)


def _validate_roster(game_state: GameState, size: CompanySize, counts: Dict[NPCRole, int]) -> None:
    """初始化后 invariants（不静默修正，失败即抛错）。"""
    npcs = game_state.npcs
    if not npcs or set(npcs.keys()) != set(game_state.relationships.keys()):
        raise NPCInitializationError("roster 初始化后 npcs/relationships key 不一致。")

    def role_count(role: NPCRole) -> int:
        return sum(1 for p in npcs.values() if p.role == role)

    rules = _ROSTER_RULES[size]
    checks = []
    for role in (NPCRole.TRAINEE, NPCRole.TEACHER, NPCRole.STAFF):
        lo, hi = rules[role.value]
        checks.append((f"{role.value} count", lo <= role_count(role) <= hi))
    checks.append(("manager count", role_count(NPCRole.MANAGER) == 1))
    checks.append(("expected totals", role_count(NPCRole.TRAINEE) == counts[NPCRole.TRAINEE]
                   and role_count(NPCRole.TEACHER) == counts[NPCRole.TEACHER]
                   and role_count(NPCRole.MANAGER) == counts[NPCRole.MANAGER]
                   and role_count(NPCRole.STAFF) == counts[NPCRole.STAFF]))

    teacher_specialties = [p.specialty for p in npcs.values() if p.role == NPCRole.TEACHER]
    for base in _BASE_TEACHER_SPECIALTIES:
        checks.append((f"teacher {base.value} coverage", base in teacher_specialties))

    names = [p.name for p in npcs.values()]
    checks.append(("name unique", len(set(names)) == len(names)))
    checks.append(("all active", all(p.active for p in npcs.values())))

    failed = [label for label, ok in checks if not ok]
    if failed:
        raise NPCInitializationError(f"roster invariant 失败：{', '.join(failed)}")
