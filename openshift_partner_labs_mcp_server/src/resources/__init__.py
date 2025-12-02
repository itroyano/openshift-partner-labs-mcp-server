"""OpenShift Partner Labs MCP Server Resources.

This package provides resource-based access to lab and company data following
the Model Context Protocol (MCP) resources specification.

Resources provide read-only access to structured data for AI context, while
tools handle actions and state modifications.
"""

from .base import BaseResource, ResourceManager
from .lab_resources import LabResources
from .company_resources import CompanyResources
from .asset_resources import AssetResources
from .config_resources import ConfigResources

__all__ = [
    "BaseResource",
    "ResourceManager",
    "LabResources",
    "CompanyResources",
    "AssetResources",
    "ConfigResources",
]