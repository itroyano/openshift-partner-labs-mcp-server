"""Database query MCP tools for user and cluster management."""

from typing import Dict, Optional

from openshift_partner_labs_mcp_server.src.database.models import (
    ClusterUpdateRequest,
    UserCreateRequest,
)
from openshift_partner_labs_mcp_server.src.database.service import db_service
from openshift_partner_labs_mcp_server.utils.pylogger import get_python_logger

logger = get_python_logger()


async def create_user(
    username: str,
    email: str,
    red_hat_uuid: Optional[str] = None
) -> Dict[str, str]:
    """Create a new user in the system.
    
    Args:
        username: Unique username
        email: User's email address
        red_hat_uuid: Optional Red Hat UUID for SSO integration
        
    Returns:
        Dictionary with operation result and user information
    """
    try:
        logger.info(f"Creating user {username}")
        
        # Check if user already exists
        existing_user = await db_service.get_user_by_username(username)
        if existing_user:
            return {
                "success": "false",
                "message": f"User {username} already exists",
                "username": username,
                "user_id": str(existing_user.id)
            }
        
        # Create user
        user_request = UserCreateRequest(
            username=username,
            email=email,
            red_hat_uuid=red_hat_uuid
        )
        
        user = await db_service.create_user(user_request)
        
        logger.info(f"Successfully created user {username} with ID {user.id}")
        
        return {
            "success": "true",
            "message": f"User {username} created successfully",
            "username": username,
            "user_id": str(user.id),
            "email": email,
            "red_hat_uuid": red_hat_uuid or "",
            "created_at": user.created_at.isoformat() if user.created_at else ""
        }
    
    except Exception as e:
        error_msg = f"Unexpected error creating user {username}: {str(e)}"
        logger.error(error_msg)
        
        return {
            "success": "false",
            "message": error_msg,
            "username": username,
            "error": str(e)
        }


async def get_user(username: str) -> Dict[str, str]:
    """Get user information by username.
    
    Args:
        username: Username to lookup
        
    Returns:
        Dictionary with user information
    """
    try:
        logger.info(f"Getting user {username}")
        
        user = await db_service.get_user_by_username(username)
        if not user:
            return {
                "success": "false",
                "message": f"User {username} not found",
                "username": username
            }
        
        return {
            "success": "true",
            "message": f"User {username} found",
            "username": user.username,
            "user_id": str(user.id),
            "email": user.email,
            "red_hat_uuid": user.red_hat_uuid or "",
            "created_at": user.created_at.isoformat() if user.created_at else "",
            "updated_at": user.updated_at.isoformat() if user.updated_at else ""
        }
    
    except Exception as e:
        error_msg = f"Unexpected error getting user {username}: {str(e)}"
        logger.error(error_msg)
        
        return {
            "success": "false",
            "message": error_msg,
            "username": username,
            "error": str(e)
        }


async def list_users(page: int = 1, page_size: int = 20) -> Dict[str, str]:
    """List all users with pagination.
    
    Args:
        page: Page number (1-based)
        page_size: Number of users per page
        
    Returns:
        Dictionary with paginated user list
    """
    try:
        logger.info(f"Listing users (page {page}, size {page_size})")
        
        users, total_count = await db_service.list_users(page=page, page_size=page_size)
        
        user_list = []
        for user in users:
            user_info = {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "red_hat_uuid": user.red_hat_uuid or "",
                "created_at": user.created_at.isoformat() if user.created_at else "",
                "updated_at": user.updated_at.isoformat() if user.updated_at else ""
            }
            user_list.append(user_info)
        
        total_pages = (total_count + page_size - 1) // page_size
        
        return {
            "success": "true",
            "message": f"Found {total_count} users",
            "total_users": str(total_count),
            "page": str(page),
            "page_size": str(page_size),
            "total_pages": str(total_pages),
            "users": str(user_list)  # Convert to string for MCP tool return
        }
    
    except Exception as e:
        error_msg = f"Unexpected error listing users: {str(e)}"
        logger.error(error_msg)
        
        return {
            "success": "false",
            "message": error_msg,
            "page": str(page),
            "page_size": str(page_size),
            "error": str(e)
        }


