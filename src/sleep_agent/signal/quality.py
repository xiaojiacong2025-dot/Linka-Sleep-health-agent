from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QualityResult:
    usable: bool
    reasons: list[str]


def assess_quality(
    *, coverage: float, contact_fraction: float, motion_fraction: float,
    abnormal_rr_fraction: float, min_coverage: float = 0.99,
    min_contact_fraction: float = 0.99, max_motion_fraction: float = 0.05,
    max_abnormal_rr_fraction: float = 0.10,
) -> QualityResult:
    reasons: list[str] = []
    if coverage < min_coverage:
        reasons.append("coverage_below_threshold")
    if contact_fraction < min_contact_fraction:
        reasons.append("contact_below_threshold")
    if motion_fraction > max_motion_fraction:
        reasons.append("excessive_motion")
    if abnormal_rr_fraction > max_abnormal_rr_fraction:
        reasons.append("too_many_abnormal_rr")
    return QualityResult(not reasons, reasons)

