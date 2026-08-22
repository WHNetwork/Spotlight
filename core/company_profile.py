from __future__ import annotations

import hashlib
from dataclasses import dataclass

from core.models import CompanySize, ManagementStyle, TrainingStyle


@dataclass(frozen=True)
class CompanyProfile:
    training_style: TrainingStyle
    management_style: ManagementStyle
    training_intensity: int
    resource_level: int


_RESOURCE_RANGE: dict[CompanySize, tuple[int, int]] = {
    CompanySize.LARGE: (70, 95),
    CompanySize.MEDIUM: (45, 75),
    CompanySize.SMALL: (20, 55),
}


def _stable_int(namespace: str, low: int, high: int) -> int:
    """由 sha256 命名空间派生 [low, high] 内的稳定整数。

    跨进程、跨运行完全确定；不使用 Python 内置 hash()。
    """
    digest = hashlib.sha256(namespace.encode("utf-8")).hexdigest()
    return low + (int(digest[:8], 16) % (high - low + 1))


def derive_company_profile(size: CompanySize, rng_seed: int) -> CompanyProfile:
    """由存档 rng_seed 确定性生成公司画像。

    所有随机量都来自 sha256 派生子种子（namespace: company-profile:{rng_seed}），
    同一存档每次重建画像完全一致。

    只有 resource_level 受 size 的范围约束（三个区间故意重叠）；
    training_style / management_style / training_intensity 与规模完全无关。
    """
    namespace = f"company-profile:{rng_seed}"

    styles = list(TrainingStyle)
    managements = list(ManagementStyle)

    training_style = styles[_stable_int(f"{namespace}:style", 0, len(styles) - 1)]
    management_style = managements[_stable_int(f"{namespace}:management", 0, len(managements) - 1)]
    training_intensity = _stable_int(f"{namespace}:intensity", 40, 85)

    low, high = _RESOURCE_RANGE[size]
    resource_level = _stable_int(f"{namespace}:resource", low, high)

    return CompanyProfile(
        training_style=training_style,
        management_style=management_style,
        training_intensity=training_intensity,
        resource_level=resource_level,
    )
