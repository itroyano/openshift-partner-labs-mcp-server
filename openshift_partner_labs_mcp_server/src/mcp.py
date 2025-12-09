"""OpenShift Partner Labs MCP Server implementation.

This module contains the main OpenShift Partner Labs MCP Server class that provides
lab and company management tools and resources for MCP clients. It uses FastMCP to
register and manage MCP capabilities for partner lab workflows.

This server implements a hybrid architecture with both tools and resources:
- Tools: For actions and state modifications (create, approve, deny, etc.)
- Resources: For data access and context provision (lab details, company info, etc.)
"""

from typing import Any, Dict, List

from fastmcp import FastMCP

from openshift_partner_labs_mcp_server.src.settings import settings

# Import tools from the tools package

# Import lab management and company tools
from openshift_partner_labs_mcp_server.src.tools.lab_tools import (
    approve_lab,
    complete_lab,
    create_lab,
    deny_lab,
    extend_lab,
    get_lab_status,
    list_labs,
)
from openshift_partner_labs_mcp_server.src.tools.company_tools import (
    create_company,
    get_company,
    get_company_labs,
    list_companies,
    mark_company_curated,
)

# Import resources
from openshift_partner_labs_mcp_server.src.resources import (
    ResourceManager,
    LabResources,
    CompanyResources,
    AssetResources,
    ConfigResources,
)
from openshift_partner_labs_mcp_server.src.resources.asset_resources import (
    AssetInfoResource,
)

from openshift_partner_labs_mcp_server.src.database.service import db_service
from openshift_partner_labs_mcp_server.src.acm.client import acm_client
from openshift_partner_labs_mcp_server.utils.pylogger import (
    force_reconfigure_all_loggers,
    get_python_logger,
)

logger = get_python_logger()


