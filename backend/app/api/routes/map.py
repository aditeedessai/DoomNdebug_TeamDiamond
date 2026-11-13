"""FastAPI routes for map, traffic hotspots, and privacy-preserving safety zones."""
from typing import List, Optional, Union
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_current_user, require_official
from app.schemas.map import (
    AggregatedSafetyZoneResponse,
    MapComplaintMarker,
    MapProjectMarker,
    SafetyOfficerIncidentMarker,
    TrafficHotspotCreate,
    TrafficHotspotResponse,
)
from app.schemas.profile import ProfileResponse
from app.services.map_service import map_service

router = APIRouter()


@router.get(
    "/complaints",
    response_model=List[MapComplaintMarker],
    summary="Get map-visible complaint markers",
    description="Retrieve sanitized complaint markers for the interactive map. Excludes safety complaints and citizen PII for citizens.",
)
async def get_map_complaints(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by lifecycle status"),
    category: Optional[str] = Query(None, description="Filter by complaint category"),
    department_id: Optional[UUID] = Query(None, description="Filter by department UUID"),
    safety_related: Optional[bool] = Query(None, description="Restricted safety filter (Safety officers only)"),
    current_user: ProfileResponse = Depends(get_current_user),
) -> List[MapComplaintMarker]:
    """Retrieve map-visible complaints with server-side authorization enforcement."""
    return await map_service.get_complaint_markers(
        current_user=current_user,
        status_filter=status_filter,
        category=category,
        department_id=department_id,
        safety_related=safety_related,
    )


@router.get(
    "/projects",
    response_model=List[MapProjectMarker],
    summary="Get map-visible municipal projects",
    description="Retrieve municipal infrastructure project markers. Citizens and workers see only published projects.",
)
async def get_map_projects(
    department_id: Optional[UUID] = Query(None, description="Filter projects by department UUID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter projects by status"),
    current_user: ProfileResponse = Depends(get_current_user),
) -> List[MapProjectMarker]:
    """Retrieve project markers respecting publication boundaries and official permissions."""
    return await map_service.get_project_markers(
        current_user=current_user,
        department_id=department_id,
        status_filter=status_filter,
    )


@router.get(
    "/hotspots",
    response_model=List[TrafficHotspotResponse],
    summary="List traffic congestion hotspots",
    description="Retrieve observed and demo traffic congestion hotspots. Clearly identifies demo records for frontend labeling.",
)
async def get_map_traffic_hotspots(
    congestion_level: Optional[str] = Query(None, description="Filter by congestion level (Low, Medium, High)"),
    source: Optional[str] = Query(None, description="Filter by source (e.g. demo)"),
    current_user: ProfileResponse = Depends(get_current_user),
) -> List[TrafficHotspotResponse]:
    """Retrieve traffic hotspots for the city map."""
    return await map_service.get_traffic_hotspots(
        congestion_level=congestion_level,
        source=source,
    )


@router.post(
    "/hotspots",
    response_model=TrafficHotspotResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a traffic congestion hotspot",
    description="Register an observed or demo traffic congestion hotspot (authorized officials only).",
)
async def create_map_traffic_hotspot(
    data: TrafficHotspotCreate,
    current_user: ProfileResponse = Depends(require_official),
) -> TrafficHotspotResponse:
    """Create a demo traffic hotspot."""
    return await map_service.create_traffic_hotspot(
        data=data,
        official=current_user,
    )


@router.get(
    "/safety-zones",
    response_model=Union[List[AggregatedSafetyZoneResponse], List[SafetyOfficerIncidentMarker]],
    summary="Get safety zones and hotspots",
    description="Retrieve privacy-preserving aggregated safety clusters (k >= 3) for citizens and ordinary officials, or granular authorized safety incident markers for designated safety officers.",
)
async def get_map_safety_zones(
    current_user: ProfileResponse = Depends(get_current_user),
) -> Union[List[AggregatedSafetyZoneResponse], List[SafetyOfficerIncidentMarker]]:
    """Retrieve privacy-preserving safety zones or authorized safety officer incident markers."""
    return await map_service.get_safety_zones(current_user=current_user)
