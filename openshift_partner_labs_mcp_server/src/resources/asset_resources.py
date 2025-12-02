"""Asset resources for MCP server - handles static files and binary assets."""

import base64
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from openshift_partner_labs_mcp_server.src.resources.base import BinaryResource, JSONResource, ResourceNotFoundError
from openshift_partner_labs_mcp_server.utils.pylogger import get_python_logger

logger = get_python_logger()


class AssetResources(BinaryResource):
    """Resource handler for static assets and binary files."""

    def __init__(self):
        """Initialize asset resources."""
        super().__init__()
        # Get path to assets directory
        current_dir = Path(__file__).parent.parent
        self.assets_dir = current_dir / "assets"

    def _register_uri_patterns(self) -> None:
        """Register URI patterns for asset resources."""
        self.add_uri_pattern(r'^assets://redhat-logo$')
        self.add_uri_pattern(r'^assets://branding/(?P<asset_name>[^/]+)$')
        self.add_uri_pattern(r'^assets://templates/(?P<template_name>[^/]+)$')
        self.add_uri_pattern(r'^assets://(?P<asset_name>[^/]+)$')

    async def list_resources(self) -> List[Dict[str, Any]]:
        """List all available asset resources."""
        resources = [
            {
                "uri": "assets://redhat-logo",
                "name": "Red Hat Logo",
                "description": "Red Hat logo as PNG image",
                "mimeType": "image/png"
            }
        ]

        # Dynamically discover assets if the directory exists
        if self.assets_dir.exists():
            try:
                for asset_file in self.assets_dir.iterdir():
                    if asset_file.is_file() and asset_file.name != "redhat.png":
                        mime_type = self._get_mime_type(asset_file.name)
                        resources.append({
                            "uri": f"assets://{asset_file.stem}",
                            "name": asset_file.name,
                            "description": f"Asset file: {asset_file.name}",
                            "mimeType": mime_type
                        })
            except Exception as e:
                logger.warning(f"Could not scan assets directory: {e}")

        return resources

    async def get_binary_data(self, uri: str) -> tuple[str, str]:
        """Get binary data for asset resources."""
        params = self.extract_uri_params(uri)
        if not params:
            params = {}

        if uri == "assets://redhat-logo":
            return await self._get_redhat_logo()
        elif uri.startswith("assets://branding/"):
            asset_name = params.get("asset_name")
            return await self._get_branding_asset(asset_name)
        elif uri.startswith("assets://templates/"):
            template_name = params.get("template_name")
            return await self._get_template_asset(template_name)
        elif uri.startswith("assets://"):
            asset_name = params.get("asset_name")
            return await self._get_generic_asset(asset_name)

        raise ResourceNotFoundError(f"Unknown asset resource: {uri}")

    async def _get_redhat_logo(self) -> tuple[str, str]:
        """Get the Red Hat logo asset."""
        logo_path = self.assets_dir / "redhat.png"

        if not logo_path.exists():
            raise ResourceNotFoundError(f"Red Hat logo not found at {logo_path}")

        try:
            with open(logo_path, "rb") as f:
                logo_data = f.read()
                logo_base64 = base64.b64encode(logo_data).decode("utf-8")

            logger.info("Successfully retrieved Red Hat logo")
            return logo_base64, "image/png"

        except Exception as e:
            error_msg = f"Error reading Red Hat logo: {str(e)}"
            logger.error(error_msg)
            raise ResourceNotFoundError(error_msg)

    async def _get_branding_asset(self, asset_name: str) -> tuple[str, str]:
        """Get a branding asset."""
        if not asset_name:
            raise ResourceNotFoundError("Asset name is required")

        branding_dir = self.assets_dir / "branding"
        if not branding_dir.exists():
            raise ResourceNotFoundError("Branding assets directory not found")

        # Try to find the asset with various extensions
        possible_extensions = ['.png', '.jpg', '.jpeg', '.svg', '.gif', '.webp']
        asset_path = None

        for ext in possible_extensions:
            candidate_path = branding_dir / f"{asset_name}{ext}"
            if candidate_path.exists():
                asset_path = candidate_path
                break

        if not asset_path:
            raise ResourceNotFoundError(f"Branding asset '{asset_name}' not found")

        try:
            with open(asset_path, "rb") as f:
                asset_data = f.read()
                asset_base64 = base64.b64encode(asset_data).decode("utf-8")

            mime_type = self._get_mime_type(asset_path.name)
            logger.info(f"Successfully retrieved branding asset: {asset_name}")
            return asset_base64, mime_type

        except Exception as e:
            error_msg = f"Error reading branding asset '{asset_name}': {str(e)}"
            logger.error(error_msg)
            raise ResourceNotFoundError(error_msg)

    async def _get_template_asset(self, template_name: str) -> tuple[str, str]:
        """Get a template asset."""
        if not template_name:
            raise ResourceNotFoundError("Template name is required")

        templates_dir = self.assets_dir / "templates"
        if not templates_dir.exists():
            raise ResourceNotFoundError("Templates directory not found")

        # Try common template extensions
        possible_extensions = ['.html', '.md', '.txt', '.json', '.yaml', '.yml']
        template_path = None

        for ext in possible_extensions:
            candidate_path = templates_dir / f"{template_name}{ext}"
            if candidate_path.exists():
                template_path = candidate_path
                break

        if not template_path:
            raise ResourceNotFoundError(f"Template '{template_name}' not found")

        try:
            with open(template_path, "rb") as f:
                template_data = f.read()
                template_base64 = base64.b64encode(template_data).decode("utf-8")

            mime_type = self._get_mime_type(template_path.name)
            logger.info(f"Successfully retrieved template: {template_name}")
            return template_base64, mime_type

        except Exception as e:
            error_msg = f"Error reading template '{template_name}': {str(e)}"
            logger.error(error_msg)
            raise ResourceNotFoundError(error_msg)

    async def _get_generic_asset(self, asset_name: str) -> tuple[str, str]:
        """Get a generic asset from the assets directory."""
        if not asset_name:
            raise ResourceNotFoundError("Asset name is required")

        # Try to find the asset with various extensions
        possible_extensions = ['.png', '.jpg', '.jpeg', '.svg', '.gif', '.webp', '.pdf', '.txt', '.md', '.json']
        asset_path = None

        for ext in possible_extensions:
            candidate_path = self.assets_dir / f"{asset_name}{ext}"
            if candidate_path.exists():
                asset_path = candidate_path
                break

        # Also try exact name match
        if not asset_path:
            candidate_path = self.assets_dir / asset_name
            if candidate_path.exists():
                asset_path = candidate_path

        if not asset_path:
            raise ResourceNotFoundError(f"Asset '{asset_name}' not found")

        try:
            with open(asset_path, "rb") as f:
                asset_data = f.read()
                asset_base64 = base64.b64encode(asset_data).decode("utf-8")

            mime_type = self._get_mime_type(asset_path.name)
            logger.info(f"Successfully retrieved asset: {asset_name}")
            return asset_base64, mime_type

        except Exception as e:
            error_msg = f"Error reading asset '{asset_name}': {str(e)}"
            logger.error(error_msg)
            raise ResourceNotFoundError(error_msg)

    def _get_mime_type(self, filename: str) -> str:
        """Get MIME type for a file based on extension."""
        extension = Path(filename).suffix.lower()

        mime_types = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.svg': 'image/svg+xml',
            '.webp': 'image/webp',
            '.pdf': 'application/pdf',
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.html': 'text/html',
            '.css': 'text/css',
            '.js': 'application/javascript',
            '.json': 'application/json',
            '.yaml': 'application/yaml',
            '.yml': 'application/yaml',
            '.xml': 'application/xml'
        }

        return mime_types.get(extension, 'application/octet-stream')

    def get_resource_name(self, uri: str) -> Optional[str]:
        """Get display name for asset resources."""
        if uri == "assets://redhat-logo":
            return "Red Hat Logo"
        elif uri.startswith("assets://branding/"):
            params = self.extract_uri_params(uri)
            asset_name = params.get("asset_name") if params else None
            return f"Branding: {asset_name}" if asset_name else "Branding Asset"
        elif uri.startswith("assets://templates/"):
            params = self.extract_uri_params(uri)
            template_name = params.get("template_name") if params else None
            return f"Template: {template_name}" if template_name else "Template Asset"
        elif uri.startswith("assets://"):
            params = self.extract_uri_params(uri)
            asset_name = params.get("asset_name") if params else None
            return f"Asset: {asset_name}" if asset_name else "Asset"
        return None

    def get_resource_description(self, uri: str) -> Optional[str]:
        """Get description for asset resources."""
        if uri == "assets://redhat-logo":
            return "Red Hat corporate logo in PNG format"
        elif uri.startswith("assets://branding/"):
            return "Branding asset for marketing and presentation materials"
        elif uri.startswith("assets://templates/"):
            return "Template file for document or configuration generation"
        elif uri.startswith("assets://"):
            return "Static asset file"
        return None


