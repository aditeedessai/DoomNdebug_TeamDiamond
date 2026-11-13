"""Conservative Duplicate Complaint Detection Service.

Task: Member 3 Task M3-07 - Conservative Duplicate Matching
Target File: backend/app/services/duplicate_service.py
Author: Member 3 (AI & Intelligence Developer)

Provides spatial and categorical duplicate matching for civic complaints
using the Haversine formula over Earth's sphere (R = 6,371,000 m).
Identifies potential existing reports within a radius (default 100 m) for official review.
Strictly read-only: never automatically merges, deletes, or mutates complaint records.
Never returns citizen PII (citizen_id, phone, full description).
"""
import logging
import math
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import UUID

from app.database.supabase import supabase_service
from app.schemas.ai import ComplaintCategory

logger = logging.getLogger(__name__)

# Earth mean radius in metres per WGS84 spherical approximation
EARTH_RADIUS_METRES: float = 6371000.0

# Exact canonical categories from backend/app/schemas/ai.py
CANONICAL_CATEGORIES: Tuple[str, ...] = (
    "Potholes, damaged roads, footpaths",
    "Broken streetlights",
    "Garbage accumulation",
    "Water leakage, drainage blockage",
    "Traffic congestion, signal faults",
    "Public park or facility damage",
    "Unsafe public infrastructure",
    "Other",
)
CANONICAL_CATEGORIES_SET = set(CANONICAL_CATEGORIES)


def _validate_coordinate(val: Any, min_val: float, max_val: float) -> Optional[float]:
    """Validate and convert a geographic coordinate value.

    Rejects None, booleans, non-numeric strings, NaN, inf, and out-of-range values.
    Returns float coordinate if valid, or None.
    """
    if val is None or isinstance(val, bool):
        return None
    try:
        num = float(val)
    except (TypeError, ValueError):
        return None
    if math.isnan(num) or math.isinf(num):
        return None
    if not (min_val <= num <= max_val):
        return None
    return num


