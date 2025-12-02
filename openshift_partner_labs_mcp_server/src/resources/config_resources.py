"""Configuration resources for MCP server."""

from typing import Any, Dict, List, Optional

from openshift_partner_labs_mcp_server.src.database.models import (
    CloudProvider,
    ClusterSize,
    LabState,
    Region,
    RequestType,
)
from openshift_partner_labs_mcp_server.src.resources.base import JSONResource, ResourceNotFoundError
from openshift_partner_labs_mcp_server.src.settings import settings
from openshift_partner_labs_mcp_server.utils.pylogger import get_python_logger

logger = get_python_logger()


class ConfigResources(JSONResource):
    """Resource handler for configuration and enumeration data."""

    def _register_uri_patterns(self) -> None:
        """Register URI patterns for configuration resources."""
        self.add_uri_pattern(r'^config://lab-types$')
        self.add_uri_pattern(r'^config://lab-states$')
        self.add_uri_pattern(r'^config://cloud-providers$')
        self.add_uri_pattern(r'^config://regions$')
        self.add_uri_pattern(r'^config://cluster-sizes$')
        self.add_uri_pattern(r'^config://server$')
        self.add_uri_pattern(r'^config://limits$')
        self.add_uri_pattern(r'^config://all$')
        self.add_uri_pattern(r'^config://api-schema$')

    async def list_resources(self) -> List[Dict[str, Any]]:
        """List all available configuration resources."""
        return [
            {
                "uri": "config://lab-types",
                "name": "Lab Request Types",
                "description": "Available lab request types and their descriptions",
                "mimeType": "application/json"
            },
            {
                "uri": "config://lab-states",
                "name": "Lab States",
                "description": "Possible states for labs in the system",
                "mimeType": "application/json"
            },
            {
                "uri": "config://cloud-providers",
                "name": "Cloud Providers",
                "description": "Supported cloud providers for lab deployment",
                "mimeType": "application/json"
            },
            {
                "uri": "config://regions",
                "name": "Deployment Regions",
                "description": "Available regions for lab deployment",
                "mimeType": "application/json"
            },
            {
                "uri": "config://cluster-sizes",
                "name": "Cluster Sizes",
                "description": "Available cluster size options",
                "mimeType": "application/json"
            },
            {
                "uri": "config://server",
                "name": "Server Configuration",
                "description": "MCP server configuration and settings",
                "mimeType": "application/json"
            },
            {
                "uri": "config://limits",
                "name": "System Limits",
                "description": "System limits and constraints",
                "mimeType": "application/json"
            },
            {
                "uri": "config://all",
                "name": "All Configuration",
                "description": "Complete configuration data in one resource",
                "mimeType": "application/json"
            },
            {
                "uri": "config://api-schema",
                "name": "API Schema",
                "description": "Schema definitions for API request/response models",
                "mimeType": "application/json"
            }
        ]

    async def get_json_data(self, uri: str) -> Dict[str, Any]:
        """Get JSON data for configuration resources."""
        if uri == "config://lab-types":
            return await self._get_lab_types()
        elif uri == "config://lab-states":
            return await self._get_lab_states()
        elif uri == "config://cloud-providers":
            return await self._get_cloud_providers()
        elif uri == "config://regions":
            return await self._get_regions()
        elif uri == "config://cluster-sizes":
            return await self._get_cluster_sizes()
        elif uri == "config://server":
            return await self._get_server_config()
        elif uri == "config://limits":
            return await self._get_system_limits()
        elif uri == "config://all":
            return await self._get_all_config()
        elif uri == "config://api-schema":
            return await self._get_api_schema()

        raise ResourceNotFoundError(f"Unknown configuration resource: {uri}")

    async def _get_lab_types(self) -> Dict[str, Any]:
        """Get available lab request types."""
        return {
            "request_types": [
                {
                    "value": RequestType.GENERAL,
                    "display_name": "General Purpose",
                    "description": "Standard OpenShift lab environment for general testing and development"
                },
                {
                    "value": RequestType.ENGINEERING,
                    "display_name": "Engineering",
                    "description": "Engineering-focused lab with development tools and enhanced access"
                },
                {
                    "value": RequestType.ROSA,
                    "display_name": "ROSA",
                    "description": "Red Hat OpenShift Service on AWS environment"
                },
                {
                    "value": RequestType.RHOAI,
                    "display_name": "RHOAI",
                    "description": "Red Hat OpenShift AI platform for machine learning workloads"
                },
                {
                    "value": RequestType.NVIDIA,
                    "display_name": "NVIDIA",
                    "description": "GPU-enabled OpenShift environment for AI/ML workloads"
                },
                {
                    "value": RequestType.OCPV,
                    "display_name": "OpenShift Virtualization",
                    "description": "OpenShift Container Platform with virtualization capabilities"
                }
            ],
            "metadata": {
                "retrieved_at": "2024-12-02T00:00:00Z",
                "total_types": 6
            }
        }

    async def _get_lab_states(self) -> Dict[str, Any]:
        """Get possible lab states."""
        return {
            "states": [
                {
                    "value": LabState.PENDING,
                    "display_name": "Pending",
                    "description": "Lab request submitted and awaiting approval",
                    "is_final": False
                },
                {
                    "value": LabState.APPROVED,
                    "display_name": "Approved",
                    "description": "Lab request approved, cluster creation in progress",
                    "is_final": False
                },
                {
                    "value": LabState.ACTIVE,
                    "display_name": "Active",
                    "description": "Lab is running and accessible to users",
                    "is_final": False
                },
                {
                    "value": LabState.EXTENDED,
                    "display_name": "Extended",
                    "description": "Lab duration has been extended beyond original end date",
                    "is_final": False
                },
                {
                    "value": LabState.COMPLETED,
                    "display_name": "Completed",
                    "description": "Lab has been successfully completed and cleaned up",
                    "is_final": True
                },
                {
                    "value": LabState.DENIED,
                    "display_name": "Denied",
                    "description": "Lab request was denied and will not be provisioned",
                    "is_final": True
                }
            ],
            "state_flow": {
                "normal": [LabState.PENDING, LabState.APPROVED, LabState.ACTIVE, LabState.COMPLETED],
                "with_extension": [LabState.PENDING, LabState.APPROVED, LabState.ACTIVE, LabState.EXTENDED, LabState.COMPLETED],
                "denied": [LabState.PENDING, LabState.DENIED]
            },
            "metadata": {
                "retrieved_at": "2024-12-02T00:00:00Z",
                "total_states": 6
            }
        }

    async def _get_cloud_providers(self) -> Dict[str, Any]:
        """Get supported cloud providers."""
        return {
            "providers": [
                {
                    "value": CloudProvider.AWS,
                    "display_name": "Amazon Web Services",
                    "description": "AWS public cloud platform",
                    "supported_regions": ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"],
                    "supports_gpu": True
                },
                {
                    "value": CloudProvider.AZURE,
                    "display_name": "Microsoft Azure",
                    "description": "Microsoft Azure public cloud platform",
                    "supported_regions": ["eastus", "westus2", "westeurope", "southeastasia"],
                    "supports_gpu": True
                },
                {
                    "value": CloudProvider.GOOGLE,
                    "display_name": "Google Cloud Platform",
                    "description": "Google Cloud public cloud platform",
                    "supported_regions": ["us-central1", "us-west1", "europe-west1", "asia-southeast1"],
                    "supports_gpu": True
                },
                {
                    "value": CloudProvider.IBM,
                    "display_name": "IBM Cloud",
                    "description": "IBM public cloud platform",
                    "supported_regions": ["us-south", "eu-gb", "ap-north"],
                    "supports_gpu": False
                },
                {
                    "value": CloudProvider.ORACLE,
                    "display_name": "Oracle Cloud Infrastructure",
                    "description": "Oracle public cloud platform",
                    "supported_regions": ["us-ashburn-1", "us-phoenix-1", "eu-frankfurt-1"],
                    "supports_gpu": False
                },
                {
                    "value": CloudProvider.ALIBABA,
                    "display_name": "Alibaba Cloud",
                    "description": "Alibaba public cloud platform",
                    "supported_regions": ["cn-hangzhou", "cn-beijing", "ap-southeast-1"],
                    "supports_gpu": False
                },
                {
                    "value": CloudProvider.LINODE,
                    "display_name": "Linode",
                    "description": "Linode cloud platform",
                    "supported_regions": ["us-east", "us-west", "eu-central"],
                    "supports_gpu": False
                },
                {
                    "value": CloudProvider.VULTR,
                    "display_name": "Vultr",
                    "description": "Vultr cloud platform",
                    "supported_regions": ["ewr", "lax", "fra"],
                    "supports_gpu": False
                },
                {
                    "value": CloudProvider.DIGITALO,
                    "display_name": "DigitalOcean",
                    "description": "DigitalOcean cloud platform",
                    "supported_regions": ["nyc1", "nyc3", "sfo3", "fra1"],
                    "supports_gpu": False
                }
            ],
            "metadata": {
                "retrieved_at": "2024-12-02T00:00:00Z",
                "total_providers": 9
            }
        }

    async def _get_regions(self) -> Dict[str, Any]:
        """Get available deployment regions."""
        return {
            "regions": [
                {
                    "value": Region.NA1,
                    "display_name": "North America 1",
                    "description": "Primary North American region (US East)",
                    "timezone": "America/New_York",
                    "primary": True
                },
                {
                    "value": Region.NA2,
                    "display_name": "North America 2",
                    "description": "Secondary North American region (US West)",
                    "timezone": "America/Los_Angeles",
                    "primary": False
                },
                {
                    "value": Region.EMEA,
                    "display_name": "EMEA",
                    "description": "Europe, Middle East, and Africa region",
                    "timezone": "Europe/London",
                    "primary": False
                },
                {
                    "value": Region.APAC1,
                    "display_name": "Asia Pacific 1",
                    "description": "Primary Asia Pacific region",
                    "timezone": "Asia/Singapore",
                    "primary": False
                },
                {
                    "value": Region.APAC2,
                    "display_name": "Asia Pacific 2",
                    "description": "Secondary Asia Pacific region",
                    "timezone": "Asia/Tokyo",
                    "primary": False
                },
                {
                    "value": Region.LATAM,
                    "display_name": "Latin America",
                    "description": "Latin American region",
                    "timezone": "America/Sao_Paulo",
                    "primary": False
                }
            ],
            "metadata": {
                "retrieved_at": "2024-12-02T00:00:00Z",
                "total_regions": 6,
                "default_region": Region.NA1
            }
        }

    async def _get_cluster_sizes(self) -> Dict[str, Any]:
        """Get available cluster sizes."""
        return {
            "sizes": [
                {
                    "value": ClusterSize.SMALL,
                    "display_name": "Small",
                    "description": "Basic cluster for development and testing",
                    "specs": {
                        "worker_nodes": 3,
                        "vcpus_per_node": 2,
                        "memory_per_node_gb": 8,
                        "storage_per_node_gb": 100
                    },
                    "use_cases": ["Development", "Testing", "Learning"]
                },
                {
                    "value": ClusterSize.MEDIUM,
                    "display_name": "Medium",
                    "description": "Standard cluster for moderate workloads",
                    "specs": {
                        "worker_nodes": 3,
                        "vcpus_per_node": 4,
                        "memory_per_node_gb": 16,
                        "storage_per_node_gb": 200
                    },
                    "use_cases": ["Demo", "POC", "Small Production"]
                },
                {
                    "value": ClusterSize.LARGE,
                    "display_name": "Large",
                    "description": "High-performance cluster for intensive workloads",
                    "specs": {
                        "worker_nodes": 5,
                        "vcpus_per_node": 8,
                        "memory_per_node_gb": 32,
                        "storage_per_node_gb": 500
                    },
                    "use_cases": ["Production", "Performance Testing", "AI/ML"]
                },
                {
                    "value": ClusterSize.XLARGE,
                    "display_name": "Extra Large",
                    "description": "Maximum performance cluster for enterprise workloads",
                    "specs": {
                        "worker_nodes": 10,
                        "vcpus_per_node": 16,
                        "memory_per_node_gb": 64,
                        "storage_per_node_gb": 1000
                    },
                    "use_cases": ["Enterprise", "Large Scale", "Heavy AI/ML"]
                },
                {
                    "value": ClusterSize.CUSTOM,
                    "display_name": "Custom",
                    "description": "Custom cluster configuration based on specific requirements",
                    "specs": {
                        "worker_nodes": "Variable",
                        "vcpus_per_node": "Variable",
                        "memory_per_node_gb": "Variable",
                        "storage_per_node_gb": "Variable"
                    },
                    "use_cases": ["Special Requirements", "Research", "Unique Workloads"]
                }
            ],
            "metadata": {
                "retrieved_at": "2024-12-02T00:00:00Z",
                "total_sizes": 5,
                "default_size": ClusterSize.MEDIUM
            }
        }

    async def _get_server_config(self) -> Dict[str, Any]:
        """Get server configuration information."""
        return {
            "server": {
                "name": "OpenShift Partner Labs MCP Server",
                "version": "1.0.0",  # TODO: Get from package version
                "mcp_version": "2025-06-18",
                "capabilities": {
                    "tools": True,
                    "resources": True,
                    "prompts": False,
                    "sampling": False
                }
            },
            "database": {
                "type": "PostgreSQL",
                "host": settings.DATABASE_HOST if hasattr(settings, 'DATABASE_HOST') else "configured",
                "database": settings.DATABASE_NAME if hasattr(settings, 'DATABASE_NAME') else "configured"
            },
            "authentication": {
                "enabled": bool(settings.ENABLE_AUTH) if hasattr(settings, 'ENABLE_AUTH') else False,
                "type": "OAuth2" if hasattr(settings, 'ENABLE_AUTH') and settings.ENABLE_AUTH else None
            },
            "transport": {
                "protocols": ["HTTP", "SSE", "Streamable-HTTP"],
                "default_port": 8000
            },
            "metadata": {
                "retrieved_at": "2024-12-02T00:00:00Z"
            }
        }

    async def _get_system_limits(self) -> Dict[str, Any]:
        """Get system limits and constraints."""
        return {
            "limits": {
                "max_lab_duration_days": 30,
                "max_labs_per_company": 10,
                "max_concurrent_labs": 100,
                "max_extensions": 2,
                "max_extension_days": 14
            },
            "field_limits": {
                "generated_name_max_length": 32,
                "cluster_name_max_length": 32,
                "company_name_max_length": 64,
                "sponsor_email_max_length": 64,
                "contact_name_max_length": 32,
                "contact_email_max_length": 64,
                "description_max_length": 1000,
                "notes_max_length": 2000
            },
            "pagination": {
                "default_page_size": 20,
                "max_page_size": 100
            },
            "metadata": {
                "retrieved_at": "2024-12-02T00:00:00Z",
                "note": "These limits are configurable and may vary by deployment"
            }
        }

    async def _get_all_config(self) -> Dict[str, Any]:
        """Get all configuration data in one resource."""
        return {
            "lab_types": (await self._get_lab_types())["request_types"],
            "lab_states": (await self._get_lab_states())["states"],
            "cloud_providers": (await self._get_cloud_providers())["providers"],
            "regions": (await self._get_regions())["regions"],
            "cluster_sizes": (await self._get_cluster_sizes())["sizes"],
            "server_config": (await self._get_server_config())["server"],
            "limits": (await self._get_system_limits())["limits"],
            "metadata": {
                "retrieved_at": "2024-12-02T00:00:00Z",
                "description": "Complete configuration data for OpenShift Partner Labs"
            }
        }

    async def _get_api_schema(self) -> Dict[str, Any]:
        """Get API schema definitions."""
        return {
            "schemas": {
                "lab_create_request": {
                    "type": "object",
                    "required": [
                        "generated_name", "cluster_name", "openshift_version",
                        "cluster_size", "request_type", "cloud_provider",
                        "primary_first", "primary_last", "primary_email",
                        "secondary_first", "secondary_last", "secondary_email",
                        "region", "project_name", "lease_time",
                        "description", "notes", "start_date", "end_date"
                    ],
                    "properties": {
                        "generated_name": {"type": "string", "maxLength": 32},
                        "cluster_name": {"type": "string", "maxLength": 32},
                        "openshift_version": {"type": "string", "maxLength": 16},
                        "cluster_size": {"type": "string", "enum": [ClusterSize.SMALL, ClusterSize.MEDIUM, ClusterSize.LARGE, ClusterSize.XLARGE, ClusterSize.CUSTOM]},
                        "request_type": {"type": "string", "enum": [RequestType.GENERAL, RequestType.ENGINEERING, RequestType.ROSA, RequestType.RHOAI, RequestType.NVIDIA, RequestType.OCPV]},
                        "cloud_provider": {"type": "string", "enum": [CloudProvider.AWS, CloudProvider.AZURE, CloudProvider.GOOGLE, CloudProvider.IBM, CloudProvider.ORACLE]},
                        "region": {"type": "string", "enum": [Region.NA1, Region.NA2, Region.EMEA, Region.APAC1, Region.APAC2, Region.LATAM]},
                        "partner": {"type": "integer", "enum": [0, 1]},
                        "always_on": {"type": "integer", "enum": [0, 1]},
                        "hold": {"type": "integer", "enum": [0, 1]}
                    }
                },
                "company_create_request": {
                    "type": "object",
                    "required": ["company_name"],
                    "properties": {
                        "company_name": {"type": "string", "maxLength": 64},
                        "curated": {"type": "integer", "enum": [0, 1]}
                    }
                }
            },
            "metadata": {
                "retrieved_at": "2024-12-02T00:00:00Z",
                "description": "JSON Schema definitions for API requests and responses"
            }
        }

    def get_resource_name(self, uri: str) -> Optional[str]:
        """Get display name for configuration resources."""
        name_map = {
            "config://lab-types": "Lab Request Types",
            "config://lab-states": "Lab States",
            "config://cloud-providers": "Cloud Providers",
            "config://regions": "Deployment Regions",
            "config://cluster-sizes": "Cluster Sizes",
            "config://server": "Server Configuration",
            "config://limits": "System Limits",
            "config://all": "All Configuration",
            "config://api-schema": "API Schema"
        }
        return name_map.get(uri)

    def get_resource_description(self, uri: str) -> Optional[str]:
        """Get description for configuration resources."""
        desc_map = {
            "config://lab-types": "Available lab request types and their descriptions",
            "config://lab-states": "Possible states for labs and their transitions",
            "config://cloud-providers": "Supported cloud providers with capabilities",
            "config://regions": "Available deployment regions with timezones",
            "config://cluster-sizes": "Cluster size options with specifications",
            "config://server": "MCP server configuration and capabilities",
            "config://limits": "System limits, constraints, and field validations",
            "config://all": "Complete configuration data in a single resource",
            "config://api-schema": "JSON Schema definitions for API validation"
        }
        return desc_map.get(uri)