class AssetInfoResource(JSONResource):
    """Resource handler for asset metadata and information."""

    def _register_uri_patterns(self) -> None:
        """Register URI patterns for asset info resources."""
        self.add_uri_pattern(r'^assets://info/(?P<asset_name>[^/]+)$')
        self.add_uri_pattern(r'^assets://directory$')

    async def list_resources(self) -> List[Dict[str, Any]]:
        """List asset information resources."""
        return [
            {
                "uri": "assets://directory",
                "name": "Asset Directory",
                "description": "Directory listing of all available assets",
                "mimeType": "application/json"
            }
        ]

    async def get_json_data(self, uri: str) -> Dict[str, Any]:
        """Get JSON data for asset info resources."""
        params = self.extract_uri_params(uri)
        if not params:
            params = {}

        if uri == "assets://directory":
            return await self._get_assets_directory()
        elif uri.startswith("assets://info/"):
            asset_name = params.get("asset_name")
            return await self._get_asset_info(asset_name)

        raise ResourceNotFoundError(f"Unknown asset info resource: {uri}")

    async def _get_assets_directory(self) -> Dict[str, Any]:
        """Get directory listing of all assets."""
        current_dir = Path(__file__).parent.parent
        assets_dir = current_dir / "assets"

        assets = []
        if assets_dir.exists():
            try:
                for asset_file in assets_dir.iterdir():
                    if asset_file.is_file():
                        asset_info = {
                            "name": asset_file.name,
                            "size_bytes": asset_file.stat().st_size,
                            "modified_at": asset_file.stat().st_mtime,
                            "mime_type": self._get_mime_type(asset_file.name),
                            "uri": f"assets://{asset_file.stem}"
                        }
                        assets.append(asset_info)
            except Exception as e:
                logger.warning(f"Error scanning assets directory: {e}")

        return {
            "assets": assets,
            "total_assets": len(assets),
            "directory_path": str(assets_dir),
            "metadata": {
                "retrieved_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            }
        }

    async def _get_asset_info(self, asset_name: str) -> Dict[str, Any]:
        """Get information about a specific asset."""
        if not asset_name:
            raise ResourceNotFoundError("Asset name is required")

        current_dir = Path(__file__).parent.parent
        assets_dir = current_dir / "assets"

        # Find the asset file
        asset_path = None
        possible_extensions = ['.png', '.jpg', '.jpeg', '.svg', '.gif', '.webp', '.pdf', '.txt', '.md', '.json']

        for ext in possible_extensions:
            candidate_path = assets_dir / f"{asset_name}{ext}"
            if candidate_path.exists():
                asset_path = candidate_path
                break

        if not asset_path:
            # Try exact name match
            candidate_path = assets_dir / asset_name
            if candidate_path.exists():
                asset_path = candidate_path

        if not asset_path:
            raise ResourceNotFoundError(f"Asset '{asset_name}' not found")

        try:
            stat = asset_path.stat()
            return {
                "name": asset_path.name,
                "path": str(asset_path),
                "size_bytes": stat.st_size,
                "created_at": stat.st_ctime,
                "modified_at": stat.st_mtime,
                "mime_type": self._get_mime_type(asset_path.name),
                "uri": f"assets://{asset_name}",
                "metadata": {
                    "retrieved_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
                }
            }
        except Exception as e:
            error_msg = f"Error getting asset info for '{asset_name}': {str(e)}"
            logger.error(error_msg)
            raise ResourceNotFoundError(error_msg)

    def _get_mime_type(self, filename: str) -> str:
        """Get MIME type for a file based on extension."""
        extension = Path(filename).suffix.lower()

        mime_types = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.svg': 'image/svg+xml',
            '.webp': 'image/webp',
            '.pdf': 'application/pdf',
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.html': 'text/html',
            '.json': 'application/json',
            '.yaml': 'application/yaml',
            '.yml': 'application/yaml'
        }

        return mime_types.get(extension, 'application/octet-stream')