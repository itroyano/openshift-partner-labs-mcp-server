"""OpenShift ACM models and data structures."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ACMClusterStatus:
    """ACM cluster status constants."""
    
    PENDING = "Pending"
    AVAILABLE = "Available"
    OFFLINE = "Offline"
    UNKNOWN = "Unknown"
    DESTROYING = "Destroying"
    HIBERNATING = "Hibernating"


class ACMClusterCondition(BaseModel):
    """ACM cluster condition model."""
    
    type: str
    status: str
    last_transition_time: Optional[str] = None
    reason: Optional[str] = None
    message: Optional[str] = None


class ACMClusterInfo(BaseModel):
    """ACM cluster information model."""
    
    cloud: Optional[str] = None
    version: Optional[str] = None
    distributor: Optional[str] = None
    region: Optional[str] = None
    vendor: Optional[str] = None
    nodes: Optional[int] = None


class ACMClusterClaimItem(BaseModel):
    """ACM cluster claim item model (simple key-value pair)."""
    
    name: str
    value: str


class ACMClusterLabels(BaseModel):
    """ACM cluster labels model."""
    
    cloud: Optional[str] = None
    cluster_id: Optional[str] = Field(None, alias="cluster.open-cluster-management.io/clusterset")
    name: Optional[str] = None
    vendor: Optional[str] = None
    environment: Optional[str] = None
    purpose: Optional[str] = None


class ACMManagedClusterSpec(BaseModel):
    """ACM ManagedCluster spec model."""
    
    hub_accepts_client: bool = Field(True, alias="hubAcceptsClient")
    leaseDurationSeconds: Optional[int] = Field(None, alias="leaseDurationSeconds")
    managed_cluster_client_configs: Optional[List[Dict[str, Any]]] = Field(
        None, alias="managedClusterClientConfigs"
    )


class ACMManagedClusterStatus(BaseModel):
    """ACM ManagedCluster status model."""
    
    allocatable: Optional[Dict[str, str]] = None
    capacity: Optional[Dict[str, str]] = None
    cluster_claims: Optional[List[ACMClusterClaimItem]] = Field(None, alias="clusterClaims")
    conditions: Optional[List[ACMClusterCondition]] = None
    version: Optional[ACMClusterInfo] = None


class ACMManagedCluster(BaseModel):
    """ACM ManagedCluster model."""
    
    api_version: str = Field("cluster.open-cluster-management.io/v1", alias="apiVersion")
    kind: str = "ManagedCluster"
    metadata: Dict[str, Any]
    spec: ACMManagedClusterSpec
    status: Optional[ACMManagedClusterStatus] = None


class ACMClusterDeploymentSpec(BaseModel):
    """ACM ClusterDeployment spec model."""
    
    base_domain: str = Field(..., alias="baseDomain")
    cluster_name: str = Field(..., alias="clusterName")
    platform: Dict[str, Any]
    provisioning: Dict[str, Any]
    pull_secret_ref: Dict[str, str] = Field(..., alias="pullSecretRef")
    cluster_metadata: Optional[Dict[str, Any]] = Field(None, alias="clusterMetadata")
    installed: Optional[bool] = False


class ACMClusterDeploymentStatus(BaseModel):
    """ACM ClusterDeployment status model."""
    
    admin_kubeconfig_secret_ref: Optional[Dict[str, str]] = Field(
        None, alias="adminKubeconfigSecretRef"
    )
    admin_password_secret_ref: Optional[Dict[str, str]] = Field(
        None, alias="adminPasswordSecretRef"
    )
    api_url: Optional[str] = Field(None, alias="apiURL")
    cluster_id: Optional[str] = Field(None, alias="clusterID")
    conditions: Optional[List[ACMClusterCondition]] = None
    installed_timestamp: Optional[str] = Field(None, alias="installedTimestamp")
    provision_ref: Optional[Dict[str, str]] = Field(None, alias="provisionRef")
    web_console_url: Optional[str] = Field(None, alias="webConsoleURL")


class ACMClusterDeployment(BaseModel):
    """ACM ClusterDeployment model."""
    
    api_version: str = Field("hive.openshift.io/v1", alias="apiVersion")
    kind: str = "ClusterDeployment"
    metadata: Dict[str, Any]
    spec: ACMClusterDeploymentSpec
    status: Optional[ACMClusterDeploymentStatus] = None


class ACMHibernationConfig(BaseModel):
    """ACM hibernation configuration model."""
    
    hibernateAfter: Optional[str] = None
    resumeAfter: Optional[str] = None


class ACMClusterPoolSpec(BaseModel):
    """ACM ClusterPool spec model."""
    
    base_domain: str = Field(..., alias="baseDomain")
    image_set_ref: Dict[str, str] = Field(..., alias="imageSetRef")
    platform: Dict[str, Any]
    pull_secret_ref: Dict[str, str] = Field(..., alias="pullSecretRef")
    size: int = 1
    hibernation_config: Optional[ACMHibernationConfig] = Field(None, alias="hibernationConfig")
    labels: Optional[Dict[str, str]] = None


class ACMClusterPool(BaseModel):
    """ACM ClusterPool model."""
    
    api_version: str = Field("hive.openshift.io/v1", alias="apiVersion")
    kind: str = "ClusterPool"
    metadata: Dict[str, Any]
    spec: ACMClusterPoolSpec


class ACMClusterClaimSpec(BaseModel):
    """ACM ClusterClaim spec model."""
    
    cluster_pool_name: str = Field(..., alias="clusterPoolName")
    lifetime: Optional[str] = None
    subjects: Optional[List[Dict[str, Any]]] = None


class ACMClusterClaimStatus(BaseModel):
    """ACM ClusterClaim status model."""
    
    conditions: Optional[List[ACMClusterCondition]] = None
    lifetime: Optional[str] = None
    namespace: Optional[str] = None


class ACMClusterClaim(BaseModel):
    """ACM ClusterClaim model."""
    
    api_version: str = Field("hive.openshift.io/v1", alias="apiVersion")
    kind: str = "ClusterClaim"
    metadata: Dict[str, Any]
    spec: ACMClusterClaimSpec
    status: Optional[ACMClusterClaimStatus] = None


class ACMCreateClusterRequest(BaseModel):
    """Request model for creating a cluster via ACM."""
    
    cluster_name: str = Field(..., description="Name of the cluster")
    namespace: str = Field(..., description="Namespace for cluster resources")
    base_domain: str = Field(..., description="Base domain for the cluster")
    cloud_provider: str = Field(..., description="Cloud provider (aws, azure, gcp)")
    region: str = Field(..., description="Cloud region")
    machine_type: Optional[str] = Field(None, description="Machine type/instance size")
    worker_nodes: int = Field(default=3, description="Number of worker nodes")
    hibernation_enabled: bool = Field(default=False, description="Enable hibernation")
    labels: Optional[Dict[str, str]] = Field(None, description="Additional cluster labels")
    annotations: Optional[Dict[str, str]] = Field(None, description="Additional cluster annotations")


class ACMHibernateClusterRequest(BaseModel):
    """Request model for hibernating a cluster."""
    
    cluster_name: str = Field(..., description="Name of the cluster to hibernate")
    namespace: str = Field(..., description="Namespace of the cluster")
    force: bool = Field(default=False, description="Force hibernation even if unsafe")


class ACMResumeClusterRequest(BaseModel):
    """Request model for resuming a hibernated cluster."""
    
    cluster_name: str = Field(..., description="Name of the cluster to resume")
    namespace: str = Field(..., description="Namespace of the cluster")


class ACMDeleteClusterRequest(BaseModel):
    """Request model for deleting a cluster."""
    
    cluster_name: str = Field(..., description="Name of the cluster to delete")
    namespace: str = Field(..., description="Namespace of the cluster")
    force: bool = Field(default=False, description="Force deletion even if unsafe")


class ACMClusterResponse(BaseModel):
    """Response model for cluster operations."""
    
    success: bool
    message: str
    cluster_name: Optional[str] = None
    namespace: Optional[str] = None
    status: Optional[str] = None
    details: Optional[Dict[str, Any]] = None