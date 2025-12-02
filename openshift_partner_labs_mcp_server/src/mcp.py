"""OpenShift Partner Labs MCP Server implementation.

This module contains the main OpenShift Partner Labs MCP Server class that provides
lab and company management tools and resources for MCP clients. It uses FastMCP to
register and manage MCP capabilities for partner lab workflows.

This server implements a hybrid architecture with both tools and resources:
- Tools: For actions and state modifications (create, approve, deny, etc.)
- Resources: For data access and context provision (lab details, company info, etc.)
"""

from fastmcp import FastMCP

from openshift_partner_labs_mcp_server.src.settings import settings

# Import tools from the tools package
from openshift_partner_labs_mcp_server.src.tools.code_review_tool import (
    generate_code_review_prompt,
)
from openshift_partner_labs_mcp_server.src.tools.multiply_tool import (
    multiply_numbers,
)
from openshift_partner_labs_mcp_server.src.tools.redhat_logo_tool import (
    get_redhat_logo,
)

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
    - Utility tools (multiply, code review prompts, logo retrieval)

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
        """Initialize database and ACM services."""
        try:
            logger.info("Initializing database service...")
            await db_service.initialize()

            logger.info("Initializing ACM client...")
            await acm_client.initialize()

            logger.info("All services initialized successfully")

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

        Template tools:
        - multiply_numbers: Basic arithmetic operations
        - generate_code_review_prompt: Code review prompt generation
        - get_redhat_logo: Red Hat logo retrieval as base64 (DEPRECATED: Use assets://redhat-logo resource)

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
        # Register template tools
        self.mcp.tool()(multiply_numbers)
        self.mcp.tool()(generate_code_review_prompt)
        self.mcp.tool()(get_redhat_logo)

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
        """Register MCP protocol handlers for resources.

        Note: FastMCP automatically handles resources/list and resources/read
        when resources are properly registered. We don't need to manually
        create these handlers as FastMCP will use the resource manager.
        """
        # FastMCP handles resource protocol automatically when we use:
        # - self.mcp.resource() decorator on individual resources
        # - or resource registration through the resource manager

        # For now, we'll rely on the automatic handling by FastMCP
        # The resource manager and individual resource classes handle the logic

        logger.info("MCP resource protocol handlers will be handled automatically by FastMCP")
