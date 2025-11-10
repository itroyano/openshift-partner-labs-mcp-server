"""Database models for OpenShift Partner Labs MCP Server."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class Company(BaseModel):
    """Company model for partner organizations."""

    id: Optional[int] = None
    company_name: str = Field(..., max_length=64)
    curated: bool = Field(default=False)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class LabState:
    """Enum-like class for lab state values."""

    PENDING = "pending"
    APPROVED = "approved"
    ACTIVE = "active"
    EXTENDED = "extended"
    COMPLETED = "completed"
    DENIED = "denied"


class RequestType:
    """Enum-like class for lab request types."""

    GENERAL = "general"
    ENGINEERING = "engineering"
    ROSA = "rosa"
    RHOAI = "rhoai"
    NVIDIA = "nvidia"
    OCPV = "ocpv"  # OpenShift Container Platform Virtualization


class CloudProvider:
    """Enum-like class for cloud provider values."""

    AWS = "AWS"
    AZURE = "Azure"
    GOOGLE = "Google"
    IBM = "IBM"
    ORACLE = "Oracle"
    ALIBABA = "Alibaba"
    LINODE = "Linode"
    VULTR = "Vultr"
    DIGITALO = "DigitalO"


class Region:
    """Enum-like class for region values."""

    NA1 = "na1"      # North America 1
    NA2 = "na2"      # North America 2
    EMEA = "emea"    # Europe, Middle East, Africa
    APAC1 = "apac1"  # Asia Pacific 1
    APAC2 = "apac2"  # Asia Pacific 2
    LATAM = "latam"  # Latin America


class ClusterSize:
    """Enum-like class for cluster size values."""

    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    XLARGE = "xlarge"
    CUSTOM = "custom"


class Lab(BaseModel):
    """Lab model for managing OpenShift Partner Labs."""

    id: Optional[int] = None
    cluster_id: str = Field(..., max_length=36, description="UUID of the cluster")
    generated_name: str = Field(..., max_length=32, description="Auto-generated friendly name")
    state: str = Field(default=LabState.PENDING, max_length=12)
    cluster_name: str = Field(..., max_length=32, description="Actual cluster name")
    openshift_version: str = Field(..., max_length=16, description="OpenShift version")
    cluster_size: str = Field(..., max_length=7, description="Size of the cluster")
    company_id: Optional[int] = Field(None, description="FK to companies table")
    request_type: str = Field(..., max_length=12, description="Type of lab request")
    partner: bool = Field(default=False, description="Is this a partner lab")
    sponsor: str = Field(..., max_length=64, description="Sponsor email")
    cloud_provider: str = Field(..., max_length=8, description="Cloud provider")

    # Primary contact information
    primary_first: str = Field(..., max_length=32, description="Primary contact first name")
    primary_last: str = Field(..., max_length=32, description="Primary contact last name")
    primary_email: str = Field(..., max_length=64, description="Primary contact email")

    # Secondary contact information
    secondary_first: str = Field(..., max_length=32, description="Secondary contact first name")
    secondary_last: str = Field(..., max_length=32, description="Secondary contact last name")
    secondary_email: str = Field(..., max_length=64, description="Secondary contact email")

    region: str = Field(..., max_length=5, description="Deployment region")
    always_on: bool = Field(default=False, description="Keep cluster always running")
    project_name: str = Field(..., max_length=32, description="Project identifier")
    lease_time: str = Field(..., max_length=2, description="Lease duration (1d, 1w, 1m, 2w, 2d)")
    description: str = Field(..., description="Lab description")
    notes: str = Field(..., description="Additional notes")
    start_date: datetime = Field(..., description="Lab start date")
    end_date: datetime = Field(..., description="Lab end date")
    hold: bool = Field(default=False, description="Put lab on hold")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class LabEvent(BaseModel):
    """Lab event model for audit trail."""

    id: Optional[int] = None
    lab_id: int
    event_type: str = Field(..., max_length=100)
    description: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: Optional[datetime] = None


class LabCreateRequest(BaseModel):
    """Request model for creating a new lab."""

    generated_name: str = Field(..., max_length=32, description="Auto-generated friendly name")
    cluster_name: str = Field(..., max_length=32, description="Actual cluster name")
    openshift_version: str = Field(..., max_length=16, description="OpenShift version")
    cluster_size: str = Field(..., max_length=7, description="Size of cluster")
    company_id: Optional[int] = Field(None, description="Company ID if applicable")
    request_type: str = Field(..., max_length=12, description="Type of request")
    partner: bool = Field(default=False, description="Partner lab flag")
    sponsor: str = Field(..., max_length=64, description="Sponsor email")
    cloud_provider: str = Field(..., max_length=8, description="Cloud provider")

    # Contact information
    primary_first: str = Field(..., max_length=32)
    primary_last: str = Field(..., max_length=32)
    primary_email: str = Field(..., max_length=64)
    secondary_first: str = Field(..., max_length=32)
    secondary_last: str = Field(..., max_length=32)
    secondary_email: str = Field(..., max_length=64)

    region: str = Field(..., max_length=5)
    always_on: bool = Field(default=False)
    project_name: str = Field(..., max_length=32)
    lease_time: str = Field(..., max_length=2)
    description: str = Field(...)
    notes: str = Field(...)
    start_date: datetime
    end_date: datetime
    hold: bool = Field(default=False)


class LabUpdateRequest(BaseModel):
    """Request model for updating lab information."""

    state: Optional[str] = Field(None, max_length=12)
    cluster_name: Optional[str] = Field(None, max_length=32)
    company_id: Optional[int] = None
    always_on: Optional[bool] = None
    hold: Optional[bool] = None
    end_date: Optional[datetime] = None
    notes: Optional[str] = None


class CompanyCreateRequest(BaseModel):
    """Request model for creating a new company."""

    company_name: str = Field(..., max_length=64)
    curated: bool = Field(default=False)


class LabListResponse(BaseModel):
    """Response model for listing labs."""

    labs: List[Lab]
    total_count: int
    page: int
    page_size: int


class CompanyListResponse(BaseModel):
    """Response model for listing companies."""

    companies: List[Company]
    total_count: int
    page: int
    page_size: int


class LabEventListResponse(BaseModel):
    """Response model for listing lab events."""

    events: List[LabEvent]
    total_count: int
    page: int
    page_size: int