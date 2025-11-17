"""Cluster management MCP tools for OpenShift ACM integration."""

from typing import Dict, List, Optional

from openshift_partner_labs_mcp_server.src.acm.client import acm_client
from openshift_partner_labs_mcp_server.src.acm.models import (
    ACMCreateClusterRequest,
    ACMDeleteClusterRequest,
    ACMHibernateClusterRequest,
    ACMResumeClusterRequest,
)
from openshift_partner_labs_mcp_server.src.database.models import (
    ClusterCreateRequest,
    ClusterEventType,
    ClusterStatus,
    ClusterUpdateRequest,
)
from openshift_partner_labs_mcp_server.src.database.service import db_service
from openshift_partner_labs_mcp_server.utils.pylogger import get_python_logger

logger = get_python_logger()


async def create_cluster(
    cluster_name: str,
    namespace: str,
    cluster_type: str,
    provider: str,
    region: str,
    base_domain: str,
    owner_username: str,
    hibernation_enabled: bool = False,
    machine_type: Optional[str] = None,
    worker_nodes: int = 3,
    labels: Optional[Dict[str, str]] = None,
    annotations: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """Create a new OpenShift cluster via ACM.
    
    Args:
        cluster_name: Unique name for the cluster
        namespace: Kubernetes namespace for cluster resources
        cluster_type: Type of cluster (e.g., 'ocp', 'rosa')
        provider: Cloud provider ('aws', 'azure', 'gcp')
        region: Cloud region
        base_domain: Base domain for the cluster
        owner_username: Username of the cluster owner
        hibernation_enabled: Whether to enable hibernation support
        machine_type: Machine type/instance size
        worker_nodes: Number of worker nodes
        labels: Additional cluster labels
        annotations: Additional cluster annotations
        
    Returns:
        Dictionary with operation result and cluster information
    """
    try:
        logger.info(f"Creating cluster {cluster_name} for user {owner_username}")
        
        # Initialize services if needed
        if not acm_client._custom_objects_api:
            await acm_client.initialize()
        
        # Get or create user
        user = await db_service.get_user_by_username(owner_username)
        if not user:
            return {
                "success": "false",
                "message": f"User {owner_username} not found. Please create user first.",
                "cluster_name": cluster_name
            }
        
        # Check if cluster name already exists
        existing_cluster = await db_service.get_cluster_by_name(cluster_name)
        if existing_cluster:
            return {
                "success": "false",
                "message": f"Cluster {cluster_name} already exists",
                "cluster_name": cluster_name
            }
        
        # Create cluster record in database
        cluster_request = ClusterCreateRequest(
            name=cluster_name,
            namespace=namespace,
            cluster_type=cluster_type,
            provider=provider,
            region=region,
            hibernation_enabled=hibernation_enabled,
            metadata={
                "base_domain": base_domain,
                "machine_type": machine_type,
                "worker_nodes": worker_nodes,
                "labels": labels or {},
                "annotations": annotations or {}
            }
        )
        
        cluster = await db_service.create_cluster(cluster_request, user.id)
        
        # Create cluster via ACM
        acm_request = ACMCreateClusterRequest(
            cluster_name=cluster_name,
            namespace=namespace,
            base_domain=base_domain,
            cloud_provider=provider,
            region=region,
            machine_type=machine_type,
            worker_nodes=worker_nodes,
            hibernation_enabled=hibernation_enabled,
            labels=labels,
            annotations=annotations
        )
        
        acm_response = await acm_client.create_cluster(acm_request)
        
        if acm_response.success:
            # Update cluster status to creating
            await db_service.update_cluster(
                cluster.id,
                ClusterUpdateRequest(status=ClusterStatus.CREATING)
            )
            
            logger.info(f"Successfully initiated cluster creation for {cluster_name}")
            
            return {
                "success": "true",
                "message": f"Cluster {cluster_name} creation initiated successfully",
                "cluster_name": cluster_name,
                "cluster_id": str(cluster.id),
                "namespace": namespace,
                "status": "creating",
                "acm_details": acm_response.details
            }
        else:
            # Update cluster status to error
            await db_service.update_cluster(
                cluster.id,
                ClusterUpdateRequest(status=ClusterStatus.ERROR)
            )
            
            # Create error event
            await db_service.create_cluster_event(
                cluster.id,
                ClusterEventType.ERROR_OCCURRED,
                f"Failed to create cluster via ACM: {acm_response.message}",
                {"acm_error": acm_response.details}
            )
            
            return {
                "success": "false",
                "message": f"Failed to create cluster {cluster_name}: {acm_response.message}",
                "cluster_name": cluster_name,
                "cluster_id": str(cluster.id),
                "error_details": acm_response.details
            }
    
    except Exception as e:
        error_msg = f"Unexpected error creating cluster {cluster_name}: {str(e)}"
        logger.error(error_msg)
        
        return {
            "success": "false",
            "message": error_msg,
            "cluster_name": cluster_name,
            "error": str(e)
        }


async def hibernate_cluster(cluster_name: str, force: bool = False) -> Dict[str, str]:
    """Hibernate a cluster to save costs.
    
    Args:
        cluster_name: Name of the cluster to hibernate
        force: Force hibernation even if unsafe
        
    Returns:
        Dictionary with operation result
    """
    try:
        logger.info(f"Hibernating cluster {cluster_name}")
        
        # Initialize services if needed
        if not acm_client._custom_objects_api:
            await acm_client.initialize()
        
        # Get cluster from database
        cluster = await db_service.get_cluster_by_name(cluster_name)
        if not cluster:
            return {
                "success": "false",
                "message": f"Cluster {cluster_name} not found",
                "cluster_name": cluster_name
            }
        
        # Check if hibernation is enabled
        if not cluster.hibernation_enabled:
            return {
                "success": "false",
                "message": f"Hibernation not enabled for cluster {cluster_name}",
                "cluster_name": cluster_name
            }
        
        # Hibernate via ACM
        acm_request = ACMHibernateClusterRequest(
            cluster_name=cluster_name,
            namespace=cluster.namespace,
            force=force
        )
        
        acm_response = await acm_client.hibernate_cluster(acm_request)
        
        if acm_response.success:
            # Update cluster status
            await db_service.update_cluster(
                cluster.id,
                ClusterUpdateRequest(status=ClusterStatus.HIBERNATING)
            )
            
            # Create hibernation event
            await db_service.create_cluster_event(
                cluster.id,
                ClusterEventType.HIBERNATED,
                f"Cluster {cluster_name} hibernation initiated",
                {"force": force}
            )
            
            logger.info(f"Successfully initiated hibernation for cluster {cluster_name}")
            
            return {
                "success": "true",
                "message": f"Cluster {cluster_name} hibernation initiated successfully",
                "cluster_name": cluster_name,
                "cluster_id": str(cluster.id),
                "status": "hibernating"
            }
        else:
            # Create error event
            await db_service.create_cluster_event(
                cluster.id,
                ClusterEventType.ERROR_OCCURRED,
                f"Failed to hibernate cluster: {acm_response.message}",
                {"acm_error": acm_response.details}
            )
            
            return {
                "success": "false",
                "message": f"Failed to hibernate cluster {cluster_name}: {acm_response.message}",
                "cluster_name": cluster_name,
                "cluster_id": str(cluster.id),
                "error_details": acm_response.details
            }
    
    except Exception as e:
        error_msg = f"Unexpected error hibernating cluster {cluster_name}: {str(e)}"
        logger.error(error_msg)
        
        return {
            "success": "false",
            "message": error_msg,
            "cluster_name": cluster_name,
            "error": str(e)
        }


async def resume_cluster(cluster_name: str) -> Dict[str, str]:
    """Resume a hibernated cluster.
    
    Args:
        cluster_name: Name of the cluster to resume
        
    Returns:
        Dictionary with operation result
    """
    try:
        logger.info(f"Resuming cluster {cluster_name}")
        
        # Initialize services if needed
        if not acm_client._custom_objects_api:
            await acm_client.initialize()
        
        # Get cluster from database
        cluster = await db_service.get_cluster_by_name(cluster_name)
        if not cluster:
            return {
                "success": "false",
                "message": f"Cluster {cluster_name} not found",
                "cluster_name": cluster_name
            }
        
        # Resume via ACM
        acm_request = ACMResumeClusterRequest(
            cluster_name=cluster_name,
            namespace=cluster.namespace
        )
        
        acm_response = await acm_client.resume_cluster(acm_request)
        
        if acm_response.success:
            # Update cluster status
            await db_service.update_cluster(
                cluster.id,
                ClusterUpdateRequest(status=ClusterStatus.RESUMING)
            )
            
            # Create resume event
            await db_service.create_cluster_event(
                cluster.id,
                ClusterEventType.RESUMED,
                f"Cluster {cluster_name} resume initiated"
            )
            
            logger.info(f"Successfully initiated resume for cluster {cluster_name}")
            
            return {
                "success": "true",
                "message": f"Cluster {cluster_name} resume initiated successfully",
                "cluster_name": cluster_name,
                "cluster_id": str(cluster.id),
                "status": "resuming"
            }
        else:
            # Create error event
            await db_service.create_cluster_event(
                cluster.id,
                ClusterEventType.ERROR_OCCURRED,
                f"Failed to resume cluster: {acm_response.message}",
                {"acm_error": acm_response.details}
            )
            
            return {
                "success": "false",
                "message": f"Failed to resume cluster {cluster_name}: {acm_response.message}",
                "cluster_name": cluster_name,
                "cluster_id": str(cluster.id),
                "error_details": acm_response.details
            }
    
    except Exception as e:
        error_msg = f"Unexpected error resuming cluster {cluster_name}: {str(e)}"
        logger.error(error_msg)
        
        return {
            "success": "false",
            "message": error_msg,
            "cluster_name": cluster_name,
            "error": str(e)
        }


async def delete_cluster(cluster_name: str, force: bool = False) -> Dict[str, str]:
    """Delete a cluster permanently.
    
    Args:
        cluster_name: Name of the cluster to delete
        force: Force deletion even if unsafe
        
    Returns:
        Dictionary with operation result
    """
    try:
        logger.info(f"Deleting cluster {cluster_name}")
        
        # Initialize services if needed
        if not acm_client._custom_objects_api:
            await acm_client.initialize()
        
        # Get cluster from database
        cluster = await db_service.get_cluster_by_name(cluster_name)
        if not cluster:
            return {
                "success": "false",
                "message": f"Cluster {cluster_name} not found",
                "cluster_name": cluster_name
            }
        
        # Delete via ACM
        acm_request = ACMDeleteClusterRequest(
            cluster_name=cluster_name,
            namespace=cluster.namespace,
            force=force
        )
        
        acm_response = await acm_client.delete_cluster(acm_request)
        
        if acm_response.success:
            # Update cluster status to deleting
            await db_service.update_cluster(
                cluster.id,
                ClusterUpdateRequest(status=ClusterStatus.DELETING)
            )
            
            # Soft delete the cluster in database
            await db_service.soft_delete_cluster(cluster.id)
            
            logger.info(f"Successfully initiated deletion for cluster {cluster_name}")
            
            return {
                "success": "true",
                "message": f"Cluster {cluster_name} deletion initiated successfully",
                "cluster_name": cluster_name,
                "cluster_id": str(cluster.id),
                "status": "deleting"
            }
        else:
            # Create error event
            await db_service.create_cluster_event(
                cluster.id,
                ClusterEventType.ERROR_OCCURRED,
                f"Failed to delete cluster: {acm_response.message}",
                {"acm_error": acm_response.details}
            )
            
            return {
                "success": "false",
                "message": f"Failed to delete cluster {cluster_name}: {acm_response.message}",
                "cluster_name": cluster_name,
                "cluster_id": str(cluster.id),
                "error_details": acm_response.details
            }
    
    except Exception as e:
        error_msg = f"Unexpected error deleting cluster {cluster_name}: {str(e)}"
        logger.error(error_msg)
        
        return {
            "success": "false",
            "message": error_msg,
            "cluster_name": cluster_name,
            "error": str(e)
        }


async def get_cluster_status(cluster_name: str) -> Dict[str, str]:
    """Get the current status of a cluster.
    
    Args:
        cluster_name: Name of the cluster
        
    Returns:
        Dictionary with cluster status information
    """
    try:
        logger.info(f"Getting status for cluster {cluster_name}")
        
        # Initialize services if needed
        if not acm_client._custom_objects_api:
            await acm_client.initialize()
        
        # Get cluster from database
        cluster = await db_service.get_cluster_by_name(cluster_name)
        if not cluster:
            return {
                "success": "false",
                "message": f"Cluster {cluster_name} not found",
                "cluster_name": cluster_name
            }
        
        # Get status from ACM
        acm_response = await acm_client.get_cluster_status(cluster_name, cluster.namespace)
        
        if acm_response.success:
            # Update cluster status in database if it changed
            if cluster.status != acm_response.status:
                await db_service.update_cluster(
                    cluster.id,
                    ClusterUpdateRequest(status=acm_response.status.lower())
                )
                
                # Create status change event
                await db_service.create_cluster_event(
                    cluster.id,
                    ClusterEventType.STATUS_CHANGED,
                    f"Cluster status updated to {acm_response.status}",
                    {"previous_status": cluster.status, "new_status": acm_response.status}
                )
            
            return {
                "success": "true",
                "message": f"Cluster {cluster_name} status retrieved successfully",
                "cluster_name": cluster_name,
                "cluster_id": str(cluster.id),
                "status": acm_response.status,
                "database_status": cluster.status,
                "owner_id": str(cluster.owner_id) if cluster.owner_id else None,
                "namespace": cluster.namespace,
                "provider": cluster.provider,
                "region": cluster.region,
                "hibernation_enabled": str(cluster.hibernation_enabled),
                "created_at": cluster.created_at.isoformat() if cluster.created_at else None,
                "acm_details": acm_response.details
            }
        else:
            return {
                "success": "false",
                "message": f"Failed to get status for cluster {cluster_name}: {acm_response.message}",
                "cluster_name": cluster_name,
                "cluster_id": str(cluster.id),
                "database_status": cluster.status,
                "error_details": acm_response.details
            }
    
    except Exception as e:
        error_msg = f"Unexpected error getting status for cluster {cluster_name}: {str(e)}"
        logger.error(error_msg)
        
        return {
            "success": "false",
            "message": error_msg,
            "cluster_name": cluster_name,
            "error": str(e)
        }


async def list_user_clusters(username: str, status_filter: Optional[str] = None) -> Dict[str, str]:
    """List all clusters owned by a specific user.
    
    Args:
        username: Username of the cluster owner
        status_filter: Optional status filter (e.g., 'ready', 'hibernated')
        
    Returns:
        Dictionary with list of user's clusters
    """
    try:
        logger.info(f"Listing clusters for user {username}")
        
        # Get user
        user = await db_service.get_user_by_username(username)
        if not user:
            return {
                "success": "false",
                "message": f"User {username} not found",
                "username": username
            }
        
        # List clusters for user
        clusters, total_count = await db_service.list_clusters(
            owner_id=user.id,
            status=status_filter,
            page=1,
            page_size=100  # Adjust as needed
        )
        
        cluster_list = []
        for cluster in clusters:
            cluster_info = {
                "id": str(cluster.id),
                "name": cluster.name,
                "namespace": cluster.namespace,
                "status": cluster.status,
                "cluster_type": cluster.cluster_type,
                "provider": cluster.provider,
                "region": cluster.region,
                "hibernation_enabled": str(cluster.hibernation_enabled),
                "created_at": cluster.created_at.isoformat() if cluster.created_at else None,
                "updated_at": cluster.updated_at.isoformat() if cluster.updated_at else None
            }
            cluster_list.append(cluster_info)
        
        return {
            "success": "true",
            "message": f"Found {total_count} clusters for user {username}",
            "username": username,
            "user_id": str(user.id),
            "total_clusters": str(total_count),
            "status_filter": status_filter or "all",
            "clusters": str(cluster_list)  # Convert to string for MCP tool return
        }
    
    except Exception as e:
        error_msg = f"Unexpected error listing clusters for user {username}: {str(e)}"
        logger.error(error_msg)
        
        return {
            "success": "false",
            "message": error_msg,
            "username": username,
            "error": str(e)
        }