"""OpenShift ACM client for cluster lifecycle management."""

import json
from typing import Any, Dict, List, Optional

import httpx
from kubernetes import client, config
from kubernetes.client.rest import ApiException

from openshift_partner_labs_mcp_server.src.acm.models import (
    ACMClusterDeployment,
    ACMClusterResponse,
    ACMCreateClusterRequest,
    ACMDeleteClusterRequest,
    ACMHibernateClusterRequest,
    ACMManagedCluster,
    ACMResumeClusterRequest,
)
from openshift_partner_labs_mcp_server.src.settings import settings
from openshift_partner_labs_mcp_server.utils.pylogger import get_python_logger

logger = get_python_logger()


class ACMClient:
    """OpenShift Advanced Cluster Management client."""
    
    def __init__(self, kubeconfig_path: Optional[str] = None):
        """Initialize ACM client.
        
        Args:
            kubeconfig_path: Path to kubeconfig file. If None, uses default location.
        """
        self.kubeconfig_path = kubeconfig_path
        self._api_client: Optional[client.ApiClient] = None
        self._custom_objects_api: Optional[client.CustomObjectsApi] = None
        self._core_v1_api: Optional[client.CoreV1Api] = None
    
    async def initialize(self) -> None:
        """Initialize Kubernetes client."""
        try:
            if self.kubeconfig_path:
                config.load_kube_config(config_file=self.kubeconfig_path)
            else:
                # Try in-cluster config first, then default kubeconfig
                try:
                    config.load_incluster_config()
                except config.ConfigException:
                    config.load_kube_config()
            
            self._api_client = client.ApiClient()
            self._custom_objects_api = client.CustomObjectsApi(self._api_client)
            self._core_v1_api = client.CoreV1Api(self._api_client)
            
            logger.info("ACM client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize ACM client: {e}")
            raise
    
    def _ensure_initialized(self) -> None:
        """Ensure client is initialized."""
        if not self._custom_objects_api:
            raise RuntimeError("ACM client not initialized. Call initialize() first.")
    
    async def create_cluster(self, request: ACMCreateClusterRequest) -> ACMClusterResponse:
        """Create a new cluster via ACM.
        
        Args:
            request: Cluster creation request.
            
        Returns:
            ACMClusterResponse with operation result.
        """
        self._ensure_initialized()
        
        try:
            # Create ManagedCluster resource
            managed_cluster = self._build_managed_cluster(request)
            
            logger.info(f"Creating ManagedCluster {request.cluster_name} in namespace {request.namespace}")
            
            # Create the ManagedCluster
            result = self._custom_objects_api.create_cluster_custom_object(
                group="cluster.open-cluster-management.io",
                version="v1",
                plural="managedclusters",
                body=managed_cluster.dict(by_alias=True, exclude_none=True)
            )
            
            # Create ClusterDeployment if needed
            if request.cloud_provider in ["aws", "azure", "gcp"]:
                cluster_deployment = self._build_cluster_deployment(request)
                
                logger.info(f"Creating ClusterDeployment {request.cluster_name} in namespace {request.namespace}")
                
                self._custom_objects_api.create_namespaced_custom_object(
                    group="hive.openshift.io",
                    version="v1",
                    namespace=request.namespace,
                    plural="clusterdeployments",
                    body=cluster_deployment.dict(by_alias=True, exclude_none=True)
                )
            
            logger.info(f"Successfully initiated cluster creation for {request.cluster_name}")
            
            return ACMClusterResponse(
                success=True,
                message=f"Cluster {request.cluster_name} creation initiated",
                cluster_name=request.cluster_name,
                namespace=request.namespace,
                status="Creating",
                details={"managed_cluster": result}
            )
            
        except ApiException as e:
            error_msg = f"Failed to create cluster {request.cluster_name}: {e.reason}"
            logger.error(error_msg)
            
            return ACMClusterResponse(
                success=False,
                message=error_msg,
                cluster_name=request.cluster_name,
                namespace=request.namespace,
                details={"error": str(e)}
            )
        
        except Exception as e:
            error_msg = f"Unexpected error creating cluster {request.cluster_name}: {str(e)}"
            logger.error(error_msg)
            
            return ACMClusterResponse(
                success=False,
                message=error_msg,
                cluster_name=request.cluster_name,
                namespace=request.namespace,
                details={"error": str(e)}
            )
    
    async def hibernate_cluster(self, request: ACMHibernateClusterRequest) -> ACMClusterResponse:
        """Hibernate a cluster.
        
        Args:
            request: Hibernation request.
            
        Returns:
            ACMClusterResponse with operation result.
        """
        self._ensure_initialized()
        
        try:
            logger.info(f"Hibernating cluster {request.cluster_name} in namespace {request.namespace}")
            
            # Get the ClusterDeployment
            cd = self._custom_objects_api.get_namespaced_custom_object(
                group="hive.openshift.io",
                version="v1",
                namespace=request.namespace,
                plural="clusterdeployments",
                name=request.cluster_name
            )
            
            # Add hibernation annotation
            if "metadata" not in cd:
                cd["metadata"] = {}
            if "annotations" not in cd["metadata"]:
                cd["metadata"]["annotations"] = {}
            
            cd["metadata"]["annotations"]["hive.openshift.io/hibernating"] = "true"
            
            # Update the ClusterDeployment
            self._custom_objects_api.patch_namespaced_custom_object(
                group="hive.openshift.io",
                version="v1",
                namespace=request.namespace,
                plural="clusterdeployments",
                name=request.cluster_name,
                body=cd
            )
            
            logger.info(f"Successfully initiated hibernation for cluster {request.cluster_name}")
            
            return ACMClusterResponse(
                success=True,
                message=f"Cluster {request.cluster_name} hibernation initiated",
                cluster_name=request.cluster_name,
                namespace=request.namespace,
                status="Hibernating"
            )
            
        except ApiException as e:
            error_msg = f"Failed to hibernate cluster {request.cluster_name}: {e.reason}"
            logger.error(error_msg)
            
            return ACMClusterResponse(
                success=False,
                message=error_msg,
                cluster_name=request.cluster_name,
                namespace=request.namespace,
                details={"error": str(e)}
            )
        
        except Exception as e:
            error_msg = f"Unexpected error hibernating cluster {request.cluster_name}: {str(e)}"
            logger.error(error_msg)
            
            return ACMClusterResponse(
                success=False,
                message=error_msg,
                cluster_name=request.cluster_name,
                namespace=request.namespace,
                details={"error": str(e)}
            )
    
    async def resume_cluster(self, request: ACMResumeClusterRequest) -> ACMClusterResponse:
        """Resume a hibernated cluster.
        
        Args:
            request: Resume request.
            
        Returns:
            ACMClusterResponse with operation result.
        """
        self._ensure_initialized()
        
        try:
            logger.info(f"Resuming cluster {request.cluster_name} in namespace {request.namespace}")
            
            # Get the ClusterDeployment
            cd = self._custom_objects_api.get_namespaced_custom_object(
                group="hive.openshift.io",
                version="v1",
                namespace=request.namespace,
                plural="clusterdeployments",
                name=request.cluster_name
            )
            
            # Remove hibernation annotation
            if ("metadata" in cd and 
                "annotations" in cd["metadata"] and 
                "hive.openshift.io/hibernating" in cd["metadata"]["annotations"]):
                
                del cd["metadata"]["annotations"]["hive.openshift.io/hibernating"]
            
            # Update the ClusterDeployment
            self._custom_objects_api.patch_namespaced_custom_object(
                group="hive.openshift.io",
                version="v1",
                namespace=request.namespace,
                plural="clusterdeployments",
                name=request.cluster_name,
                body=cd
            )
            
            logger.info(f"Successfully initiated resume for cluster {request.cluster_name}")
            
            return ACMClusterResponse(
                success=True,
                message=f"Cluster {request.cluster_name} resume initiated",
                cluster_name=request.cluster_name,
                namespace=request.namespace,
                status="Resuming"
            )
            
        except ApiException as e:
            error_msg = f"Failed to resume cluster {request.cluster_name}: {e.reason}"
            logger.error(error_msg)
            
            return ACMClusterResponse(
                success=False,
                message=error_msg,
                cluster_name=request.cluster_name,
                namespace=request.namespace,
                details={"error": str(e)}
            )
        
        except Exception as e:
            error_msg = f"Unexpected error resuming cluster {request.cluster_name}: {str(e)}"
            logger.error(error_msg)
            
            return ACMClusterResponse(
                success=False,
                message=error_msg,
                cluster_name=request.cluster_name,
                namespace=request.namespace,
                details={"error": str(e)}
            )
    
    async def delete_cluster(self, request: ACMDeleteClusterRequest) -> ACMClusterResponse:
        """Delete a cluster.
        
        Args:
            request: Delete request.
            
        Returns:
            ACMClusterResponse with operation result.
        """
        self._ensure_initialized()
        
        try:
            logger.info(f"Deleting cluster {request.cluster_name} in namespace {request.namespace}")
            
            # Delete ClusterDeployment first
            try:
                self._custom_objects_api.delete_namespaced_custom_object(
                    group="hive.openshift.io",
                    version="v1",
                    namespace=request.namespace,
                    plural="clusterdeployments",
                    name=request.cluster_name
                )
                logger.info(f"ClusterDeployment {request.cluster_name} deleted")
            except ApiException as e:
                if e.status != 404:  # Ignore not found errors
                    raise
            
            # Delete ManagedCluster
            try:
                self._custom_objects_api.delete_cluster_custom_object(
                    group="cluster.open-cluster-management.io",
                    version="v1",
                    plural="managedclusters",
                    name=request.cluster_name
                )
                logger.info(f"ManagedCluster {request.cluster_name} deleted")
            except ApiException as e:
                if e.status != 404:  # Ignore not found errors
                    raise
            
            logger.info(f"Successfully initiated deletion for cluster {request.cluster_name}")
            
            return ACMClusterResponse(
                success=True,
                message=f"Cluster {request.cluster_name} deletion initiated",
                cluster_name=request.cluster_name,
                namespace=request.namespace,
                status="Deleting"
            )
            
        except ApiException as e:
            error_msg = f"Failed to delete cluster {request.cluster_name}: {e.reason}"
            logger.error(error_msg)
            
            return ACMClusterResponse(
                success=False,
                message=error_msg,
                cluster_name=request.cluster_name,
                namespace=request.namespace,
                details={"error": str(e)}
            )
        
        except Exception as e:
            error_msg = f"Unexpected error deleting cluster {request.cluster_name}: {str(e)}"
            logger.error(error_msg)
            
            return ACMClusterResponse(
                success=False,
                message=error_msg,
                cluster_name=request.cluster_name,
                namespace=request.namespace,
                details={"error": str(e)}
            )
    
    async def get_cluster_status(self, cluster_name: str, namespace: str) -> ACMClusterResponse:
        """Get cluster status.
        
        Args:
            cluster_name: Name of the cluster.
            namespace: Namespace of the cluster.
            
        Returns:
            ACMClusterResponse with cluster status.
        """
        self._ensure_initialized()
        
        try:
            logger.info(f"Getting status for cluster {cluster_name} in namespace {namespace}")
            
            # Get ManagedCluster
            managed_cluster = self._custom_objects_api.get_cluster_custom_object(
                group="cluster.open-cluster-management.io",
                version="v1",
                plural="managedclusters",
                name=cluster_name
            )
            
            status = "Unknown"
            details = {"managed_cluster": managed_cluster}
            
            # Extract status from ManagedCluster
            if "status" in managed_cluster and "conditions" in managed_cluster["status"]:
                conditions = managed_cluster["status"]["conditions"]
                for condition in conditions:
                    if condition["type"] == "ManagedClusterConditionAvailable":
                        if condition["status"] == "True":
                            status = "Available"
                        else:
                            status = "Offline"
                        break
            
            # Try to get ClusterDeployment for additional info
            try:
                cluster_deployment = self._custom_objects_api.get_namespaced_custom_object(
                    group="hive.openshift.io",
                    version="v1",
                    namespace=namespace,
                    plural="clusterdeployments",
                    name=cluster_name
                )
                details["cluster_deployment"] = cluster_deployment
                
                # Check for hibernation
                if ("metadata" in cluster_deployment and 
                    "annotations" in cluster_deployment["metadata"] and 
                    cluster_deployment["metadata"]["annotations"].get("hive.openshift.io/hibernating") == "true"):
                    status = "Hibernating"
                
            except ApiException as e:
                if e.status != 404:
                    logger.warning(f"Could not get ClusterDeployment for {cluster_name}: {e.reason}")
            
            return ACMClusterResponse(
                success=True,
                message=f"Cluster {cluster_name} status retrieved",
                cluster_name=cluster_name,
                namespace=namespace,
                status=status,
                details=details
            )
            
        except ApiException as e:
            error_msg = f"Failed to get status for cluster {cluster_name}: {e.reason}"
            logger.error(error_msg)
            
            return ACMClusterResponse(
                success=False,
                message=error_msg,
                cluster_name=cluster_name,
                namespace=namespace,
                details={"error": str(e)}
            )
        
        except Exception as e:
            error_msg = f"Unexpected error getting status for cluster {cluster_name}: {str(e)}"
            logger.error(error_msg)
            
            return ACMClusterResponse(
                success=False,
                message=error_msg,
                cluster_name=cluster_name,
                namespace=namespace,
                details={"error": str(e)}
            )
    
    async def list_clusters(self, namespace: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all managed clusters.
        
        Args:
            namespace: Optional namespace filter.
            
        Returns:
            List of cluster information.
        """
        self._ensure_initialized()
        
        try:
            logger.info(f"Listing clusters in namespace: {namespace or 'all'}")
            
            # Get all ManagedClusters
            clusters = self._custom_objects_api.list_cluster_custom_object(
                group="cluster.open-cluster-management.io",
                version="v1",
                plural="managedclusters"
            )
            
            result = []
            for cluster in clusters.get("items", []):
                cluster_info = {
                    "name": cluster["metadata"]["name"],
                    "labels": cluster["metadata"].get("labels", {}),
                    "status": "Unknown"
                }
                
                # Extract status
                if "status" in cluster and "conditions" in cluster["status"]:
                    conditions = cluster["status"]["conditions"]
                    for condition in conditions:
                        if condition["type"] == "ManagedClusterConditionAvailable":
                            if condition["status"] == "True":
                                cluster_info["status"] = "Available"
                            else:
                                cluster_info["status"] = "Offline"
                            break
                
                result.append(cluster_info)
            
            logger.info(f"Found {len(result)} clusters")
            return result
            
        except Exception as e:
            logger.error(f"Failed to list clusters: {str(e)}")
            return []
    
    def _build_managed_cluster(self, request: ACMCreateClusterRequest) -> ACMManagedCluster:
        """Build ManagedCluster resource.
        
        Args:
            request: Cluster creation request.
            
        Returns:
            ACMManagedCluster object.
        """
        labels = {
            "cloud": request.cloud_provider,
            "name": request.cluster_name,
            "vendor": "OpenShift"
        }
        
        if request.labels:
            labels.update(request.labels)
        
        annotations = {}
        if request.annotations:
            annotations.update(request.annotations)
        
        metadata = {
            "name": request.cluster_name,
            "labels": labels,
            "annotations": annotations
        }
        
        spec = {
            "hubAcceptsClient": True,
            "leaseDurationSeconds": 60
        }
        
        return ACMManagedCluster(
            metadata=metadata,
            spec=spec
        )
    
    def _build_cluster_deployment(self, request: ACMCreateClusterRequest) -> ACMClusterDeployment:
        """Build ClusterDeployment resource.
        
        Args:
            request: Cluster creation request.
            
        Returns:
            ACMClusterDeployment object.
        """
        metadata = {
            "name": request.cluster_name,
            "namespace": request.namespace,
            "labels": {
                "hive.openshift.io/cluster-platform": request.cloud_provider,
                "hive.openshift.io/cluster-region": request.region
            }
        }
        
        if request.labels:
            metadata["labels"].update(request.labels)
        
        platform_config = self._build_platform_config(request)
        
        spec = {
            "baseDomain": request.base_domain,
            "clusterName": request.cluster_name,
            "platform": platform_config,
            "provisioning": {
                "installConfigSecretRef": {
                    "name": f"{request.cluster_name}-install-config"
                },
                "sshPrivateKeySecretRef": {
                    "name": f"{request.cluster_name}-ssh-private-key"
                }
            },
            "pullSecretRef": {
                "name": f"{request.cluster_name}-pull-secret"
            }
        }
        
        return ACMClusterDeployment(
            metadata=metadata,
            spec=spec
        )
    
    def _build_platform_config(self, request: ACMCreateClusterRequest) -> Dict[str, Any]:
        """Build platform-specific configuration.
        
        Args:
            request: Cluster creation request.
            
        Returns:
            Platform configuration dictionary.
        """
        if request.cloud_provider.lower() == "aws":
            return {
                "aws": {
                    "region": request.region,
                    "userTags": {
                        "created-by": "acm-mcp-server"
                    }
                }
            }
        elif request.cloud_provider.lower() == "azure":
            return {
                "azure": {
                    "region": request.region,
                    "baseDomainResourceGroupName": f"{request.cluster_name}-base-domain-rg"
                }
            }
        elif request.cloud_provider.lower() == "gcp":
            project_id = settings.ACM_GCP_PROJECT_ID
            if not project_id:
                raise ValueError("ACM_GCP_PROJECT_ID must be configured for GCP cluster creation")
            return {
                "gcp": {
                    "region": request.region,
                    "projectID": project_id
                }
            }
        else:
            raise ValueError(f"Unsupported cloud provider: {request.cloud_provider}")


# Global ACM client instance
# Initialize with kubeconfig path from settings if available
acm_client = ACMClient(kubeconfig_path=settings.ACM_KUBECONFIG_PATH if hasattr(settings, 'ACM_KUBECONFIG_PATH') else None)