"""OpenShift Partner Labs MCP Server implementation.

This module contains the main OpenShift Partner Labs MCP Server class that provides
lab and company management tools for MCP clients. It uses FastMCP to register and
manage MCP capabilities for partner lab workflows.
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
from openshift_partner_labs_mcp_server.src.database.service import db_service
from openshift_partner_labs_mcp_server.src.acm.client import acm_client
from openshift_partner_labs_mcp_server.utils.pylogger import (
    force_reconfigure_all_loggers,
    get_python_logger,
)

logger = get_python_logger()


class TemplateMCPServer:
    """OpenShift Partner Labs MCP Server implementation following tools-first architecture.

    This server provides tools for managing OpenShift Partner Labs, companies,
    and ACM integration. It follows the tools-first architectural pattern.
    """

    def __init__(self):
        """Initialize the MCP server with partner labs tools following tools-first architecture."""
        try:
            # Initialize FastMCP server
            self.mcp = FastMCP("openshift-partner-labs")

            # Force reconfigure all loggers after FastMCP initialization to ensure structured logging
            force_reconfigure_all_loggers(settings.PYTHON_LOG_LEVEL)

            self._register_mcp_tools()

            logger.info("OpenShift Partner Labs MCP Server initialized successfully")

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
        """Register MCP tools for OpenShift Partner Labs management (tools-first architecture).

        Registers all available tools with the FastMCP server instance.
        In tools-first architecture, the server only provides tools.

        Template tools:
        - multiply_numbers: Basic arithmetic operations
        - generate_code_review_prompt: Code review prompt generation
        - get_redhat_logo: Red Hat logo retrieval as base64

        Lab management tools:
        - create_lab: Create new partner lab requests
        - approve_lab: Approve lab requests and initiate cluster creation via ACM
        - deny_lab: Deny lab requests with reason
        - complete_lab: Mark labs as completed and clean up resources
        - extend_lab: Extend lab duration
        - get_lab_status: Get detailed lab status information
        - list_labs: List labs with filtering options

        Company management tools:
        - create_company: Create new partner companies
        - get_company: Get company information
        - list_companies: List companies with pagination
        - get_company_labs: Get labs for a specific company
        - mark_company_curated: Mark companies as curated partners
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
