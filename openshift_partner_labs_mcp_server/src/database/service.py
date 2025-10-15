"""Database service layer for OpenShift Partner Labs MCP Server."""

import asyncio
from datetime import datetime
from typing import List, Optional, Tuple

import asyncpg
from asyncpg import Pool

from openshift_partner_labs_mcp_server.src.database.models import (
    Cluster,
    ClusterCreateRequest,
    ClusterEvent,
    ClusterEventType,
    ClusterStatus,
    ClusterUpdateRequest,
    User,
    UserCreateRequest,
)
from openshift_partner_labs_mcp_server.src.settings import settings
from openshift_partner_labs_mcp_server.utils.pylogger import get_python_logger

logger = get_python_logger()


class DatabaseService:
    """Database service for managing users, clusters, and events."""
    
    def __init__(self):
        """Initialize database service."""
        self._pool: Optional[Pool] = None
    
    async def initialize(self) -> None:
        """Initialize database connection pool."""
        try:
            if not all([
                settings.POSTGRES_HOST,
                settings.POSTGRES_PORT,
                settings.POSTGRES_DB,
                settings.POSTGRES_USER,
                settings.POSTGRES_PASSWORD
            ]):
                raise ValueError("Missing required PostgreSQL configuration")
            
            dsn = (
                f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
                f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
            )
            
            self._pool = await asyncpg.create_pool(
                dsn,
                min_size=settings.POSTGRES_POOL_SIZE,
                max_size=settings.POSTGRES_MAX_CONNECTIONS,
                command_timeout=60,
            )
            
            logger.info("Database connection pool initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database connection pool: {e}")
            raise
    
    async def close(self) -> None:
        """Close database connection pool."""
        if self._pool:
            await self._pool.close()
            logger.info("Database connection pool closed")
    
    async def get_pool(self) -> Pool:
        """Get database connection pool."""
        if not self._pool:
            await self.initialize()
        return self._pool
    
    # User operations
    
    async def create_user(self, user_request: UserCreateRequest) -> User:
        """Create a new user."""
        pool = await self.get_pool()
        
        query = """
            INSERT INTO users (username, email, red_hat_uuid, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, username, email, red_hat_uuid, created_at, updated_at
        """
        
        now = datetime.utcnow()
        
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                query,
                user_request.username,
                user_request.email,
                user_request.red_hat_uuid,
                now,
                now
            )
            
            return User(**dict(row))
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        pool = await self.get_pool()
        
        query = "SELECT * FROM users WHERE id = $1"
        
        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, user_id)
            
            if row:
                return User(**dict(row))
            return None
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        pool = await self.get_pool()
        
        query = "SELECT * FROM users WHERE username = $1"
        
        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, username)
            
            if row:
                return User(**dict(row))
            return None
    
    async def list_users(self, page: int = 1, page_size: int = 20) -> Tuple[List[User], int]:
        """List users with pagination."""
        pool = await self.get_pool()
        
        offset = (page - 1) * page_size
        
        count_query = "SELECT COUNT(*) FROM users"
        data_query = "SELECT * FROM users ORDER BY created_at DESC LIMIT $1 OFFSET $2"
        
        async with pool.acquire() as conn:
            total_count = await conn.fetchval(count_query)
            rows = await conn.fetch(data_query, page_size, offset)
            
            users = [User(**dict(row)) for row in rows]
            return users, total_count
    
    # Cluster operations
    
    async def create_cluster(self, cluster_request: ClusterCreateRequest, owner_id: int) -> Cluster:
        """Create a new cluster."""
        pool = await self.get_pool()
        
        query = """
            INSERT INTO clusters (name, namespace, owner_id, status, cluster_type, provider, region,
                                hibernation_enabled, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING id, name, namespace, owner_id, status, cluster_type, provider, region,
                     acm_managed_cluster_name, hibernation_enabled, created_at, updated_at, deleted_at
        """
        
        now = datetime.utcnow()
        
        async with pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    query,
                    cluster_request.name,
                    cluster_request.namespace,
                    owner_id,
                    ClusterStatus.PENDING,
                    cluster_request.cluster_type,
                    cluster_request.provider,
                    cluster_request.region,
                    cluster_request.hibernation_enabled,
                    now,
                    now
                )
                
                cluster = Cluster(**dict(row))
                
                # Create cluster creation event
                await self._create_cluster_event(
                    conn,
                    cluster.id,
                    ClusterEventType.CREATED,
                    f"Cluster {cluster.name} created",
                    cluster_request.metadata
                )
                
                return cluster
    
    async def get_cluster_by_id(self, cluster_id: int) -> Optional[Cluster]:
        """Get cluster by ID."""
        pool = await self.get_pool()
        
        query = "SELECT * FROM clusters WHERE id = $1 AND deleted_at IS NULL"
        
        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, cluster_id)
            
            if row:
                return Cluster(**dict(row))
            return None
    
    async def get_cluster_by_name(self, name: str) -> Optional[Cluster]:
        """Get cluster by name."""
        pool = await self.get_pool()
        
        query = "SELECT * FROM clusters WHERE name = $1 AND deleted_at IS NULL"
        
        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, name)
            
            if row:
                return Cluster(**dict(row))
            return None
    
    async def update_cluster(self, cluster_id: int, update_request: ClusterUpdateRequest) -> Optional[Cluster]:
        """Update cluster information."""
        pool = await self.get_pool()
        
        # Build dynamic update query
        set_clauses = ["updated_at = $1"]
        params = [datetime.utcnow()]
        param_index = 2
        
        if update_request.status is not None:
            set_clauses.append(f"status = ${param_index}")
            params.append(update_request.status)
            param_index += 1
        
        if update_request.owner_id is not None:
            set_clauses.append(f"owner_id = ${param_index}")
            params.append(update_request.owner_id)
            param_index += 1
        
        if update_request.hibernation_enabled is not None:
            set_clauses.append(f"hibernation_enabled = ${param_index}")
            params.append(update_request.hibernation_enabled)
            param_index += 1
        
        query = f"""
            UPDATE clusters
            SET {', '.join(set_clauses)}
            WHERE id = ${param_index} AND deleted_at IS NULL
            RETURNING id, name, namespace, owner_id, status, cluster_type, provider, region,
                     acm_managed_cluster_name, hibernation_enabled, created_at, updated_at, deleted_at
        """
        params.append(cluster_id)
        
        async with pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(query, *params)
                
                if row:
                    cluster = Cluster(**dict(row))
                    
                    # Create status change event if status was updated
                    if update_request.status:
                        await self._create_cluster_event(
                            conn,
                            cluster_id,
                            ClusterEventType.STATUS_CHANGED,
                            f"Cluster status changed to {update_request.status}",
                            update_request.metadata
                        )
                    
                    # Create ownership transfer event if owner was updated
                    if update_request.owner_id:
                        await self._create_cluster_event(
                            conn,
                            cluster_id,
                            ClusterEventType.OWNERSHIP_TRANSFERRED,
                            f"Cluster ownership transferred to user {update_request.owner_id}",
                            update_request.metadata
                        )
                    
                    return cluster
                
                return None
    
    async def list_clusters(self, owner_id: Optional[int] = None, status: Optional[str] = None,
                          page: int = 1, page_size: int = 20) -> Tuple[List[Cluster], int]:
        """List clusters with optional filtering and pagination."""
        pool = await self.get_pool()
        
        where_clauses = ["deleted_at IS NULL"]
        params = []
        param_index = 1
        
        if owner_id is not None:
            where_clauses.append(f"owner_id = ${param_index}")
            params.append(owner_id)
            param_index += 1
        
        if status is not None:
            where_clauses.append(f"status = ${param_index}")
            params.append(status)
            param_index += 1
        
        where_clause = " AND ".join(where_clauses)
        offset = (page - 1) * page_size
        
        count_query = f"SELECT COUNT(*) FROM clusters WHERE {where_clause}"
        data_query = f"""
            SELECT * FROM clusters
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ${param_index} OFFSET ${param_index + 1}
        """
        
        params.extend([page_size, offset])
        
        async with pool.acquire() as conn:
            total_count = await conn.fetchval(count_query, *params[:-2])
            rows = await conn.fetch(data_query, *params)
            
            clusters = [Cluster(**dict(row)) for row in rows]
            return clusters, total_count
    
    async def soft_delete_cluster(self, cluster_id: int) -> bool:
        """Soft delete a cluster."""
        pool = await self.get_pool()
        
        query = """
            UPDATE clusters
            SET deleted_at = $1, updated_at = $1, status = $2
            WHERE id = $3 AND deleted_at IS NULL
            RETURNING id
        """
        
        now = datetime.utcnow()
        
        async with pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(query, now, ClusterStatus.DELETED, cluster_id)
                
                if row:
                    await self._create_cluster_event(
                        conn,
                        cluster_id,
                        ClusterEventType.DELETED,
                        f"Cluster {cluster_id} deleted"
                    )
                    return True
                
                return False
    
    # Cluster events operations
    
    async def _create_cluster_event(self, conn, cluster_id: int, event_type: str,
                                  description: str, metadata: Optional[dict] = None) -> ClusterEvent:
        """Create a cluster event (internal method)."""
        query = """
            INSERT INTO cluster_events (cluster_id, event_type, description, metadata, created_at)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, cluster_id, event_type, description, metadata, created_at
        """
        
        now = datetime.utcnow()
        
        row = await conn.fetchrow(
            query,
            cluster_id,
            event_type,
            description,
            metadata,
            now
        )
        
        return ClusterEvent(**dict(row))
    
    async def create_cluster_event(self, cluster_id: int, event_type: str,
                                 description: str, metadata: Optional[dict] = None) -> ClusterEvent:
        """Create a cluster event."""
        pool = await self.get_pool()
        
        async with pool.acquire() as conn:
            return await self._create_cluster_event(conn, cluster_id, event_type, description, metadata)
    
    async def list_cluster_events(self, cluster_id: Optional[int] = None,
                                page: int = 1, page_size: int = 50) -> Tuple[List[ClusterEvent], int]:
        """List cluster events with optional filtering and pagination."""
        pool = await self.get_pool()
        
        where_clause = ""
        params = []
        param_index = 1
        
        if cluster_id is not None:
            where_clause = f"WHERE cluster_id = ${param_index}"
            params.append(cluster_id)
            param_index += 1
        
        offset = (page - 1) * page_size
        
        count_query = f"SELECT COUNT(*) FROM cluster_events {where_clause}"
        data_query = f"""
            SELECT * FROM cluster_events
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ${param_index} OFFSET ${param_index + 1}
        """
        
        params.extend([page_size, offset])
        
        async with pool.acquire() as conn:
            if cluster_id is not None:
                total_count = await conn.fetchval(count_query, cluster_id)
                rows = await conn.fetch(data_query, *params)
            else:
                total_count = await conn.fetchval(count_query)
                rows = await conn.fetch(data_query, page_size, offset)
            
            events = [ClusterEvent(**dict(row)) for row in rows]
            return events, total_count


# Global database service instance
db_service = DatabaseService()