class DuplicateService:
    """Service for identifying nearby active complaints in the same canonical category."""

    DEFAULT_RADIUS_METRES: float = 100.0

    # Exact active statuses verified from database/schema.sql Table 3 CHECK constraint
    ACTIVE_STATUSES: Tuple[str, ...] = (
        "Submitted",
        "Under Review",
        "Assigned",
        "In Progress",
        "Needs More Information",
    )

    @staticmethod
    def calculate_distance(
        lat1: Any,
        lon1: Any,
        lat2: Any,
        lon2: Any,
    ) -> Optional[float]:
        """Calculate surface distance in metres between two coordinate pairs using Haversine formula.

        Args:
            lat1: Latitude of point 1 (-90.0 to 90.0)
            lon1: Longitude of point 1 (-180.0 to 180.0)
            lat2: Latitude of point 2 (-90.0 to 90.0)
            lon2: Longitude of point 2 (-180.0 to 180.0)

        Returns:
            Distance in metres as float, or None if any coordinate is invalid.
        """
        valid_lat1 = _validate_coordinate(lat1, -90.0, 90.0)
        valid_lon1 = _validate_coordinate(lon1, -180.0, 180.0)
        valid_lat2 = _validate_coordinate(lat2, -90.0, 90.0)
        valid_lon2 = _validate_coordinate(lon2, -180.0, 180.0)

        if (
            valid_lat1 is None
            or valid_lon1 is None
            or valid_lat2 is None
            or valid_lon2 is None
        ):
            return None

        # Convert decimal degrees to radians
        phi1 = math.radians(valid_lat1)
        phi2 = math.radians(valid_lat2)
        delta_phi = math.radians(valid_lat2 - valid_lat1)
        delta_lambda = math.radians(valid_lon2 - valid_lon1)

        # Haversine formula
        a = (
            math.sin(delta_phi / 2.0) ** 2
            + math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2)
        )

        # Domain clamp to protect against floating point rounding issues [0.0, 1.0]
        a = max(0.0, min(1.0, a))

        # Angular distance in radians
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

        return float(EARTH_RADIUS_METRES * c)

    async def find_duplicates(
        self,
        category: str,
        latitude: Optional[float],
        longitude: Optional[float],
        exclude_complaint_id: Optional[Union[UUID, str]] = None,
        radius_metres: float = DEFAULT_RADIUS_METRES,
        active_only: bool = True,
        candidates: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """Find potential duplicate complaints matching canonical category within search radius.

        Args:
            category: Canonical complaint category name.
            latitude: Target latitude in decimal degrees.
            longitude: Target longitude in decimal degrees.
            exclude_complaint_id: Optional complaint ID to exclude (e.g. self-matching).
            radius_metres: Search radius in metres (must be positive and finite, default 100.0m).
            active_only: If True, only search non-terminal complaints (Submitted, Under Review, etc.).
            candidates: Optional pre-loaded candidate list (avoids DB query, useful for testing).

        Returns:
            List of sanitized duplicate summary dicts sorted ascending by distance_meters.
            Strictly read-only; zero PII returned.
        """
        # 1. Category validation
        if not category or not isinstance(category, str) or category not in CANONICAL_CATEGORIES_SET:
            logger.debug("Duplicate search skipped: invalid or non-canonical category '%s'", category)
            return []

        # 2. Target coordinate validation
        target_lat = _validate_coordinate(latitude, -90.0, 90.0)
        target_lon = _validate_coordinate(longitude, -180.0, 180.0)
        if target_lat is None or target_lon is None:
            logger.debug("Duplicate search skipped: invalid target coordinates (%s, %s)", latitude, longitude)
            return []

        # 3. Radius validation
        if isinstance(radius_metres, bool):
            return []
        try:
            r_val = float(radius_metres)
            if math.isnan(r_val) or math.isinf(r_val) or r_val <= 0:
                logger.debug("Duplicate search skipped: invalid radius %s", radius_metres)
                return []
        except (TypeError, ValueError):
            return []

        # 4. Candidate retrieval (in-memory or Supabase query)
        if candidates is not None:
            candidate_list = candidates
        else:
            try:
                params: Dict[str, Any] = {
                    "category": f"eq.{category}",
                    "select": "id,title,category,issue_type,status,latitude,longitude,report_count,created_at",
                }
                if active_only:
                    statuses = ",".join(self.ACTIVE_STATUSES)
                    params["status"] = f"in.({statuses})"

                response = await supabase_service.rest_query(
                    "complaints",
                    method="GET",
                    params=params,
                )
                if not isinstance(response, list):
                    logger.warning("Supabase rest_query did not return a list: %s", type(response))
                    return []
                candidate_list = response
            except Exception as e:
                logger.error("Failed to query duplicate candidates from Supabase: %s", e)
                return []

        # 5. Evaluate and filter candidates
        exclude_id_norm: Optional[str] = None
        if exclude_complaint_id is not None:
            exclude_id_norm = str(exclude_complaint_id).strip().lower()

        matches: List[Dict[str, Any]] = []

        for c in candidate_list:
            if not isinstance(c, dict):
                continue

            # Self-matching exclusion
            cand_id_str = str(c.get("id", "")).strip().lower()
            if exclude_id_norm and cand_id_str == exclude_id_norm:
                continue

            # Exact category equality
            if c.get("category") != category:
                continue

            # Active status filter
            if active_only and c.get("status") not in self.ACTIVE_STATUSES:
                continue

            # Candidate coordinate validation & distance calculation
            cand_lat = c.get("latitude")
            cand_lon = c.get("longitude")
            dist = self.calculate_distance(target_lat, target_lon, cand_lat, cand_lon)

            if dist is None or dist > r_val:
                continue

            # Parse report count safely
            raw_rc = c.get("report_count", 1)
            if isinstance(raw_rc, bool):
                report_count = 1
            else:
                try:
                    report_count = int(raw_rc)
                    if report_count < 1:
                        report_count = 1
                except (TypeError, ValueError):
                    report_count = 1

            # Build strictly sanitized match dictionary (Zero PII)
            matches.append({
                "complaint_id": str(c.get("id", "")),
                "title": str(c.get("title") or ""),
                "category": str(c.get("category") or ""),
                "issue_type": str(c.get("issue_type") or ""),
                "status": str(c.get("status") or ""),
                "distance_meters": round(dist, 1),
                "report_count": report_count,
                "created_at": str(c.get("created_at") or ""),
            })

        # 6. Sort ascending by distance
        matches.sort(key=lambda m: m["distance_meters"])

        return matches


# Global singleton instance for injection across application layers
duplicate_service = DuplicateService()
