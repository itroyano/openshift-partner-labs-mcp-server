"""Database models for OpenShift Partner Labs MCP Server."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class User(BaseModel):
    """User model for cluster ownership tracking."""
    
    id: Optional[int] = None
    username: str = Field(..., max_length=255)
    email: str = Field(..., max_length=255)
    red_hat_uuid: Optional[str] = Field(None, max_length=255)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ClusterStatus:
    """Enum-like class for cluster status values."""
    
    PENDING = "pending"
    CREATING = "creating"
    READY = "ready"
    HIBERNATING = "hibernating"
    HIBERNATED = "hibernated"
    RESUMING = "resuming"
    DELETING = "deleting"
    DELETED = "deleted"
    ERROR = "error"


class ClusterEventType:
    """Enum-like class for cluster event types."""
    
    CREATED = "created"
    HIBERNATED = "hibernated"
    RESUMED = "resumed"
    DELETED = "deleted"
    STATUS_CHANGED = "status_changed"
    OWNERSHIP_TRANSFERRED = "ownership_transferred"
    ERROR_OCCURRED = "error_occurred"


class Cluster(BaseModel):
    """Cluster model for managing OpenShift clusters."""
    
    id: Optional[int] = None
    name: str = Field(..., max_length=255)
    namespace: str = Field(..., max_length=255)
    owner_id: Optional[int] = None
    status: str = Field(default=ClusterStatus.PENDING, max_length=50)
    cluster_type: Optional[str] = Field(None, max_length=100)
    provider: Optional[str] = Field(None, max_length=100)
    region: Optional[str] = Field(None, max_length=100)
    acm_managed_cluster_name: Optional[str] = Field(None, max_length=255)
    hibernation_enabled: bool = Field(default=False)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None


class ClusterEvent(BaseModel):
    """Cluster event model for audit trail."""
    
    id: Optional[int] = None
    cluster_id: int
    event_type: str = Field(..., max_length=100)
    description: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: Optional[datetime] = None


class ClusterCreateRequest(BaseModel):
    """Request model for creating a new cluster."""
    
    name: str = Field(..., max_length=255, description="Unique cluster name")
    namespace: str = Field(..., max_length=255, description="Kubernetes namespace")
    cluster_type: str = Field(..., max_length=100, description="Type of cluster (e.g., 'ocp', 'rosa')")
    provider: str = Field(..., max_length=100, description="Cloud provider (e.g., 'aws', 'azure', 'gcp')")
    region: str = Field(..., max_length=100, description="Cloud region")
    hibernation_enabled: bool = Field(default=False, description="Enable hibernation support")
    metadata: Optional[dict] = Field(None, description="Additional cluster configuration")


class ClusterUpdateRequest(BaseModel):
    """Request model for updating cluster information."""
    
    status: Optional[str] = Field(None, max_length=50)
    owner_id: Optional[int] = None
    hibernation_enabled: Optional[bool] = None
    metadata: Optional[dict] = None


class UserCreateRequest(BaseModel):
    """Request model for creating a new user."""
    
    username: str = Field(..., max_length=255)
    email: str = Field(..., max_length=255)
    red_hat_uuid: Optional[str] = Field(None, max_length=255)


class ClusterListResponse(BaseModel):
    """Response model for listing clusters."""
    
    clusters: List[Cluster]
    total_count: int
    page: int
    page_size: int


class UserListResponse(BaseModel):
    """Response model for listing users."""
    
    users: List[User]
    total_count: int
    page: int
    page_size: int


class ClusterEventListResponse(BaseModel):
    """Response model for listing cluster events."""
    
    events: List[ClusterEvent]
    total_count: int
    page: int
    page_size: int