class PartnerLabsMCPServer:
    """OpenShift Partner Labs MCP Server implementation with hybrid tools and resources architecture.

    This server provides both tools and resources for managing OpenShift Partner Labs:

    Tools (for actions):
    - Lab lifecycle management (create, approve, deny, complete, extend)
    - Company management (create, mark curated)

    Resources (for data access):
    - Lab collections and individual lab details
    - Company collections and company-specific data
    - Static assets (logos, branding materials)
    - Configuration data (types, states, providers, regions)

    This hybrid approach provides the best of both worlds: powerful actions via tools
    and efficient context provision via resources.
    """

    def __init__(self):
        """Initialize the MCP server with hybrid tools and resources architecture."""
        try:
            # Initialize FastMCP server
            self.mcp = FastMCP("openshift-partner-labs")

            # Force reconfigure all loggers after FastMCP initialization to ensure structured logging
            force_reconfigure_all_loggers(settings.PYTHON_LOG_LEVEL)

            # Initialize resource manager
            self.resource_manager = ResourceManager()

            # Register MCP capabilities
            self._register_mcp_tools()
            self._register_mcp_resources()
            self._register_mcp_handlers()

            logger.info("OpenShift Partner Labs MCP Server initialized successfully with hybrid architecture")

        except Exception as e:
            logger.error(f"Failed to initialize OpenShift Partner Labs MCP Server: {e}")
            raise

    async def initialize_services(self) -> None:
        """Initialize database and ACM services.
        
        Database initialization is conditional on database configuration being provided.
        If database config is not provided, database features will be unavailable but
        the server will still start for deployments that don't require database access.
        
        ACM initialization is also conditional and will gracefully handle environments
        without Kubernetes access. Tools support lazy initialization, so ACM is not
        required for server startup.
        """
        try:
            # Conditionally initialize database service if configuration is provided
            # Check all required fields including PASSWORD to match service.py validation
            if all([
                settings.DATABASE_HOST,
                settings.DATABASE_PORT,
                settings.DATABASE_DB,
                settings.DATABASE_USER,
                settings.DATABASE_PASSWORD,
            ]):
                logger.info("Initializing database service...")
                await db_service.initialize()
                logger.info("Database service initialized successfully")
            else:
                logger.info("Database configuration not provided - database features will be unavailable")

            # Conditionally initialize ACM client if configuration is available
            # ACM initialization is optional - tools will lazy-initialize on demand
            if hasattr(settings, 'ACM_KUBECONFIG_PATH') and settings.ACM_KUBECONFIG_PATH:
                logger.info("Initializing ACM client with configured kubeconfig...")
                try:
                    await acm_client.initialize()
                    logger.info("ACM client initialized successfully")
                except Exception as e:
                    logger.warning(f"ACM client initialization failed (will use lazy initialization): {e}")
                    logger.info("ACM features will be unavailable until Kubernetes access is configured")
            else:
                # Try to initialize ACM if in-cluster or default kubeconfig is available
                logger.info("Attempting to initialize ACM client...")
                try:
                    await acm_client.initialize()
                    logger.info("ACM client initialized successfully")
                except Exception as e:
                    logger.info(f"ACM client not available (Kubernetes not accessible): {e}")
                    logger.info("ACM features will use lazy initialization when needed")

            logger.info("Service initialization complete")

        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            raise

    async def cleanup(self) -> None:
        """Clean up resources on shutdown."""
        try:
            logger.info("Cleaning up database connections...")
            await db_service.close()

            logger.info("Cleanup completed successfully")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def _register_mcp_tools(self) -> None:
        """Register MCP tools for OpenShift Partner Labs management (hybrid architecture).

        Registers action-oriented tools with the FastMCP server instance.
        In hybrid architecture, tools handle state modifications while resources provide data access.

        Template tools (removed):

        Lab lifecycle management tools (active):
        - create_lab: Create new partner lab requests
        - approve_lab: Approve lab requests and initiate cluster creation via ACM
        - deny_lab: Deny lab requests with reason
        - complete_lab: Mark labs as completed and clean up resources
        - extend_lab: Extend lab duration

        Lab data access tools (DEPRECATED - use resources instead):
        - get_lab_status: Get detailed lab status (→ use lab://{id}/status resource)
        - list_labs: List labs with filtering (→ use labs:// collection resources)

        Company management tools:
        - create_company: Create new partner companies (active)
        - mark_company_curated: Mark companies as curated partners (active)
        - get_company: Get company information (DEPRECATED: use company://{id} resource)
        - list_companies: List companies (DEPRECATED: use companies:// resources)
        - get_company_labs: Get company labs (DEPRECATED: use company://{id}/labs resource)

        Note: Data access tools are maintained for backward compatibility but clients
        should prefer using resources for better performance and caching.
        """
        # Register template tools (removed)

        # Register lab management tools
        self.mcp.tool()(create_lab)
        self.mcp.tool()(approve_lab)
        self.mcp.tool()(deny_lab)
        self.mcp.tool()(complete_lab)
        self.mcp.tool()(extend_lab)
        self.mcp.tool()(get_lab_status)
        self.mcp.tool()(list_labs)

        # Register company management tools
        self.mcp.tool()(create_company)
        self.mcp.tool()(get_company)
        self.mcp.tool()(list_companies)
        self.mcp.tool()(get_company_labs)
        self.mcp.tool()(mark_company_curated)

    def _register_mcp_resources(self) -> None:
        """Register MCP resources for OpenShift Partner Labs data access.

        Registers all available resource handlers with the resource manager.
        Resources provide read-only access to structured data for AI context.

        Lab resources:
        - labs://all, labs://pending, labs://active, etc. - Lab collections
        - lab://{id}, lab://name/{name} - Individual lab details
        - lab://{id}/status, lab://{id}/events - Lab status and events

        Company resources:
        - companies://all, companies://curated - Company collections
        - company://{id}, company://name/{name} - Company details
        - company://{id}/labs, company://{id}/stats - Company labs and statistics

        Asset resources:
        - assets://redhat-logo - Red Hat logo and branding
        - assets://branding/{name} - Branding materials
        - assets://templates/{name} - Document templates

        Configuration resources:
        - config://lab-types, config://cloud-providers - Enumeration data
        - config://regions, config://cluster-sizes - Configuration options
        - config://server, config://limits - Server and system information
        """
        # Register lab resources
        lab_resources = LabResources()
        self.resource_manager.register_resource(lab_resources)

        # Register company resources
        company_resources = CompanyResources()
        self.resource_manager.register_resource(company_resources)

        # Register asset resources
        asset_resources = AssetResources()
        self.resource_manager.register_resource(asset_resources)

        # Register asset info resources
        asset_info_resources = AssetInfoResource()
        self.resource_manager.register_resource(asset_info_resources)

        # Register configuration resources
        config_resources = ConfigResources()
        self.resource_manager.register_resource(config_resources)

        logger.info("Registered all MCP resource handlers")

    def _register_mcp_handlers(self) -> None:
        """Bridge custom ResourceManager resources to FastMCP using the @resource() decorator.

        FastMCP uses a decorator-based approach for resource registration, similar to tools.
        This method creates FastMCP resource decorators for each resource type managed
        by our custom ResourceManager, allowing them to be properly exposed via the MCP protocol.

        The decorator approach is the correct way to register resources with FastMCP v2.10.4.
        """
        # Lab collection resources
        @self.mcp.resource(
            "labs://all",
            name="All Labs",
            description="Complete list of all partner labs",
            mime_type="application/json"
        )
        async def labs_all():
            """Get all labs."""
            return await self.resource_manager.read_resource("labs://all")

        @self.mcp.resource(
            "labs://pending",
            name="Pending Labs",
            description="Labs awaiting approval",
            mime_type="application/json"
        )
        async def labs_pending():
            """Get pending labs."""
            return await self.resource_manager.read_resource("labs://pending")

        @self.mcp.resource(
            "labs://active",
            name="Active Labs",
            description="Currently running labs",
            mime_type="application/json"
        )
        async def labs_active():
            """Get active labs."""
            return await self.resource_manager.read_resource("labs://active")

        @self.mcp.resource(
            "labs://completed",
            name="Completed Labs",
            description="Successfully completed labs",
            mime_type="application/json"
        )
        async def labs_completed():
            """Get completed labs."""
            return await self.resource_manager.read_resource("labs://completed")

        # Individual lab resources with parameters
        @self.mcp.resource(
            "lab://{lab_id}",
            name="Lab Details",
            description="Detailed information about a specific lab",
            mime_type="application/json"
        )
        async def lab_by_id(lab_id: str):
            """Get lab details by ID."""
            return await self.resource_manager.read_resource(f"lab://{lab_id}")

        @self.mcp.resource(
            "lab://name/{lab_name}",
            name="Lab by Name",
            description="Lab information by name",
            mime_type="application/json"
        )
        async def lab_by_name(lab_name: str):
            """Get lab details by name."""
            return await self.resource_manager.read_resource(f"lab://name/{lab_name}")

        @self.mcp.resource(
            "lab://{lab_id}/status",
            name="Lab Status",
            description="Current status and state of a specific lab",
            mime_type="application/json"
        )
        async def lab_status(lab_id: str):
            """Get lab status."""
            return await self.resource_manager.read_resource(f"lab://{lab_id}/status")

        @self.mcp.resource(
            "lab://{lab_id}/events",
            name="Lab Events",
            description="Event history for a specific lab",
            mime_type="application/json"
        )
        async def lab_events(lab_id: str):
            """Get lab events."""
            return await self.resource_manager.read_resource(f"lab://{lab_id}/events")

        # Company collection resources
        @self.mcp.resource(
            "companies://all",
            name="All Companies",
            description="Complete list of partner companies",
            mime_type="application/json"
        )
        async def companies_all():
            """Get all companies."""
            return await self.resource_manager.read_resource("companies://all")

        @self.mcp.resource(
            "companies://curated",
            name="Curated Companies",
            description="Curated partner companies",
            mime_type="application/json"
        )
        async def companies_curated():
            """Get curated companies."""
            return await self.resource_manager.read_resource("companies://curated")

        # Individual company resources
        @self.mcp.resource(
            "company://{company_id}",
            name="Company Details",
            description="Detailed information about a specific company",
            mime_type="application/json"
        )
        async def company_by_id(company_id: str):
            """Get company details by ID."""
            return await self.resource_manager.read_resource(f"company://{company_id}")

        @self.mcp.resource(
            "company://name/{company_name}",
            name="Company by Name",
            description="Company information by name",
            mime_type="application/json"
        )
        async def company_by_name(company_name: str):
            """Get company details by name."""
            return await self.resource_manager.read_resource(f"company://name/{company_name}")

        @self.mcp.resource(
            "company://{company_id}/labs",
            name="Company Labs",
            description="All labs associated with a specific company",
            mime_type="application/json"
        )
        async def company_labs(company_id: str):
            """Get labs for a company."""
            return await self.resource_manager.read_resource(f"company://{company_id}/labs")

        @self.mcp.resource(
            "company://{company_id}/stats",
            name="Company Statistics",
            description="Statistics and metrics for a specific company",
            mime_type="application/json"
        )
        async def company_stats(company_id: str):
            """Get company statistics."""
            return await self.resource_manager.read_resource(f"company://{company_id}/stats")

        # Configuration resources
        @self.mcp.resource(
            "config://lab-types",
            name="Lab Types",
            description="Available lab types and configurations",
            mime_type="application/json"
        )
        async def config_lab_types():
            """Get lab types configuration."""
            return await self.resource_manager.read_resource("config://lab-types")

        @self.mcp.resource(
            "config://cloud-providers",
            name="Cloud Providers",
            description="Supported cloud providers and regions",
            mime_type="application/json"
        )
        async def config_providers():
            """Get cloud providers configuration."""
            return await self.resource_manager.read_resource("config://cloud-providers")

        @self.mcp.resource(
            "config://regions",
            name="Available Regions",
            description="Supported deployment regions",
            mime_type="application/json"
        )
        async def config_regions():
            """Get regions configuration."""
            return await self.resource_manager.read_resource("config://regions")

        @self.mcp.resource(
            "config://cluster-sizes",
            name="Cluster Sizes",
            description="Available cluster size configurations",
            mime_type="application/json"
        )
        async def config_cluster_sizes():
            """Get cluster sizes configuration."""
            return await self.resource_manager.read_resource("config://cluster-sizes")

        @self.mcp.resource(
            "config://server",
            name="Server Configuration",
            description="Server settings and capabilities",
            mime_type="application/json"
        )
        async def config_server():
            """Get server configuration."""
            return await self.resource_manager.read_resource("config://server")

        @self.mcp.resource(
            "config://limits",
            name="System Limits",
            description="Resource limits and quotas",
            mime_type="application/json"
        )
        async def config_limits():
            """Get system limits configuration."""
            return await self.resource_manager.read_resource("config://limits")

        # Asset resources
        @self.mcp.resource(
            "assets://redhat-logo",
            name="Red Hat Logo",
            description="Red Hat logo as base64 encoded PNG",
            mime_type="image/png"
        )
        async def asset_redhat_logo():
            """Get Red Hat logo."""
            return await self.resource_manager.read_resource("assets://redhat-logo")

        @self.mcp.resource(
            "assets://branding/{asset_name}",
            name="Branding Assets",
            description="Red Hat branding materials",
            mime_type="image/png"
        )
        async def asset_branding(asset_name: str):
            """Get branding assets."""
            return await self.resource_manager.read_resource(f"assets://branding/{asset_name}")

        @self.mcp.resource(
            "assets://templates/{template_name}",
            name="Template Assets",
            description="Document and configuration templates",
            mime_type="text/plain"
        )
        async def asset_templates(template_name: str):
            """Get template assets."""
            return await self.resource_manager.read_resource(f"assets://templates/{template_name}")

        @self.mcp.resource(
            "assets://{asset_name}",
            name="Generic Assets",
            description="Static asset files",
            mime_type="application/octet-stream"
        )
        async def asset_generic(asset_name: str):
            """Get generic assets."""
            return await self.resource_manager.read_resource(f"assets://{asset_name}")

        # Asset info resources
        @self.mcp.resource(
            "assets://directory",
            name="Asset Directory",
            description="Directory listing of all available assets",
            mime_type="application/json"
        )
        async def assets_directory():
            """Get asset directory listing."""
            return await self.resource_manager.read_resource("assets://directory")

        @self.mcp.resource(
            "assets://info/{asset_name}",
            name="Asset Information",
            description="Metadata and information about specific assets",
            mime_type="application/json"
        )
        async def asset_info(asset_name: str):
            """Get asset information."""
            return await self.resource_manager.read_resource(f"assets://info/{asset_name}")

        logger.info("Successfully registered all resources with FastMCP using @resource() decorators")
