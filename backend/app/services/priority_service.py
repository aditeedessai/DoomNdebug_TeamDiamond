"""Deterministic Priority Calculation Service.

Task: Member 3 Task M3-08 - Deterministic Priority Calculation
Target File: backend/app/services/priority_service.py
Author: Member 3 (AI & Intelligence Developer)

Calculates deterministic civic complaint priority based on:
  Priority Score = (AI Severity * 10) + Community Report Bonus + Overdue Bonus

Where:
  - AI Severity is an integer from 1 through 10.
  - Community Report Bonus = (report_count - 1) * 5 (report_count >= 1).
  - Overdue Bonus is an explicit non-negative integer supplied by the caller (default 0).

Thresholds (PRD Section 4.2):
  - 80 or higher : "Critical"
  - 60 to 79     : "High"
  - 35 to 59     : "Medium"
  - 0 to 34      : "Low"

Strictly deterministic, synchronous, and pure: no database, network, AI, or wall-clock dependencies.
"""
from typing import Any, Literal

PriorityLevel = Literal["Low", "Medium", "High", "Critical"]


def _validate_integer_param(val: Any, name: str, min_val: int, max_val: int | None = None) -> int:
    """Validate that a parameter is an exact integer within the specified range.

    Rejects booleans (since bool is a subclass of int in Python), floats,
    strings, None, NaN, infinity, and values outside the required range.

    Raises:
        ValueError: If val is not an int or is outside [min_val, max_val].
    """
    # In Python, isinstance(True, int) is True, so we must explicitly check for bool
    if isinstance(val, bool) or not isinstance(val, int):
        raise ValueError(
            f"Invalid type for {name}: expected integer, got {type(val).__name__} ({val!r})"
        )

    if val < min_val:
        raise ValueError(
            f"{name} must be >= {min_val}, got {val}"
        )

    if max_val is not None and val > max_val:
        raise ValueError(
            f"{name} must be <= {max_val}, got {val}"
        )

    return val


class PriorityService:
    """Deterministic priority calculation service for civic complaints."""

    def calculate_priority_score(
        self,
        severity: int,
        report_count: int = 1,
        overdue_bonus: int = 0,
    ) -> int:
        """Calculate numerical priority score based on the agreed formula.

        Args:
            severity: Physical hazard severity from AI (integer 1 through 10).
            report_count: Total citizen reports for this issue (integer >= 1, default 1).
            overdue_bonus: Explicit overdue bonus points (integer >= 0, default 0).

        Returns:
            Calculated priority score as an integer.

        Raises:
            ValueError: If any input fails strict type or range validation.
        """
        valid_severity = _validate_integer_param(severity, "severity", min_val=1, max_val=10)
        valid_report_count = _validate_integer_param(report_count, "report_count", min_val=1)
        valid_overdue_bonus = _validate_integer_param(overdue_bonus, "overdue_bonus", min_val=0)

        severity_points = valid_severity * 10
        community_bonus = (valid_report_count - 1) * 5
        total_score = severity_points + community_bonus + valid_overdue_bonus

        return total_score

    def calculate_priority(
        self,
        severity: int,
        report_count: int = 1,
        overdue_bonus: int = 0,
    ) -> str:
        """Calculate deterministic priority level tier from severity, report count, and overdue bonus.

        Args:
            severity: Physical hazard severity from AI (integer 1 through 10).
            report_count: Total citizen reports for this issue (integer >= 1, default 1).
            overdue_bonus: Explicit overdue bonus points (integer >= 0, default 0).

        Returns:
            Priority level string: "Critical", "High", "Medium", or "Low".

        Raises:
            ValueError: If any input fails strict type or range validation.
        """
        score = self.calculate_priority_score(
            severity=severity,
            report_count=report_count,
            overdue_bonus=overdue_bonus,
        )

        if score >= 80:
            return "Critical"
        elif score >= 60:
            return "High"
        elif score >= 35:
            return "Medium"
        else:
            return "Low"


# Global singleton instance for injection across application layers
priority_service = PriorityService()
