"""Pydantic schemas for map, traffic hotspots, and privacy-preserving safety zones."""
from datetime import date, datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


class MapComplaintMarker(BaseModel):
    """Sanitized municipal complaint marker for the interactive map."""
    id: UUID
    latitude: float
    longitude: float
    category: str
    status: str
    priority: str
    department_id: Optional[UUID] = None
    department_name: Optional[str] = None
    created_at: datetime
    report_count: int = 1
    # Safety fields are only returned to designated safety officers
    safety_related: Optional[bool] = None
    safety_category: Optional[str] = None


class MapProjectMarker(BaseModel):
    """Sanitized municipal infrastructure project marker for the interactive map."""
    id: UUID
    title: str
    description: str
    department_id: UUID
    department_name: Optional[str] = None
    latitude: float
    longitude: float
    status: str
    start_date: date
    expected_end_date: date
    is_published: bool


class TrafficHotspotCreate(BaseModel):
    """Schema for creating a demo or observed traffic congestion hotspot."""
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude between -90 and 90")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude between -180 and 180")
    congestion_level: str = Field(..., description="Congestion level: Low, Medium, or High")
    description: str = Field(..., min_length=5, max_length=500, description="Hotspot description")
    source: str = Field(default="demo", description="Data source (strictly 'demo' for MVP)")

    @field_validator("congestion_level")
    @classmethod
    def validate_congestion_level(cls, v: str) -> str:
        normalized = v.strip().title()
        if normalized not in ("Low", "Medium", "High"):
            raise ValueError("congestion_level must be one of: 'Low', 'Medium', 'High'")
        return normalized

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        if v.strip().lower() != "demo":
            raise ValueError("source must be 'demo' for this MVP as no live provider is integrated")
        return "demo"


class TrafficHotspotResponse(BaseModel):
    """Schema representing a traffic congestion hotspot record."""
    id: UUID
    latitude: float
    longitude: float
    congestion_level: str
    source: str
    description: str
    observed_at: datetime
    created_at: datetime
    updated_at: datetime


class AggregatedSafetyZoneResponse(BaseModel):
    """Privacy-preserving aggregated safety hotspot cluster for citizens and non-safety officials."""
    zone_id: str
    latitude: float = Field(..., description="Cluster centroid latitude rounded to 2 decimal places")
    longitude: float = Field(..., description="Cluster centroid longitude rounded to 2 decimal places")
    category: str = Field(..., description="Generalized infrastructure safety category")
    report_count: int = Field(..., ge=3, description="Aggregate report count (minimum 3 reports required)")
    suggested_action: str = Field(..., description="Safe municipal inspection guidance")
    status: str = Field(default="Active Reports", description="Cluster status indicator")


class SafetyOfficerIncidentMarker(BaseModel):
    """Granular authorized safety incident marker for designated safety officers only."""
    id: UUID
    latitude: float
    longitude: float
    category: str
    safety_category: Optional[str] = None
    status: str
    priority: str
    severity: int
    report_count: int = 1
    department_id: Optional[UUID] = None
    department_name: Optional[str] = None
    created_at: datetime