async def get_user_clusters(username: str, status_filter: Optional[str] = None) -> Dict[str, str]:
    """Get all clusters owned by a specific user.
    
    Args:
        username: Username of the cluster owner
        status_filter: Optional status filter (e.g., 'ready', 'hibernated')
        
    Returns:
        Dictionary with user's clusters
    """
    try:
        logger.info(f"Getting clusters for user {username}")
        
        user = await db_service.get_user_by_username(username)
        if not user:
            return {
                "success": "false",
                "message": f"User {username} not found",
                "username": username
            }
        
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
                "created_at": cluster.created_at.isoformat() if cluster.created_at else "",
                "updated_at": cluster.updated_at.isoformat() if cluster.updated_at else ""
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
        error_msg = f"Unexpected error getting clusters for user {username}: {str(e)}"
        logger.error(error_msg)
        
        return {
            "success": "false",
            "message": error_msg,
            "username": username,
            "error": str(e)
        }


async def update_cluster_ownership(
    cluster_name: str,
    new_owner_username: str
) -> Dict[str, str]:
    """Transfer cluster ownership to a different user.
    
    Args:
        cluster_name: Name of the cluster
        new_owner_username: Username of the new owner
        
    Returns:
        Dictionary with operation result
    """
    try:
        logger.info(f"Transferring ownership of cluster {cluster_name} to {new_owner_username}")
        
        # Get cluster
        cluster = await db_service.get_cluster_by_name(cluster_name)
        if not cluster:
            return {
                "success": "false",
                "message": f"Cluster {cluster_name} not found",
                "cluster_name": cluster_name
            }
        
        # Get new owner
        new_owner = await db_service.get_user_by_username(new_owner_username)
        if not new_owner:
            return {
                "success": "false",
                "message": f"User {new_owner_username} not found",
                "cluster_name": cluster_name,
                "new_owner_username": new_owner_username
            }
        
        # Get current owner for logging
        current_owner = None
        if cluster.owner_id:
            current_owner = await db_service.get_user_by_id(cluster.owner_id)
        
        # Update cluster ownership
        updated_cluster = await db_service.update_cluster(
            cluster.id,
            ClusterUpdateRequest(owner_id=new_owner.id)
        )
        
        if updated_cluster:
            logger.info(f"Successfully transferred ownership of cluster {cluster_name}")
            
            return {
                "success": "true",
                "message": f"Cluster {cluster_name} ownership transferred to {new_owner_username}",
                "cluster_name": cluster_name,
                "cluster_id": str(cluster.id),
                "previous_owner": current_owner.username if current_owner else "none",
                "new_owner": new_owner_username,
                "new_owner_id": str(new_owner.id)
            }
        else:
            return {
                "success": "false",
                "message": f"Failed to update cluster {cluster_name} ownership",
                "cluster_name": cluster_name
            }
    
    except Exception as e:
        error_msg = f"Unexpected error updating cluster ownership: {str(e)}"
        logger.error(error_msg)
        
        return {
            "success": "false",
            "message": error_msg,
            "cluster_name": cluster_name,
            "new_owner_username": new_owner_username,
            "error": str(e)
        }


async def get_cluster_events(
    cluster_name: str,
    page: int = 1,
    page_size: int = 20
) -> Dict[str, str]:
    """Get audit trail events for a specific cluster.
    
    Args:
        cluster_name: Name of the cluster
        page: Page number (1-based)
        page_size: Number of events per page
        
    Returns:
        Dictionary with cluster events
    """
    try:
        logger.info(f"Getting events for cluster {cluster_name}")
        
        # Get cluster
        cluster = await db_service.get_cluster_by_name(cluster_name)
        if not cluster:
            return {
                "success": "false",
                "message": f"Cluster {cluster_name} not found",
                "cluster_name": cluster_name
            }
        
        # Get events
        events, total_count = await db_service.list_cluster_events(
            cluster_id=cluster.id,
            page=page,
            page_size=page_size
        )
        
        event_list = []
        for event in events:
            event_info = {
                "id": str(event.id),
                "event_type": event.event_type,
                "description": event.description or "",
                "metadata": str(event.metadata) if event.metadata else "",
                "created_at": event.created_at.isoformat() if event.created_at else ""
            }
            event_list.append(event_info)
        
        total_pages = (total_count + page_size - 1) // page_size
        
        return {
            "success": "true",
            "message": f"Found {total_count} events for cluster {cluster_name}",
            "cluster_name": cluster_name,
            "cluster_id": str(cluster.id),
            "total_events": str(total_count),
            "page": str(page),
            "page_size": str(page_size),
            "total_pages": str(total_pages),
            "events": str(event_list)  # Convert to string for MCP tool return
        }
    
    except Exception as e:
        error_msg = f"Unexpected error getting events for cluster {cluster_name}: {str(e)}"
        logger.error(error_msg)
        
        return {
            "success": "false",
            "message": error_msg,
            "cluster_name": cluster_name,
            "page": str(page),
            "page_size": str(page_size),
            "error": str(e)
        }


