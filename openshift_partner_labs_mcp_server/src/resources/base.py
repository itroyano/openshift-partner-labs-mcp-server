"""Base resource classes and interfaces for MCP resource implementation."""

import json
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Pattern

from openshift_partner_labs_mcp_server.utils.pylogger import get_python_logger

logger = get_python_logger()


class ResourceNotFoundError(Exception):
    """Raised when a requested resource cannot be found."""
    pass


class BaseResource(ABC):
    """Abstract base class for all MCP resources."""

    def __init__(self):
        """Initialize the base resource."""
        self._uri_patterns: List[Pattern] = []
        self._register_uri_patterns()

    @abstractmethod
    def _register_uri_patterns(self) -> None:
        """Register URI patterns that this resource handles."""
        pass

    @abstractmethod
    async def read(self, uri: str) -> Dict[str, Any]:
        """Read resource content for a given URI.

        Args:
            uri: The resource URI to read

        Returns:
            Dictionary containing resource data with keys:
                - uri: The resource URI
                - name: Display name (optional)
                - description: Resource description (optional)
                - mimeType: MIME type of the content
                - text: Text content (for text resources)
                - blob: Base64 encoded binary content (for binary resources)

        Raises:
            ResourceNotFoundError: If the resource cannot be found
        """
        pass

    @abstractmethod
    async def list_resources(self) -> List[Dict[str, Any]]:
        """List all available resources provided by this resource handler.

        Returns:
            List of resource descriptions with keys:
                - uri: The resource URI
                - name: Display name (optional)
                - description: Resource description (optional)
                - mimeType: MIME type of the content (optional)
        """
        pass

    def can_handle_uri(self, uri: str) -> bool:
        """Check if this resource can handle the given URI.

        Args:
            uri: The URI to check

        Returns:
            True if this resource can handle the URI, False otherwise
        """
        for pattern in self._uri_patterns:
            if pattern.match(uri):
                return True
        return False

    def extract_uri_params(self, uri: str) -> Optional[Dict[str, str]]:
        """Extract parameters from a URI using registered patterns.

        Args:
            uri: The URI to extract parameters from

        Returns:
            Dictionary of extracted parameters, or None if no pattern matches
        """
        for pattern in self._uri_patterns:
            match = pattern.match(uri)
            if match:
                return match.groupdict()
        return None

    def add_uri_pattern(self, pattern: str) -> None:
        """Add a URI pattern that this resource can handle.

        Args:
            pattern: Regular expression pattern for URIs
        """
        self._uri_patterns.append(re.compile(pattern))


class ResourceManager:
    """Manager for all MCP resources in the server."""

    def __init__(self):
        """Initialize the resource manager."""
        self.resources: List[BaseResource] = []
        logger.info("ResourceManager initialized")

    def register_resource(self, resource: BaseResource) -> None:
        """Register a resource handler.

        Args:
            resource: The resource handler to register
        """
        self.resources.append(resource)
        resource_class = resource.__class__.__name__
        logger.info(f"Registered resource handler: {resource_class}")

    async def list_resources(self) -> List[Dict[str, Any]]:
        """List all available resources from all registered handlers.

        Returns:
            Combined list of all available resources
        """
        all_resources = []

        for resource in self.resources:
            try:
                resource_list = await resource.list_resources()
                all_resources.extend(resource_list)
                logger.debug(f"Listed {len(resource_list)} resources from {resource.__class__.__name__}")
            except Exception as e:
                logger.error(f"Error listing resources from {resource.__class__.__name__}: {e}")

        logger.info(f"Total resources available: {len(all_resources)}")
        return all_resources

    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read a resource by URI.

        Args:
            uri: The resource URI to read

        Returns:
            Resource content data

        Raises:
            ResourceNotFoundError: If no handler can provide the resource
        """
        logger.info(f"Reading resource: {uri}")

        for resource in self.resources:
            if resource.can_handle_uri(uri):
                try:
                    content = await resource.read(uri)
                    logger.info(f"Successfully read resource {uri} using {resource.__class__.__name__}")
                    return content
                except ResourceNotFoundError:
                    continue  # Try next resource handler
                except Exception as e:
                    logger.error(f"Error reading resource {uri} with {resource.__class__.__name__}: {e}")
                    continue

        error_msg = f"Resource not found: {uri}"
        logger.warning(error_msg)
        raise ResourceNotFoundError(error_msg)

    def get_capabilities(self) -> Dict[str, Any]:
        """Get resource capabilities for MCP server initialization.

        Returns:
            Capabilities dictionary for MCP server
        """
        return {
            "resources": {
                "subscribe": True,
                "listChanged": True
            }
        }


class JSONResource(BaseResource):
    """Base class for resources that return JSON content."""

    async def read(self, uri: str) -> Dict[str, Any]:
        """Read JSON resource content."""
        data = await self.get_json_data(uri)

        return {
            "uri": uri,
            "name": self.get_resource_name(uri),
            "description": self.get_resource_description(uri),
            "mimeType": "application/json",
            "text": json.dumps(data, indent=2, default=str)
        }

    @abstractmethod
    async def get_json_data(self, uri: str) -> Dict[str, Any]:
        """Get the JSON data for the resource.

        Args:
            uri: The resource URI

        Returns:
            Dictionary containing the resource data
        """
        pass

    def get_resource_name(self, uri: str) -> Optional[str]:
        """Get display name for the resource (optional override).

        Args:
            uri: The resource URI

        Returns:
            Display name or None
        """
        return None

    def get_resource_description(self, uri: str) -> Optional[str]:
        """Get description for the resource (optional override).

        Args:
            uri: The resource URI

        Returns:
            Description or None
        """
        return None


class BinaryResource(BaseResource):
    """Base class for resources that return binary content."""

    async def read(self, uri: str) -> Dict[str, Any]:
        """Read binary resource content."""
        blob_data, mime_type = await self.get_binary_data(uri)

        return {
            "uri": uri,
            "name": self.get_resource_name(uri),
            "description": self.get_resource_description(uri),
            "mimeType": mime_type,
            "blob": blob_data
        }

    @abstractmethod
    async def get_binary_data(self, uri: str) -> tuple[str, str]:
        """Get the binary data for the resource.

        Args:
            uri: The resource URI

        Returns:
            Tuple of (base64_data, mime_type)
        """
        pass

    def get_resource_name(self, uri: str) -> Optional[str]:
        """Get display name for the resource (optional override)."""
        return None

    def get_resource_description(self, uri: str) -> Optional[str]:
        """Get description for the resource (optional override)."""
        return None