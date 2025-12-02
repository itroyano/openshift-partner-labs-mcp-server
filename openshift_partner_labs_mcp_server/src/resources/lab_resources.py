"""Lab resources for MCP server."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from openshift_partner_labs_mcp_server.src.database.service import db_service
from openshift_partner_labs_mcp_server.src.resources.base import JSONResource, ResourceNotFoundError
from openshift_partner_labs_mcp_server.utils.pylogger import get_python_logger

logger = get_python_logger()


class LabResources(JSONResource):
    """Resource handler for lab-related data."""

    def _register_uri_patterns(self) -> None:
        """Register URI patterns for lab resources."""
        # Labs collection resources
        self.add_uri_pattern(r'^labs://all$')
        self.add_uri_pattern(r'^labs://pending$')
        self.add_uri_pattern(r'^labs://active$')
        self.add_uri_pattern(r'^labs://completed$')
        self.add_uri_pattern(r'^labs://denied$')
        self.add_uri_pattern(r'^labs://extended$')
        self.add_uri_pattern(r'^labs://by-company/(?P<company_name>[^/]+)$')
        self.add_uri_pattern(r'^labs://by-region/(?P<region>[^/]+)$')
        self.add_uri_pattern(r'^labs://by-type/(?P<request_type>[^/]+)$')
        self.add_uri_pattern(r'^labs://by-provider/(?P<cloud_provider>[^/]+)$')

        # Individual lab resources
        self.add_uri_pattern(r'^lab://(?P<lab_id>\d+)$')
        self.add_uri_pattern(r'^lab://(?P<lab_id>\d+)/status$')
        self.add_uri_pattern(r'^lab://(?P<lab_id>\d+)/events$')
        self.add_uri_pattern(r'^lab://name/(?P<generated_name>[^/]+)$')
        self.add_uri_pattern(r'^lab://name/(?P<generated_name>[^/]+)/status$')
        self.add_uri_pattern(r'^lab://name/(?P<generated_name>[^/]+)/events$')

    async def list_resources(self) -> List[Dict[str, Any]]:
        """List all available lab resources."""
        resources = [
            {
                "uri": "labs://all",
                "name": "All Labs",
                "description": "Complete list of all labs in the system",
                "mimeType": "application/json"
            },
            {
                "uri": "labs://pending",
                "name": "Pending Labs",
                "description": "Labs awaiting approval",
                "mimeType": "application/json"
            },
            {
                "uri": "labs://active",
                "name": "Active Labs",
                "description": "Currently running labs",
                "mimeType": "application/json"
            },
            {
                "uri": "labs://completed",
                "name": "Completed Labs",
                "description": "Successfully completed labs",
                "mimeType": "application/json"
            },
            {
                "uri": "labs://denied",
                "name": "Denied Labs",
                "description": "Labs that were denied",
                "mimeType": "application/json"
            },
            {
                "uri": "labs://extended",
                "name": "Extended Labs",
                "description": "Labs with extended durations",
                "mimeType": "application/json"
            }
        ]

        # Add dynamic resources for existing labs
        try:
            labs, _ = await db_service.list_labs(page=1, page_size=100)
            for lab in labs:
                resources.extend([
                    {
                        "uri": f"lab://{lab.id}",
                        "name": f"Lab: {lab.generated_name}",
                        "description": f"Complete details for lab {lab.generated_name}",
                        "mimeType": "application/json"
                    },
                    {
                        "uri": f"lab://{lab.id}/status",
                        "name": f"Lab Status: {lab.generated_name}",
                        "description": f"Current status of lab {lab.generated_name}",
                        "mimeType": "application/json"
                    },
                    {
                        "uri": f"lab://name/{lab.generated_name}",
                        "name": f"Lab by Name: {lab.generated_name}",
                        "description": f"Lab details accessed by name",
                        "mimeType": "application/json"
                    }
                ])
        except Exception as e:
            logger.warning(f"Could not load dynamic lab resources: {e}")

        return resources

    async def get_json_data(self, uri: str) -> Dict[str, Any]:
        """Get JSON data for lab resources."""
        params = self.extract_uri_params(uri)
        if not params:
            params = {}

        # Labs collection resources
        if uri == "labs://all":
            return await self._get_labs_collection()
        elif uri == "labs://pending":
            return await self._get_labs_collection(state="pending")
        elif uri == "labs://active":
            return await self._get_labs_collection(state="active")
        elif uri == "labs://completed":
            return await self._get_labs_collection(state="completed")
        elif uri == "labs://denied":
            return await self._get_labs_collection(state="denied")
        elif uri == "labs://extended":
            return await self._get_labs_collection(state="extended")
        elif uri.startswith("labs://by-company/"):
            company_name = params.get("company_name")
            return await self._get_labs_by_company(company_name)
        elif uri.startswith("labs://by-region/"):
            region = params.get("region")
            return await self._get_labs_collection(region=region)
        elif uri.startswith("labs://by-type/"):
            request_type = params.get("request_type")
            return await self._get_labs_collection(request_type=request_type)
        elif uri.startswith("labs://by-provider/"):
            cloud_provider = params.get("cloud_provider")
            return await self._get_labs_collection(cloud_provider=cloud_provider)

        # Individual lab resources
        elif uri.startswith("lab://") and "/status" in uri:
            if "name/" in uri:
                generated_name = params.get("generated_name")
                return await self._get_lab_status_by_name(generated_name)
            else:
                lab_id = params.get("lab_id")
                return await self._get_lab_status(int(lab_id))
        elif uri.startswith("lab://") and "/events" in uri:
            if "name/" in uri:
                generated_name = params.get("generated_name")
                return await self._get_lab_events_by_name(generated_name)
            else:
                lab_id = params.get("lab_id")
                return await self._get_lab_events(int(lab_id))
        elif uri.startswith("lab://name/"):
            generated_name = params.get("generated_name")
            return await self._get_lab_by_name(generated_name)
        elif uri.startswith("lab://"):
            lab_id = params.get("lab_id")
            return await self._get_lab_details(int(lab_id))

        raise ResourceNotFoundError(f"Unknown lab resource: {uri}")

    async def _get_labs_collection(self, state: Optional[str] = None,
                                   request_type: Optional[str] = None,
                                   region: Optional[str] = None,
                                   cloud_provider: Optional[str] = None,
                                   page_size: int = 50) -> Dict[str, Any]:
        """Get a collection of labs with optional filtering."""
        labs, total_count = await db_service.list_labs(
            state=state,
            request_type=request_type,
            region=region,
            cloud_provider=cloud_provider,
            page=1,
            page_size=page_size
        )

        labs_data = []
        for lab in labs:
            # Get company name if available
            company_name = ""
            if lab.company_id:
                try:
                    company = await db_service.get_company_by_id(lab.company_id)
                    if company:
                        company_name = company.company_name
                except Exception:
                    pass

            lab_data = {
                "id": lab.id,
                "generated_name": lab.generated_name,
                "cluster_name": lab.cluster_name,
                "state": lab.state,
                "openshift_version": lab.openshift_version,
                "cluster_size": lab.cluster_size,
                "request_type": lab.request_type,
                "partner": bool(lab.partner),
                "sponsor": lab.sponsor,
                "cloud_provider": lab.cloud_provider,
                "region": lab.region,
                "always_on": bool(lab.always_on),
                "project_name": lab.project_name,
                "lease_time": lab.lease_time,
                "description": lab.description,
                "notes": lab.notes,
                "start_date": lab.start_date.isoformat(),
                "end_date": lab.end_date.isoformat(),
                "hold": bool(lab.hold),
                "created_at": lab.created_at.isoformat() if lab.created_at else None,
                "updated_at": lab.updated_at.isoformat() if lab.updated_at else None,
                "company_name": company_name,
                "primary_contact": {
                    "first_name": lab.primary_first,
                    "last_name": lab.primary_last,
                    "email": lab.primary_email
                },
                "secondary_contact": {
                    "first_name": lab.secondary_first,
                    "last_name": lab.secondary_last,
                    "email": lab.secondary_email
                }
            }
            labs_data.append(lab_data)

        return {
            "labs": labs_data,
            "total_count": total_count,
            "filtered_by": {
                "state": state,
                "request_type": request_type,
                "region": region,
                "cloud_provider": cloud_provider
            },
            "metadata": {
                "retrieved_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                "page_size": page_size,
                "total_pages": (total_count + page_size - 1) // page_size
            }
        }

    async def _get_labs_by_company(self, company_name: str) -> Dict[str, Any]:
        """Get labs for a specific company."""
        if not company_name:
            raise ResourceNotFoundError("Company name is required")

        # Get company first
        company = await db_service.get_company_by_name(company_name)
        if not company:
            raise ResourceNotFoundError(f"Company '{company_name}' not found")

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
            }
            labs_data.append(lab_data)

        return {
            "company": {
                "id": company.id,
                "name": company.company_name,
                "curated": bool(company.curated)
            },
            "labs": labs_data,
            "total_count": total_count,
            "metadata": {
                "retrieved_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            }
        }

    async def _get_lab_details(self, lab_id: int) -> Dict[str, Any]:
        """Get complete details for a specific lab."""
        lab = await db_service.get_lab_by_id(lab_id)
        if not lab:
            raise ResourceNotFoundError(f"Lab with ID {lab_id} not found")

        # Get company name if available
        company_name = ""
        if lab.company_id:
            try:
                company = await db_service.get_company_by_id(lab.company_id)
                if company:
                    company_name = company.company_name
            except Exception:
                pass

        return {
            "id": lab.id,
            "cluster_id": lab.cluster_id,
            "generated_name": lab.generated_name,
            "cluster_name": lab.cluster_name,
            "state": lab.state,
            "openshift_version": lab.openshift_version,
            "cluster_size": lab.cluster_size,
            "request_type": lab.request_type,
            "partner": bool(lab.partner),
            "sponsor": lab.sponsor,
            "cloud_provider": lab.cloud_provider,
            "region": lab.region,
            "always_on": bool(lab.always_on),
            "project_name": lab.project_name,
            "lease_time": lab.lease_time,
            "description": lab.description,
            "notes": lab.notes,
            "start_date": lab.start_date.isoformat(),
            "end_date": lab.end_date.isoformat(),
            "hold": bool(lab.hold),
            "created_at": lab.created_at.isoformat() if lab.created_at else None,
            "updated_at": lab.updated_at.isoformat() if lab.updated_at else None,
            "company_name": company_name,
            "primary_contact": {
                "first_name": lab.primary_first,
                "last_name": lab.primary_last,
                "email": lab.primary_email
            },
            "secondary_contact": {
                "first_name": lab.secondary_first,
                "last_name": lab.secondary_last,
                "email": lab.secondary_email
            }
        }

    async def _get_lab_by_name(self, generated_name: str) -> Dict[str, Any]:
        """Get lab details by generated name."""
        lab = await db_service.get_lab_by_name(generated_name)
        if not lab:
            raise ResourceNotFoundError(f"Lab with name '{generated_name}' not found")

        return await self._get_lab_details(lab.id)

    async def _get_lab_status(self, lab_id: int) -> Dict[str, Any]:
        """Get status summary for a specific lab."""
        lab = await db_service.get_lab_by_id(lab_id)
        if not lab:
            raise ResourceNotFoundError(f"Lab with ID {lab_id} not found")

        return {
            "id": lab.id,
            "generated_name": lab.generated_name,
            "cluster_name": lab.cluster_name,
            "state": lab.state,
            "start_date": lab.start_date.isoformat(),
            "end_date": lab.end_date.isoformat(),
            "created_at": lab.created_at.isoformat() if lab.created_at else None,
            "updated_at": lab.updated_at.isoformat() if lab.updated_at else None,
            "duration_days": (lab.end_date - lab.start_date).days,
            "is_expired": (lab.end_date.replace(tzinfo=timezone.utc) if lab.end_date.tzinfo is None else lab.end_date) < datetime.now(timezone.utc),
            "metadata": {
                "retrieved_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            }
        }

    async def _get_lab_status_by_name(self, generated_name: str) -> Dict[str, Any]:
        """Get lab status by generated name."""
        lab = await db_service.get_lab_by_name(generated_name)
        if not lab:
            raise ResourceNotFoundError(f"Lab with name '{generated_name}' not found")

        return await self._get_lab_status(lab.id)

    async def _get_lab_events(self, lab_id: int) -> Dict[str, Any]:
        """Get events for a specific lab."""
        lab = await db_service.get_lab_by_id(lab_id)
        if not lab:
            raise ResourceNotFoundError(f"Lab with ID {lab_id} not found")

        try:
            events = await db_service.list_lab_events(lab_id)
            events_data = []

            for event in events:
                event_data = {
                    "id": event.id,
                    "event_type": event.event_type,
                    "description": event.description,
                    "metadata": event.metadata,
                    "created_at": event.created_at.isoformat() if event.created_at else None
                }
                events_data.append(event_data)

            return {
                "lab_id": lab_id,
                "generated_name": lab.generated_name,
                "events": events_data,
                "event_count": len(events_data),
                "metadata": {
                    "retrieved_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
                }
            }

        except Exception as e:
            logger.warning(f"Could not retrieve lab events for lab {lab_id}: {e}")
            return {
                "lab_id": lab_id,
                "generated_name": lab.generated_name,
                "events": [],
                "event_count": 0,
                "metadata": {
                    "retrieved_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                    "note": "Event history not available"
                }
            }

    async def _get_lab_events_by_name(self, generated_name: str) -> Dict[str, Any]:
        """Get lab events by generated name."""
        lab = await db_service.get_lab_by_name(generated_name)
        if not lab:
            raise ResourceNotFoundError(f"Lab with name '{generated_name}' not found")

        return await self._get_lab_events(lab.id)

    def get_resource_name(self, uri: str) -> Optional[str]:
        """Get display name for lab resources."""
        if uri == "labs://all":
            return "All Labs"
        elif uri == "labs://pending":
            return "Pending Labs"
        elif uri == "labs://active":
            return "Active Labs"
        elif uri == "labs://completed":
            return "Completed Labs"
        elif uri == "labs://denied":
            return "Denied Labs"
        elif uri == "labs://extended":
            return "Extended Labs"
        elif uri.startswith("lab://"):
            params = self.extract_uri_params(uri)
            if params and "lab_id" in params:
                return f"Lab {params['lab_id']}"
            elif params and "generated_name" in params:
                return f"Lab: {params['generated_name']}"
        return None

    def get_resource_description(self, uri: str) -> Optional[str]:
        """Get description for lab resources."""
        if uri == "labs://all":
            return "Complete collection of all labs in the system"
        elif uri.startswith("labs://"):
            return f"Filtered collection of labs: {uri}"
        elif uri.startswith("lab://") and "/status" in uri:
            return "Current status and summary information for the lab"
        elif uri.startswith("lab://") and "/events" in uri:
            return "Event history and audit trail for the lab"
        elif uri.startswith("lab://"):
            return "Complete lab details including configuration and contacts"
        return None