async def query_clusters(
    status_filter: Optional[str] = None,
    provider_filter: Optional[str] = None,
    owner_filter: Optional[str] = None,
    page: int = 1,
    page_size: int = 20
) -> Dict[str, str]:
    """Query clusters with various filters.
    
    Args:
        status_filter: Optional status filter (e.g., 'ready', 'hibernated')
        provider_filter: Optional provider filter (e.g., 'aws', 'azure')
        owner_filter: Optional owner username filter
        page: Page number (1-based)
        page_size: Number of clusters per page
        
    Returns:
        Dictionary with filtered clusters
    """
    try:
        logger.info(f"Querying clusters with filters: status={status_filter}, provider={provider_filter}, owner={owner_filter}")
        
        # Get owner ID if owner filter is provided
        owner_id = None
        if owner_filter:
            owner = await db_service.get_user_by_username(owner_filter)
            if not owner:
                return {
                    "success": "false",
                    "message": f"Owner user {owner_filter} not found",
                    "owner_filter": owner_filter
                }
            owner_id = owner.id
        
        # Note: Current database service doesn't support provider filtering
        # This would need to be enhanced to support additional filters
        clusters, total_count = await db_service.list_clusters(
            owner_id=owner_id,
            status=status_filter,
            page=page,
            page_size=page_size
        )
        
        # Apply provider filter manually (should be moved to database service)
        if provider_filter:
            clusters = [c for c in clusters if c.provider == provider_filter]
            total_count = len(clusters)
        
        cluster_list = []
        for cluster in clusters:
            # Get owner username
            owner_username = ""
            if cluster.owner_id:
                owner = await db_service.get_user_by_id(cluster.owner_id)
                if owner:
                    owner_username = owner.username
            
            cluster_info = {
                "id": str(cluster.id),
                "name": cluster.name,
                "namespace": cluster.namespace,
                "owner_username": owner_username,
                "status": cluster.status,
                "cluster_type": cluster.cluster_type,
                "provider": cluster.provider,
                "region": cluster.region,
                "hibernation_enabled": str(cluster.hibernation_enabled),
                "created_at": cluster.created_at.isoformat() if cluster.created_at else "",
                "updated_at": cluster.updated_at.isoformat() if cluster.updated_at else ""
            }
            cluster_list.append(cluster_info)
        
        total_pages = (total_count + page_size - 1) // page_size
        
        filters_applied = []
        if status_filter:
            filters_applied.append(f"status={status_filter}")
        if provider_filter:
            filters_applied.append(f"provider={provider_filter}")
        if owner_filter:
            filters_applied.append(f"owner={owner_filter}")
        
        return {
            "success": "true",
            "message": f"Found {total_count} clusters matching filters: {', '.join(filters_applied) if filters_applied else 'none'}",
            "total_clusters": str(total_count),
            "page": str(page),
            "page_size": str(page_size),
            "total_pages": str(total_pages),
            "filters": ", ".join(filters_applied) if filters_applied else "none",
            "clusters": str(cluster_list)  # Convert to string for MCP tool return
        }
    
    except Exception as e:
        error_msg = f"Unexpected error querying clusters: {str(e)}"
        logger.error(error_msg)
        
        return {
            "success": "false",
            "message": error_msg,
            "page": str(page),
            "page_size": str(page_size),
            "error": str(e)
        }