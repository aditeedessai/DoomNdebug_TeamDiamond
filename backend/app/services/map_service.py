"""Map service implementing role-based municipal data filtering, privacy-preserving safety zones, and traffic hotspots."""
import logging
from typing import Any, Dict, List, Optional, Union
from uuid import UUID
from fastapi import HTTPException, status

from app.database.supabase import supabase_service
from app.schemas.map import (
    AggregatedSafetyZoneResponse,
    MapComplaintMarker,
    MapProjectMarker,
    SafetyOfficerIncidentMarker,
    TrafficHotspotCreate,
    TrafficHotspotResponse,
)
from app.schemas.profile import ProfileResponse

logger = logging.getLogger(__name__)


class MapService:
    """Service layer for municipal map markers, traffic hotspots, and privacy-preserving safety zones."""

    async def _get_department_map(self) -> Dict[str, str]:
        """Fetch municipal department ID to name mapping in a single query."""
        dept_records = await supabase_service.rest_query(
            "departments", method="GET", params={"select": "id,name"}
        )
        if dept_records and isinstance(dept_records, list):
            return {str(d["id"]): d.get("name", "Department") for d in dept_records}
        return {}

    async def get_complaint_markers(
        self,
        current_user: ProfileResponse,
        status_filter: Optional[str] = None,
        category: Optional[str] = None,
        department_id: Optional[UUID] = None,
        safety_related: Optional[bool] = None,
    ) -> List[MapComplaintMarker]:
        """Retrieve sanitized complaint markers for the map with strict server-side authorization."""
        # 1. Workers are strictly forbidden from viewing general complaint markers
        if current_user.role == "worker":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Workers do not have access to the general complaint register. View assigned tasks instead.",
            )

        # 2. Safety authorization check: Non-safety officers requesting safety_related=true are rejected
        if safety_related is True and not current_user.is_safety_officer:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Restricted safety complaint data requires designated safety officer authorization.",
            )

        # 3. Build PostgREST query parameters with explicit projection
        # Intentionally excludes citizen_id, citizen phone, full names, raw descriptions, and private attachments
        params: Dict[str, Any] = {
            "order": "created_at.desc",
            "select": "id,latitude,longitude,category,status,priority,department_id,created_at,report_count,safety_related,safety_category",
        }

        # 4. Enforce safety filtering
        if not current_user.is_safety_officer:
            # Citizens and ordinary officials CANNOT view safety complaints on the general map
            params["safety_related"] = "eq.false"
        else:
            # Designated safety officer
            if safety_related is not None:
                params["safety_related"] = f"eq.{str(safety_related).lower()}"

        # 5. Department scoping
        if current_user.role == "official" and current_user.department_id:
            # Department officials cannot expand access beyond their department
            if department_id and department_id != current_user.department_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: You are not authorized to view complaints for other departments.",
                )
            params["department_id"] = f"eq.{current_user.department_id}"
        elif department_id:
            # General officials or citizens filtering by department
            params["department_id"] = f"eq.{department_id}"

        # 6. Apply approved status and category filters
        if status_filter:
            params["status"] = f"eq.{status_filter}"
        if category:
            params["category"] = f"eq.{category}"

        records = await supabase_service.rest_query("complaints", method="GET", params=params)
        if not records or not isinstance(records, list):
            return []

        dept_map = await self._get_department_map()
        markers = []
        for r in records:
            d_id = str(r.get("department_id")) if r.get("department_id") else None
            dept_name = dept_map.get(d_id) if d_id else None

            # Redact safety category and safety flag if caller is not a designated safety officer
            if not current_user.is_safety_officer:
                r["safety_related"] = None
                r["safety_category"] = None

            markers.append(
                MapComplaintMarker(
                    id=r["id"],
                    latitude=r["latitude"],
                    longitude=r["longitude"],
                    category=r["category"],
                    status=r["status"],
                    priority=r["priority"],
                    department_id=r.get("department_id"),
                    department_name=dept_name,
                    created_at=r["created_at"],
                    report_count=r.get("report_count", 1),
                    safety_related=r.get("safety_related"),
                    safety_category=r.get("safety_category"),
                )
            )

        return markers

    async def get_project_markers(
        self,
        current_user: ProfileResponse,
        department_id: Optional[UUID] = None,
        status_filter: Optional[str] = None,
    ) -> List[MapProjectMarker]:
        """Retrieve sanitized project markers for the map with publication boundaries."""
        params: Dict[str, Any] = {
            "order": "created_at.desc",
            "select": "id,title,description,department_id,latitude,longitude,status,start_date,expected_end_date,is_published",
        }

        # 1. Enforce publication visibility
        if current_user.role != "official":
            # Citizens and workers ONLY see published projects
            params["is_published"] = "eq.true"
        else:
            # Officials visibility
            if current_user.department_id:
                # Department officials see published projects OR unpublished projects in their own department
                params["or"] = f"(is_published.eq.true,department_id.eq.{current_user.department_id})"
            # General officials (department_id is None) see all projects

        # 2. Apply department and status filters (narrowing only)
        if department_id:
            params["department_id"] = f"eq.{department_id}"
        if status_filter:
            params["status"] = f"eq.{status_filter}"

        records = await supabase_service.rest_query("projects", method="GET", params=params)
        if not records or not isinstance(records, list):
            return []

        dept_map = await self._get_department_map()
        markers = []
        for p in records:
            d_id = str(p.get("department_id")) if p.get("department_id") else None
            dept_name = dept_map.get(d_id) if d_id else None

            markers.append(
                MapProjectMarker(
                    id=p["id"],
                    title=p["title"],
                    description=p["description"],
                    department_id=p["department_id"],
                    department_name=dept_name,
                    latitude=p["latitude"],
                    longitude=p["longitude"],
                    status=p["status"],
                    start_date=p["start_date"],
                    expected_end_date=p["expected_end_date"],
                    is_published=p["is_published"],
                )
            )

        return markers

    async def get_traffic_hotspots(
        self,
        congestion_level: Optional[str] = None,
        source: Optional[str] = None,
    ) -> List[TrafficHotspotResponse]:
        """Retrieve observed and demo traffic congestion hotspots for the map."""
        params: Dict[str, Any] = {
            "order": "observed_at.desc",
            "select": "*",
        }

        if congestion_level:
            params["congestion_level"] = f"eq.{congestion_level.strip().title()}"
        if source:
            params["source"] = f"eq.{source.strip().lower()}"

        records = await supabase_service.rest_query("traffic_hotspots", method="GET", params=params)
        if not records or not isinstance(records, list):
            return []

        return [TrafficHotspotResponse(**r) for r in records]

    async def create_traffic_hotspot(
        self,
        data: TrafficHotspotCreate,
        official: ProfileResponse,
    ) -> TrafficHotspotResponse:
        """Create a demo traffic congestion hotspot (authorized officials only)."""
        if official.role != "official":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Only municipal officials can create traffic hotspots.",
            )

        payload = {
            "latitude": data.latitude,
            "longitude": data.longitude,
            "congestion_level": data.congestion_level,
            "description": data.description.strip(),
            "source": "demo",
        }

        created = await supabase_service.rest_query("traffic_hotspots", method="POST", json_data=payload)
        if not created:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to register traffic hotspot in database.",
            )

        record = created[0] if isinstance(created, list) else created
        return TrafficHotspotResponse(**record)

    async def get_safety_zones(
        self,
        current_user: ProfileResponse,
    ) -> Union[List[AggregatedSafetyZoneResponse], List[SafetyOfficerIncidentMarker]]:
        """Retrieve privacy-preserving aggregated safety zones or authorized safety officer incident markers."""
        # 1. Workers are forbidden from viewing safety zones
        if current_user.role == "worker":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Workers do not have access to safety zone information.",
            )

        # 2. Designated Safety Officer view: granular authorized safety markers
        if current_user.is_safety_officer:
            params: Dict[str, Any] = {
                "safety_related": "eq.true",
                "order": "created_at.desc",
                "select": "id,latitude,longitude,category,safety_category,status,priority,severity,report_count,department_id,created_at",
            }
            # Exclude rejected safety records
            params["status"] = "neq.Rejected"

            if current_user.department_id:
                params["department_id"] = f"eq.{current_user.department_id}"

            records = await supabase_service.rest_query("complaints", method="GET", params=params)
            if not records or not isinstance(records, list):
                return []

            dept_map = await self._get_department_map()
            results: List[SafetyOfficerIncidentMarker] = []
            for r in records:
                d_id = str(r.get("department_id")) if r.get("department_id") else None
                r["department_name"] = dept_map.get(d_id) if d_id else None
                results.append(SafetyOfficerIncidentMarker(**r))
            return results

        # 3. Citizen & Ordinary Official view: Aggregated spatial clusters with k >= 3 threshold
        params = {
            "safety_related": "eq.true",
            "select": "latitude,longitude,category,safety_category,status,report_count",
        }
        # Exclude rejected records
        params["status"] = "neq.Rejected"

        records = await supabase_service.rest_query("complaints", method="GET", params=params)
        if not records or not isinstance(records, list):
            return []

        # Discretize into 0.01-degree spatial grid cells (~1.1 km x 1.1 km)
        buckets: Dict[tuple, List[Dict[str, Any]]] = {}
        for rec in records:
            lat = rec.get("latitude")
            lon = rec.get("longitude")
            if lat is None or lon is None:
                continue
            lat_bucket = round(float(lat), 2)
            lon_bucket = round(float(lon), 2)
            key = (lat_bucket, lon_bucket)
            if key not in buckets:
                buckets[key] = []
            buckets[key].append(rec)

        clusters: List[AggregatedSafetyZoneResponse] = []
        for (lat_b, lon_b), items in buckets.items():
            total_reports = sum(int(item.get("report_count") or 1) for item in items)

            # Minimum cluster size enforcement: suppress clusters with fewer than 3 reports (k < 3)
            if total_reports < 3:
                continue

            # Determine dominant safety category
            cat_counts: Dict[str, int] = {}
            for item in items:
                c = (item.get("safety_category") or item.get("category") or "General Safety").strip().title()
                cat_counts[c] = cat_counts.get(c, 0) + 1
            dominant_cat = max(cat_counts.items(), key=lambda x: x[1])[0]

            # Generate safe municipal terminology and actionable recommendation
            if "Light" in dominant_cat:
                gen_category = "Lighting Issue"
                action = "Municipal lighting inspection and electrical maintenance assessment recommended"
            elif "Pedestrian" in dominant_cat or "Footpath" in dominant_cat or "Sidewalk" in dominant_cat:
                gen_category = "Pedestrian Accessibility"
                action = "Footpath repair and pedestrian safety inspection recommended"
            elif "Transit" in dominant_cat or "Bus" in dominant_cat:
                gen_category = "Public Transport Infrastructure"
                action = "Transit stop maintenance and passenger safety review recommended"
            else:
                gen_category = "Public Infrastructure Safety Concern"
                action = "Municipal infrastructure and safety assessment recommended"

            lat_int = int(round(lat_b * 100))
            lon_int = int(round(lon_b * 100))
            zone_id = f"zone_{lat_int}_{lon_int}"

            clusters.append(
                AggregatedSafetyZoneResponse(
                    zone_id=zone_id,
                    latitude=lat_b,  # Rounded to two decimal places
                    longitude=lon_b,  # Rounded to two decimal places
                    category=gen_category,
                    report_count=total_reports,
                    suggested_action=action,
                    status="Active Reports",
                )
            )

        return clusters


# Global service instance
map_service = MapService()
