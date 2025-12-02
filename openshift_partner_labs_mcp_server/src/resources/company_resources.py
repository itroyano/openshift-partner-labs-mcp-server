"""Company resources for MCP server."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from openshift_partner_labs_mcp_server.src.database.service import db_service
from openshift_partner_labs_mcp_server.src.resources.base import JSONResource, ResourceNotFoundError
from openshift_partner_labs_mcp_server.utils.pylogger import get_python_logger

logger = get_python_logger()


class CompanyResources(JSONResource):
    """Resource handler for company-related data."""

    def _register_uri_patterns(self) -> None:
        """Register URI patterns for company resources."""
        # Company collection resources
        self.add_uri_pattern(r'^companies://all$')
        self.add_uri_pattern(r'^companies://curated$')
        self.add_uri_pattern(r'^companies://with-labs$')

        # Individual company resources
        self.add_uri_pattern(r'^company://(?P<company_id>\d+)$')
        self.add_uri_pattern(r'^company://(?P<company_id>\d+)/labs$')
        self.add_uri_pattern(r'^company://(?P<company_id>\d+)/stats$')
        self.add_uri_pattern(r'^company://name/(?P<company_name>[^/]+)$')
        self.add_uri_pattern(r'^company://name/(?P<company_name>[^/]+)/labs$')
        self.add_uri_pattern(r'^company://name/(?P<company_name>[^/]+)/stats$')

    async def list_resources(self) -> List[Dict[str, Any]]:
        """List all available company resources."""
        resources = [
            {
                "uri": "companies://all",
                "name": "All Companies",
                "description": "Complete list of all companies in the system",
                "mimeType": "application/json"
            },
            {
                "uri": "companies://curated",
                "name": "Curated Partners",
                "description": "List of curated partner companies",
                "mimeType": "application/json"
            },
            {
                "uri": "companies://with-labs",
                "name": "Companies with Labs",
                "description": "Companies that have active or recent labs",
                "mimeType": "application/json"
            }
        ]

        # Add dynamic resources for existing companies
        try:
            companies, _ = await db_service.list_companies(page=1, page_size=100)
            for company in companies:
                resources.extend([
                    {
                        "uri": f"company://{company.id}",
                        "name": f"Company: {company.company_name}",
                        "description": f"Complete details for {company.company_name}",
                        "mimeType": "application/json"
                    },
                    {
                        "uri": f"company://{company.id}/labs",
                        "name": f"Labs: {company.company_name}",
                        "description": f"All labs for {company.company_name}",
                        "mimeType": "application/json"
                    },
                    {
                        "uri": f"company://{company.id}/stats",
                        "name": f"Statistics: {company.company_name}",
                        "description": f"Usage statistics for {company.company_name}",
                        "mimeType": "application/json"
                    },
                    {
                        "uri": f"company://name/{company.company_name}",
                        "name": f"Company by Name: {company.company_name}",
                        "description": f"Company details accessed by name",
                        "mimeType": "application/json"
                    }
                ])
        except Exception as e:
            logger.warning(f"Could not load dynamic company resources: {e}")

        return resources

    async def get_json_data(self, uri: str) -> Dict[str, Any]:
        """Get JSON data for company resources."""
        params = self.extract_uri_params(uri)
        if not params:
            params = {}

        # Company collection resources
        if uri == "companies://all":
            return await self._get_companies_collection()
        elif uri == "companies://curated":
            return await self._get_companies_collection(curated_only=True)
        elif uri == "companies://with-labs":
            return await self._get_companies_with_labs()

        # Individual company resources
        elif uri.startswith("company://") and "/labs" in uri:
            if "name/" in uri:
                company_name = params.get("company_name")
                return await self._get_company_labs_by_name(company_name)
            else:
                company_id = params.get("company_id")
                return await self._get_company_labs(int(company_id))
        elif uri.startswith("company://") and "/stats" in uri:
            if "name/" in uri:
                company_name = params.get("company_name")
                return await self._get_company_stats_by_name(company_name)
            else:
                company_id = params.get("company_id")
                return await self._get_company_stats(int(company_id))
        elif uri.startswith("company://name/"):
            company_name = params.get("company_name")
            return await self._get_company_by_name(company_name)
        elif uri.startswith("company://"):
            company_id = params.get("company_id")
            return await self._get_company_details(int(company_id))

        raise ResourceNotFoundError(f"Unknown company resource: {uri}")

    async def _get_companies_collection(self, curated_only: bool = False,
                                       page_size: int = 50) -> Dict[str, Any]:
        """Get a collection of companies with optional filtering."""
        companies, total_count = await db_service.list_companies(
            page=1,
            page_size=page_size,
            curated_only=curated_only
        )

        companies_data = []
        for company in companies:
            # Get lab count for this company
            lab_count = 0
            try:
                _, lab_count = await db_service.list_labs(
                    company_id=company.id,
                    page=1,
                    page_size=1
                )
            except Exception:
                pass

            company_data = {
                "id": company.id,
                "company_name": company.company_name,
                "curated": bool(company.curated),
                "created_at": company.created_at.isoformat() if company.created_at else None,
                "updated_at": company.updated_at.isoformat() if company.updated_at else None,
                "lab_count": lab_count
            }
            companies_data.append(company_data)

        return {
            "companies": companies_data,
            "total_count": total_count,
            "filtered_by": {
                "curated_only": curated_only
            },
            "metadata": {
                "retrieved_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                "page_size": page_size,
                "total_pages": (total_count + page_size - 1) // page_size
            }
        }

    async def _get_companies_with_labs(self) -> Dict[str, Any]:
        """Get companies that have labs."""
        companies, total_count = await db_service.list_companies(page=1, page_size=100)

        companies_with_labs = []
        for company in companies:
            try:
                labs, lab_count = await db_service.list_labs(
                    company_id=company.id,
                    page=1,
                    page_size=1
                )

                if lab_count > 0:
                    # Get active labs count
                    _, active_count = await db_service.list_labs(
                        company_id=company.id,
                        state="active",
                        page=1,
                        page_size=1
                    )

                    company_data = {
                        "id": company.id,
                        "company_name": company.company_name,
                        "curated": bool(company.curated),
                        "created_at": company.created_at.isoformat() if company.created_at else None,
                        "total_labs": lab_count,
                        "active_labs": active_count
                    }
                    companies_with_labs.append(company_data)

            except Exception as e:
                logger.warning(f"Error checking labs for company {company.id}: {e}")

        return {
            "companies": companies_with_labs,
            "total_count": len(companies_with_labs),
            "metadata": {
                "retrieved_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                "description": "Companies that have created labs"
            }
        }

    async def _get_company_details(self, company_id: int) -> Dict[str, Any]:
        """Get complete details for a specific company."""
        company = await db_service.get_company_by_id(company_id)
        if not company:
            raise ResourceNotFoundError(f"Company with ID {company_id} not found")

        # Get lab statistics
        try:
            _, total_labs = await db_service.list_labs(
                company_id=company.id,
                page=1,
                page_size=1
            )

            _, active_labs = await db_service.list_labs(
                company_id=company.id,
                state="active",
                page=1,
                page_size=1
            )

            _, completed_labs = await db_service.list_labs(
                company_id=company.id,
                state="completed",
                page=1,
                page_size=1
            )

        except Exception as e:
            logger.warning(f"Error getting lab stats for company {company_id}: {e}")
            total_labs = active_labs = completed_labs = 0

        return {
            "id": company.id,
            "company_name": company.company_name,
            "curated": bool(company.curated),
            "created_at": company.created_at.isoformat() if company.created_at else None,
            "updated_at": company.updated_at.isoformat() if company.updated_at else None,
            "lab_statistics": {
                "total_labs": total_labs,
                "active_labs": active_labs,
                "completed_labs": completed_labs
            }
        }

    async def _get_company_by_name(self, company_name: str) -> Dict[str, Any]:
        """Get company details by name."""
        company = await db_service.get_company_by_name(company_name)
        if not company:
            raise ResourceNotFoundError(f"Company with name '{company_name}' not found")

        return await self._get_company_details(company.id)

    async def _get_company_labs(self, company_id: int) -> Dict[str, Any]:
        """Get all labs for a specific company."""
        company = await db_service.get_company_by_id(company_id)
        if not company:
            raise ResourceNotFoundError(f"Company with ID {company_id} not found")

        labs, total_count = await db_service.list_labs(
            company_id=company.id,
            page=1,
            page_size=100
        )

        labs_data = []
        for lab in labs:
            lab_data = {
                "id": lab.id,
                "generated_name": lab.generated_name,
                "cluster_name": lab.cluster_name,
                "state": lab.state,
                "request_type": lab.request_type,
                "cloud_provider": lab.cloud_provider,
                "region": lab.region,
                "openshift_version": lab.openshift_version,
                "cluster_size": lab.cluster_size,
                "start_date": lab.start_date.isoformat(),
                "end_date": lab.end_date.isoformat(),
                "created_at": lab.created_at.isoformat() if lab.created_at else None,
                "sponsor": lab.sponsor,
                "primary_contact": {
                    "first_name": lab.primary_first,
                    "last_name": lab.primary_last,
                    "email": lab.primary_email
                }
            }
            labs_data.append(lab_data)

        return {
            "company": {
                "id": company.id,
                "name": company.company_name,
                "curated": bool(company.curated)
            },
            "labs": labs_data,
            "total_labs": total_count,
            "metadata": {
                "retrieved_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            }
        }

    async def _get_company_labs_by_name(self, company_name: str) -> Dict[str, Any]:
        """Get company labs by company name."""
        company = await db_service.get_company_by_name(company_name)
        if not company:
            raise ResourceNotFoundError(f"Company with name '{company_name}' not found")

        return await self._get_company_labs(company.id)

    async def _get_company_stats(self, company_id: int) -> Dict[str, Any]:
        """Get statistics for a specific company."""
        company = await db_service.get_company_by_id(company_id)
        if not company:
            raise ResourceNotFoundError(f"Company with ID {company_id} not found")

        try:
            # Get overall stats
            _, total_labs = await db_service.list_labs(
                company_id=company.id,
                page=1,
                page_size=1
            )

            # Get stats by state
            states = ["pending", "approved", "active", "extended", "completed", "denied"]
            state_stats = {}
            for state in states:
                _, count = await db_service.list_labs(
                    company_id=company.id,
                    state=state,
                    page=1,
                    page_size=1
                )
                state_stats[state] = count

            # Get stats by request type
            request_types = ["general", "engineering", "rosa", "rhoai", "nvidia", "ocpv"]
            type_stats = {}
            for req_type in request_types:
                _, count = await db_service.list_labs(
                    company_id=company.id,
                    request_type=req_type,
                    page=1,
                    page_size=1
                )
                type_stats[req_type] = count

            # Get stats by cloud provider
            providers = ["AWS", "Azure", "Google", "IBM", "Oracle"]
            provider_stats = {}
            for provider in providers:
                _, count = await db_service.list_labs(
                    company_id=company.id,
                    cloud_provider=provider,
                    page=1,
                    page_size=1
                )
                provider_stats[provider] = count

        except Exception as e:
            logger.warning(f"Error calculating stats for company {company_id}: {e}")
            state_stats = type_stats = provider_stats = {}
            total_labs = 0

        return {
            "company": {
                "id": company.id,
                "name": company.company_name,
                "curated": bool(company.curated)
            },
            "statistics": {
                "total_labs": total_labs,
                "by_state": state_stats,
                "by_request_type": type_stats,
                "by_cloud_provider": provider_stats
            },
            "metadata": {
                "retrieved_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                "calculation_date": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            }
        }

    async def _get_company_stats_by_name(self, company_name: str) -> Dict[str, Any]:
        """Get company statistics by company name."""
        company = await db_service.get_company_by_name(company_name)
        if not company:
            raise ResourceNotFoundError(f"Company with name '{company_name}' not found")

        return await self._get_company_stats(company.id)

    def get_resource_name(self, uri: str) -> Optional[str]:
        """Get display name for company resources."""
        if uri == "companies://all":
            return "All Companies"
        elif uri == "companies://curated":
            return "Curated Partners"
        elif uri == "companies://with-labs":
            return "Companies with Labs"
        elif uri.startswith("company://"):
            params = self.extract_uri_params(uri)
            if params and "company_id" in params:
                return f"Company {params['company_id']}"
            elif params and "company_name" in params:
                return f"Company: {params['company_name']}"
        return None

    def get_resource_description(self, uri: str) -> Optional[str]:
        """Get description for company resources."""
        if uri == "companies://all":
            return "Complete collection of all companies in the system"
        elif uri == "companies://curated":
            return "Collection of curated partner companies"
        elif uri == "companies://with-labs":
            return "Companies that have created labs in the system"
        elif uri.startswith("company://") and "/labs" in uri:
            return "All labs associated with this company"
        elif uri.startswith("company://") and "/stats" in uri:
            return "Usage statistics and metrics for this company"
        elif uri.startswith("company://"):
            return "Complete company details and information"
        return None