"""Template MCP Server implementation.

This module contains the main Template MCP Server class that provides
tools for MCP clients. It uses FastMCP to register and manage MCP capabilities.
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

# Import OpenShift ACM and database tools
from openshift_partner_labs_mcp_server.src.tools.cluster_tools import (
    create_cluster,
    delete_cluster,
    get_cluster_status,
    hibernate_cluster,
    list_user_clusters,
    resume_cluster,
)
from openshift_partner_labs_mcp_server.src.tools.database_tools import (
    create_user,
    get_cluster_events,
    get_user,
    get_user_clusters,
    list_users,
    query_clusters,
    update_cluster_ownership,
)
from openshift_partner_labs_mcp_server.utils.pylogger import (
    force_reconfigure_all_loggers,
    get_python_logger,
)

logger = get_python_logger()


class TemplateMCPServer:
    """Main Template MCP Server implementation following tools-first architecture.

    This server provides only tools, not resources or prompts, adhering to
    the tools-first architectural pattern for MCP servers.
    """

    def __init__(self):
        """Initialize the MCP server with template tools following tools-first architecture."""
        try:
            # Initialize FastMCP server
            self.mcp = FastMCP("template")

            # Force reconfigure all loggers after FastMCP initialization to ensure structured logging
            force_reconfigure_all_loggers(settings.PYTHON_LOG_LEVEL)

            self._register_mcp_tools()

            logger.info("Template MCP Server initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Template MCP Server: {e}")
            raise

    def _register_mcp_tools(self) -> None:
        """Register MCP tools for OpenShift ACM and database operations (tools-first architecture).

        Registers all available tools with the FastMCP server instance.
        In tools-first architecture, the server only provides tools.
        
        Template tools:
        - multiply_numbers: Basic arithmetic operations
        - generate_code_review_prompt: Code review prompt generation
        - get_redhat_logo: Red Hat logo retrieval as base64
        
        Cluster management tools:
        - create_cluster: Create new OpenShift clusters via ACM
        - hibernate_cluster: Put clusters into hibernation mode
        - resume_cluster: Resume hibernated clusters
        - delete_cluster: Delete clusters permanently
        - get_cluster_status: Get current cluster status
        - list_user_clusters: List clusters owned by a user
        
        Database tools:
        - create_user: Create new users
        - get_user: Get user information
        - list_users: List all users with pagination
        - get_user_clusters: Get clusters owned by a user
        - update_cluster_ownership: Transfer cluster ownership
        - get_cluster_events: Get cluster audit events
        - query_clusters: Query clusters with filters
        """
        # Register template tools
        self.mcp.tool()(multiply_numbers)
        self.mcp.tool()(generate_code_review_prompt)
        self.mcp.tool()(get_redhat_logo)
        
        # Register cluster management tools
        self.mcp.tool()(create_cluster)
        self.mcp.tool()(hibernate_cluster)
        self.mcp.tool()(resume_cluster)
        self.mcp.tool()(delete_cluster)
        self.mcp.tool()(get_cluster_status)
        self.mcp.tool()(list_user_clusters)
        
        # Register database tools
        self.mcp.tool()(create_user)
        self.mcp.tool()(get_user)
        self.mcp.tool()(list_users)
        self.mcp.tool()(get_user_clusters)
        self.mcp.tool()(update_cluster_ownership)
        self.mcp.tool()(get_cluster_events)
        self.mcp.tool()(query_clusters)
