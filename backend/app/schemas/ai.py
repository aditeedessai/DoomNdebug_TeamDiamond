"""Pydantic schemas for AI complaint analysis and classification contract.

Task: M3-01 Agree AI Input/Output Contract
Author: Member 3 (AI & Intelligence Developer)
Target File: backend/app/schemas/ai.py
"""
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

# ==============================================================================
# Allowed Types & Enums
# ==============================================================================

# Six canonical department names from database/seed.sql
DepartmentName = Literal[
    "Public Works Department",
    "Sanitation Department",
    "Electrical Department",
    "Water & Sewerage Department",
    "Traffic & Transport Department",
    "Parks & Public Assets Department",
]

# Exact seven canonical PRD category names from docs/PRD.md Section 4.2
# plus "Other" as a technical fallback for unclassified/ambiguous complaints
ComplaintCategory = Literal[
    "Potholes, damaged roads, footpaths",
    "Broken streetlights",
    "Garbage accumulation",
    "Water leakage, drainage blockage",
    "Traffic congestion, signal faults",
    "Public park or facility damage",
    "Unsafe public infrastructure",
    "Other",
]

# Supported citizen input languages per PRD Section 4.2
DetectedLanguage = Literal["English", "Hindi", "Other"]

# Women's / Public Safety concern categories per PRD Section 4.8
SafetyCategory = Literal[
    "Lighting issue",
    "Pedestrian accessibility issue",
    "Public transport infrastructure issue",
    "Repeated citizen concern",
    "Unverified safety concern",
]


# ==============================================================================
# Request Schema
# ==============================================================================

class AIAnalysisRequest(BaseModel):
    """Input payload for AI complaint analysis and classification."""
    model_config = ConfigDict(extra="ignore")

    description: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Citizen's description of the civic issue (English or Hindi)",
        examples=["There is a large pothole near the central bus stand causing traffic slowdown."],
    )
    latitude: Optional[float] = Field(
        None,
        ge=-90.0,
        le=90.0,
        description="Latitude coordinate of the issue location (-90.0 to 90.0)",
        examples=[15.3995],
    )
    longitude: Optional[float] = Field(
        None,
        ge=-180.0,
        le=180.0,
        description="Longitude coordinate of the issue location (-180.0 to 180.0)",
        examples=[73.8122],
    )
    image_url: Optional[str] = Field(
        None,
        description="Optional image reference stored in Supabase Storage",
        examples=["https://example.supabase.co/storage/v1/object/public/complaints/pothole.jpg"],
    )
    language_hint: Optional[Literal["en", "hi"]] = Field(
        None,
        description="Optional language hint from frontend ('en' or 'hi')",
        examples=["en"],
    )

    @field_validator("description")
    @classmethod
    def validate_description_not_whitespace(cls, value: str) -> str:
        """Reject whitespace-only descriptions while allowing short descriptions to reach AI."""
        if not value or not value.strip():
            raise ValueError("Complaint description cannot be empty or whitespace only.")
        return value


# ==============================================================================
# Response Schema
# ==============================================================================

class AIAnalysisResponse(BaseModel):
    """Structured AI intelligence output for complaint ingestion."""
    model_config = ConfigDict(extra="ignore")

    suggested_title: str = Field(
        ...,
        min_length=3,
        max_length=150,
        description="Concise 4–8 word title generated from description for complaints.title",
        examples=["Large Pothole near Central Bus Stand"],
    )
    category: ComplaintCategory = Field(
        ...,
        description="Canonical civic category matching PRD taxonomy or 'Other' as fallback",
        examples=["Potholes, damaged roads, footpaths"],
    )
    issue_type: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Specific defect classification (e.g., Pothole, Broken Streetlight)",
        examples=["Pothole"],
    )
    department: Optional[DepartmentName] = Field(
        None,
        description="Canonical responsible department, or None if uncertain / unclassified",
        examples=["Public Works Department"],
    )
    severity: int = Field(
        ...,
        ge=1,
        le=10,
        description="Severity rating on a 1–10 scale based on physical hazard level",
        examples=[8],
    )
    summary: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="Concise, factual summary stored in complaints.ai_summary",
        examples=["Large pothole near bus station exit causing vehicle damage and traffic slowdown."],
    )
    recommended_action: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="Suggested operational response for municipal officers and field workers",
        examples=["Inspect road condition, cordon off hazardous section, and dispatch asphalt patch crew."],
    )
    language: DetectedLanguage = Field(
        ...,
        description="Detected language of citizen's description",
        examples=["English"],
    )
    is_safety_related: bool = Field(
        default=False,
        description="Flag indicating if the issue impacts public or women's safety infrastructure",
        examples=[False],
    )
    safety_category: Optional[SafetyCategory] = Field(
        None,
        description="Subcategory of safety concern if is_safety_related is true",
        examples=[None],
    )
    needs_human_review: bool = Field(
        default=False,
        description="Set to true if confidence is low, input is ambiguous, or fallback triggered",
        examples=[False],
    )
    review_reason: Optional[str] = Field(
        None,
        description="Explanation when needs_human_review is true",
        examples=[None],
    )
