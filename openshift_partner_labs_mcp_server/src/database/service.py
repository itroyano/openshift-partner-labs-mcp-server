"""Database service layer for OpenShift Partner Labs MCP Server."""

import asyncio
import uuid
from datetime import datetime
from typing import List, Optional, Tuple

import asyncpg
from asyncpg import Pool

from openshift_partner_labs_mcp_server.src.database.models import (
    Company,
    CompanyCreateRequest,
    Lab,
    LabCreateRequest,
    LabEvent,
    LabState,
    LabUpdateRequest,
)
from openshift_partner_labs_mcp_server.src.settings import settings
from openshift_partner_labs_mcp_server.utils.pylogger import get_python_logger

logger = get_python_logger()


class DatabaseService:
    """Database service for managing companies, labs, and events."""

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

    # Company operations

    async def create_company(self, company_request: CompanyCreateRequest) -> Company:
        """Create a new company."""
        pool = await self.get_pool()

        query = """
            INSERT INTO companies (company_name, curated, created_at, updated_at)
            VALUES ($1, $2, $3, $4)
            RETURNING id, company_name, curated, created_at, updated_at
        """

        now = datetime.utcnow()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                query,
                company_request.company_name,
                company_request.curated,
                now,
                now
            )

            return Company(**dict(row))

    async def get_company_by_id(self, company_id: int) -> Optional[Company]:
        """Get company by ID."""
        pool = await self.get_pool()

        query = "SELECT * FROM companies WHERE id = $1"

        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, company_id)

            if row:
                return Company(**dict(row))
            return None

    async def get_company_by_name(self, company_name: str) -> Optional[Company]:
        """Get company by name."""
        pool = await self.get_pool()

        query = "SELECT * FROM companies WHERE company_name = $1"

        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, company_name)

            if row:
                return Company(**dict(row))
            return None

    async def list_companies(self, page: int = 1, page_size: int = 20, curated_only: bool = False) -> Tuple[List[Company], int]:
        """List companies with pagination."""
        pool = await self.get_pool()

        offset = (page - 1) * page_size

        where_clause = ""
        params = []

        if curated_only:
            where_clause = "WHERE curated = true"

        count_query = f"SELECT COUNT(*) FROM companies {where_clause}"
        data_query = f"""
            SELECT * FROM companies
            {where_clause}
            ORDER BY company_name
            LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}
        """

        params.extend([page_size, offset])

        async with pool.acquire() as conn:
            total_count = await conn.fetchval(count_query)
            rows = await conn.fetch(data_query, *params)

            companies = [Company(**dict(row)) for row in rows]
            return companies, total_count

    # Lab operations

    async def create_lab(self, lab_request: LabCreateRequest) -> Lab:
        """Create a new lab."""
        pool = await self.get_pool()

        # Generate UUID for cluster_id
        cluster_uuid = str(uuid.uuid4())

        query = """
            INSERT INTO labs (cluster_id, generated_name, state, cluster_name, openshift_version,
                            cluster_size, company_id, request_type, partner, sponsor, cloud_provider,
                            primary_first, primary_last, primary_email, secondary_first, secondary_last,
                            secondary_email, region, always_on, project_name, lease_time, description,
                            notes, start_date, end_date, hold, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17,
                   $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28)
            RETURNING id, cluster_id, generated_name, state, cluster_name, openshift_version,
                     cluster_size, company_id, request_type, partner, sponsor, cloud_provider,
                     primary_first, primary_last, primary_email, secondary_first, secondary_last,
                     secondary_email, region, always_on, project_name, lease_time, description,
                     notes, start_date, end_date, hold, created_at, updated_at
        """

        now = datetime.utcnow()

        async with pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    query,
                    cluster_uuid,
                    lab_request.generated_name,
                    LabState.PENDING,
                    lab_request.cluster_name,
                    lab_request.openshift_version,
                    lab_request.cluster_size,
                    lab_request.company_id,
                    lab_request.request_type,
                    lab_request.partner,
                    lab_request.sponsor,
                    lab_request.cloud_provider,
                    lab_request.primary_first,
                    lab_request.primary_last,
                    lab_request.primary_email,
                    lab_request.secondary_first,
                    lab_request.secondary_last,
                    lab_request.secondary_email,
                    lab_request.region,
                    lab_request.always_on,
                    lab_request.project_name,
                    lab_request.lease_time,
                    lab_request.description,
                    lab_request.notes,
                    lab_request.start_date,
                    lab_request.end_date,
                    lab_request.hold,
                    now,
                    now
                )

                lab = Lab(**dict(row))

                # Create lab creation event
                await self._create_lab_event(
                    conn,
                    lab.id,
                    "created",
                    f"Lab {lab.generated_name} created"
                )

                return lab

    async def get_lab_by_id(self, lab_id: int) -> Optional[Lab]:
        """Get lab by ID."""
        pool = await self.get_pool()

        query = "SELECT * FROM labs WHERE id = $1"

        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, lab_id)

            if row:
                return Lab(**dict(row))
            return None

    async def get_lab_by_name(self, generated_name: str) -> Optional[Lab]:
        """Get lab by generated name."""
        pool = await self.get_pool()

        query = "SELECT * FROM labs WHERE generated_name = $1"

        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, generated_name)

            if row:
                return Lab(**dict(row))
            return None

    async def get_lab_by_cluster_id(self, cluster_id: str) -> Optional[Lab]:
        """Get lab by cluster UUID."""
        pool = await self.get_pool()

        query = "SELECT * FROM labs WHERE cluster_id = $1"

        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, cluster_id)

            if row:
                return Lab(**dict(row))
            return None

    async def update_lab(self, lab_id: int, update_request: LabUpdateRequest) -> Optional[Lab]:
        """Update lab information."""
        pool = await self.get_pool()

        # Build dynamic update query
        set_clauses = ["updated_at = $1"]
        params = [datetime.utcnow()]
        param_index = 2

        if update_request.state is not None:
            set_clauses.append(f"state = ${param_index}")
            params.append(update_request.state)
            param_index += 1

        if update_request.cluster_name is not None:
            set_clauses.append(f"cluster_name = ${param_index}")
            params.append(update_request.cluster_name)
            param_index += 1

        if update_request.company_id is not None:
            set_clauses.append(f"company_id = ${param_index}")
            params.append(update_request.company_id)
            param_index += 1

        if update_request.always_on is not None:
            set_clauses.append(f"always_on = ${param_index}")
            params.append(update_request.always_on)
            param_index += 1

        if update_request.hold is not None:
            set_clauses.append(f"hold = ${param_index}")
            params.append(update_request.hold)
            param_index += 1

        if update_request.end_date is not None:
            set_clauses.append(f"end_date = ${param_index}")
            params.append(update_request.end_date)
            param_index += 1

        if update_request.notes is not None:
            set_clauses.append(f"notes = ${param_index}")
            params.append(update_request.notes)
            param_index += 1

        query = f"""
            UPDATE labs
            SET {', '.join(set_clauses)}
            WHERE id = ${param_index}
            RETURNING id, cluster_id, generated_name, state, cluster_name, openshift_version,
                     cluster_size, company_id, request_type, partner, sponsor, cloud_provider,
                     primary_first, primary_last, primary_email, secondary_first, secondary_last,
                     secondary_email, region, always_on, project_name, lease_time, description,
                     notes, start_date, end_date, hold, created_at, updated_at
        """
        params.append(lab_id)

        async with pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(query, *params)

                if row:
                    lab = Lab(**dict(row))

                    # Create state change event if state was updated
                    if update_request.state:
                        await self._create_lab_event(
                            conn,
                            lab_id,
                            "state_changed",
                            f"Lab state changed to {update_request.state}"
                        )

                    return lab

                return None

    async def list_labs(self,
                       state: Optional[str] = None,
                       request_type: Optional[str] = None,
                       cloud_provider: Optional[str] = None,
                       region: Optional[str] = None,
                       partner_only: bool = False,
                       company_id: Optional[int] = None,
                       page: int = 1,
                       page_size: int = 20) -> Tuple[List[Lab], int]:
        """List labs with optional filtering and pagination."""
        pool = await self.get_pool()

        where_clauses = []
        params = []
        param_index = 1

        if state is not None:
            where_clauses.append(f"state = ${param_index}")
            params.append(state)
            param_index += 1

        if request_type is not None:
            where_clauses.append(f"request_type = ${param_index}")
            params.append(request_type)
            param_index += 1

        if cloud_provider is not None:
            where_clauses.append(f"cloud_provider = ${param_index}")
            params.append(cloud_provider)
            param_index += 1

        if region is not None:
            where_clauses.append(f"region = ${param_index}")
            params.append(region)
            param_index += 1

        if partner_only:
            where_clauses.append(f"partner = ${param_index}")
            params.append(True)
            param_index += 1

        if company_id is not None:
            where_clauses.append(f"company_id = ${param_index}")
            params.append(company_id)
            param_index += 1

        where_clause = ""
        if where_clauses:
            where_clause = "WHERE " + " AND ".join(where_clauses)

        offset = (page - 1) * page_size

        count_query = f"SELECT COUNT(*) FROM labs {where_clause}"
        data_query = f"""
            SELECT * FROM labs
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ${param_index} OFFSET ${param_index + 1}
        """

        params.extend([page_size, offset])

        async with pool.acquire() as conn:
            total_count = await conn.fetchval(count_query, *params[:-2])
            rows = await conn.fetch(data_query, *params)

            labs = [Lab(**dict(row)) for row in rows]
            return labs, total_count

    # Lab events operations

    async def _create_lab_event(self, conn, lab_id: int, event_type: str,
                               description: str, metadata: Optional[dict] = None) -> LabEvent:
        """Create a lab event (internal method)."""
        query = """
            INSERT INTO lab_events (lab_id, event_type, description, metadata, created_at)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, lab_id, event_type, description, metadata, created_at
        """

        now = datetime.utcnow()

        row = await conn.fetchrow(
            query,
            lab_id,
            event_type,
            description,
            metadata,
            now
        )

        return LabEvent(**dict(row))

    async def create_lab_event(self, lab_id: int, event_type: str,
                              description: str, metadata: Optional[dict] = None) -> LabEvent:
        """Create a lab event."""
        pool = await self.get_pool()

        async with pool.acquire() as conn:
            return await self._create_lab_event(conn, lab_id, event_type, description, metadata)

    async def list_lab_events(self, lab_id: Optional[int] = None,
                             page: int = 1, page_size: int = 50) -> Tuple[List[LabEvent], int]:
        """List lab events with optional filtering and pagination."""
        pool = await self.get_pool()

        where_clause = ""
        params = []
        param_index = 1

        if lab_id is not None:
            where_clause = f"WHERE lab_id = ${param_index}"
            params.append(lab_id)
            param_index += 1

        offset = (page - 1) * page_size

        count_query = f"SELECT COUNT(*) FROM lab_events {where_clause}"
        data_query = f"""
            SELECT * FROM lab_events
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ${param_index} OFFSET ${param_index + 1}
        """

        params.extend([page_size, offset])

        async with pool.acquire() as conn:
            if lab_id is not None:
                total_count = await conn.fetchval(count_query, lab_id)
                rows = await conn.fetch(data_query, *params)
            else:
                total_count = await conn.fetchval(count_query)
                rows = await conn.fetch(data_query, page_size, offset)

            events = [LabEvent(**dict(row)) for row in rows]
            return events, total_count


# Global database service instance
db_service = DatabaseService()