"""Tests for the MCP server module."""

from unittest.mock import Mock, patch

import pytest

from openshift_partner_labs_mcp_server.src.mcp import PartnerLabsMCPServer


class TestPartnerLabsMCPServer:
    """Test the PartnerLabsMCPServer class."""

    @patch("openshift_partner_labs_mcp_server.src.mcp.force_reconfigure_all_loggers")
    @patch("openshift_partner_labs_mcp_server.src.mcp.settings")
    @patch("openshift_partner_labs_mcp_server.src.mcp.FastMCP")
    @patch("openshift_partner_labs_mcp_server.src.mcp.logger")
    def test_init_success(
        self, mock_logger, mock_fastmcp, mock_settings, mock_force_reconfigure
    ):
        """Test successful initialization of PartnerLabsMCPServer."""
        # Arrange
        mock_mcp = Mock()
        mock_fastmcp.return_value = mock_mcp
        mock_settings.PYTHON_LOG_LEVEL = "INFO"

        # Act
        server = PartnerLabsMCPServer()

        # Assert
        assert server.mcp == mock_mcp
        mock_logger.info.assert_called_with(
            "OpenShift Partner Labs MCP Server initialized successfully with hybrid architecture"
        )
        # In tools-first architecture, we only register tools
        mock_mcp.tool.assert_called()

    @patch("openshift_partner_labs_mcp_server.src.mcp.force_reconfigure_all_loggers")
    @patch("openshift_partner_labs_mcp_server.src.mcp.settings")
    @patch("openshift_partner_labs_mcp_server.src.mcp.FastMCP")
    @patch("openshift_partner_labs_mcp_server.src.mcp.logger")
    def test_init_failure(
        self, mock_logger, mock_fastmcp, mock_settings, mock_force_reconfigure
    ):
        """Test initialization failure handling."""
        # Arrange
        mock_fastmcp.side_effect = Exception("Test error")
        mock_settings.PYTHON_LOG_LEVEL = "INFO"

        # Act & Assert
        with pytest.raises(Exception, match="Test error"):
            PartnerLabsMCPServer()

        mock_logger.error.assert_called_with(
            "Failed to initialize OpenShift Partner Labs MCP Server: Test error"
        )

    @patch("openshift_partner_labs_mcp_server.src.mcp.force_reconfigure_all_loggers")
    @patch("openshift_partner_labs_mcp_server.src.mcp.settings")
    @patch("openshift_partner_labs_mcp_server.src.mcp.FastMCP")
    def test_register_mcp_tools(
        self, mock_fastmcp, mock_settings, mock_force_reconfigure
    ):
        """Test MCP tools registration."""
        # Arrange
        mock_mcp = Mock()
        mock_fastmcp.return_value = mock_mcp
        mock_settings.PYTHON_LOG_LEVEL = "INFO"
        server = PartnerLabsMCPServer()

        # Act
        server._register_mcp_tools()

        # Assert
        mock_mcp.tool.assert_called()

    @patch("openshift_partner_labs_mcp_server.src.mcp.force_reconfigure_all_loggers")
    @patch("openshift_partner_labs_mcp_server.src.mcp.settings")
    @patch("openshift_partner_labs_mcp_server.src.mcp.FastMCP")
    def test_register_mcp_tools_functionality(
        self, mock_fastmcp, mock_settings, mock_force_reconfigure
    ):
        """Test that MCP tools registration includes all expected tools."""
        # Arrange
        mock_mcp = Mock()
        mock_fastmcp.return_value = mock_mcp
        mock_settings.PYTHON_LOG_LEVEL = "INFO"
        server = PartnerLabsMCPServer()

        # Act
        server._register_mcp_tools()

        # Assert
        # Verify that tool() was called multiple times (once for each tool)
        assert (
            mock_mcp.tool.call_count >= 12
        )  # Lab management tools (7) + Company management tools (5)

    def test_server_attributes(self):
        """Test that server has required attributes for hybrid architecture."""
        # Arrange & Act
        with (
            patch(
                "openshift_partner_labs_mcp_server.src.mcp.settings"
            ) as mock_settings,
            patch("openshift_partner_labs_mcp_server.src.mcp.FastMCP"),
            patch(
                "openshift_partner_labs_mcp_server.src.mcp.force_reconfigure_all_loggers"
            ),
        ):
            mock_settings.PYTHON_LOG_LEVEL = "INFO"
            server = PartnerLabsMCPServer()

        # Assert
        assert hasattr(server, "mcp")
        assert hasattr(server, "_register_mcp_tools")

    def test_hybrid_architecture_compliance(self):
        """Test that server adheres to hybrid architecture with both tools and resources."""
        # Arrange & Act
        with (
            patch(
                "openshift_partner_labs_mcp_server.src.mcp.settings"
            ) as mock_settings,
            patch("openshift_partner_labs_mcp_server.src.mcp.FastMCP"),
            patch(
                "openshift_partner_labs_mcp_server.src.mcp.force_reconfigure_all_loggers"
            ),
        ):
            mock_settings.PYTHON_LOG_LEVEL = "INFO"
            server = PartnerLabsMCPServer()

        # Assert - These methods should exist in hybrid architecture
        assert hasattr(server, "_register_mcp_tools"), (
            "_register_mcp_tools should exist in hybrid architecture"
        )
        assert hasattr(server, "_register_mcp_resources"), (
            "_register_mcp_resources should exist in hybrid architecture"
        )
        assert hasattr(server, "_register_mcp_handlers"), (
            "_register_mcp_handlers should exist in hybrid architecture"
        )
        assert hasattr(server, "resource_manager"), (
            "resource_manager should exist in hybrid architecture"
        )
