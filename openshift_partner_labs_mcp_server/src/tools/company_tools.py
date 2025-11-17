"""Company management MCP tools for OpenShift Partner Labs."""

from typing import Dict, Optional

from openshift_partner_labs_mcp_server.src.database.models import CompanyCreateRequest
from openshift_partner_labs_mcp_server.src.database.service import db_service
from openshift_partner_labs_mcp_server.utils.pylogger import get_python_logger

logger = get_python_logger()


async def create_company(
    company_name: str,
    curated: int = 0
) -> Dict[str, str]:
    """Create a new company in the system.

    Args:
        company_name: Name of the company (max 64 chars)
        curated: Whether this is a curated partner company (0=no, 1=yes)

    Returns:
        Dictionary with operation result and company information
    """
    try:
        logger.info(f"Creating company {company_name}")

        # Check if company already exists
        existing_company = await db_service.get_company_by_name(company_name)
        if existing_company:
            return {
                "success": "false",
                "message": f"Company {company_name} already exists",
                "company_name": company_name,
                "company_id": str(existing_company.id)
            }

        # Create company
        company_request = CompanyCreateRequest(
            company_name=company_name,
            curated=curated
        )

        company = await db_service.create_company(company_request)

        logger.info(f"Successfully created company {company_name} with ID {company.id}")

        return {
            "success": "true",
            "message": f"Company {company_name} created successfully",
            "company_id": str(company.id),
            "company_name": company_name,
            "curated": str(curated),
            "created_at": company.created_at.isoformat() if company.created_at else ""
        }

    except Exception as e:
        error_msg = f"Unexpected error creating company {company_name}: {str(e)}"
        logger.error(error_msg)

        return {
            "success": "false",
            "message": error_msg,
            "company_name": company_name,
            "error": str(e)
        }


async def get_company(company_name: str) -> Dict[str, str]:
    """Get company information by name.

    Args:
        company_name: Name of the company to lookup

    Returns:
        Dictionary with company information
    """
    try:
        logger.info(f"Getting company {company_name}")

        company = await db_service.get_company_by_name(company_name)
        if not company:
            return {
                "success": "false",
                "message": f"Company {company_name} not found",
                "company_name": company_name
            }

        return {
            "success": "true",
            "message": f"Company {company_name} found",
            "company_id": str(company.id),
            "company_name": company.company_name,
            "curated": str(company.curated),
            "created_at": company.created_at.isoformat() if company.created_at else "",
            "updated_at": company.updated_at.isoformat() if company.updated_at else ""
        }

    except Exception as e:
        error_msg = f"Unexpected error getting company {company_name}: {str(e)}"
        logger.error(error_msg)

        return {
            "success": "false",
            "message": error_msg,
            "company_name": company_name,
            "error": str(e)
        }


async def list_companies(
    page: int = 1,
    page_size: int = 20,
    curated_only: bool = False
) -> Dict[str, str]:
    """List all companies with pagination.

    Args:
        page: Page number (1-based)
        page_size: Number of companies per page
        curated_only: Show only curated partner companies

    Returns:
        Dictionary with paginated company list
    """
    try:
        logger.info(f"Listing companies (page {page}, size {page_size}, curated_only={curated_only})")

        companies, total_count = await db_service.list_companies(
            page=page,
            page_size=page_size,
            curated_only=curated_only
        )

        company_list = []
        for company in companies:
            company_info = {
                "id": str(company.id),
                "company_name": company.company_name,
                "curated": str(company.curated),
                "created_at": company.created_at.isoformat() if company.created_at else "",
                "updated_at": company.updated_at.isoformat() if company.updated_at else ""
            }
            company_list.append(company_info)

        total_pages = (total_count + page_size - 1) // page_size

        return {
            "success": "true",
            "message": f"Found {total_count} companies",
            "total_companies": str(total_count),
            "page": str(page),
            "page_size": str(page_size),
            "total_pages": str(total_pages),
            "curated_only": str(curated_only),
            "companies": str(company_list)  # Convert to string for MCP tool return
        }

    except Exception as e:
        error_msg = f"Unexpected error listing companies: {str(e)}"
        logger.error(error_msg)

        return {
            "success": "false",
            "message": error_msg,
            "page": str(page),
            "page_size": str(page_size),
            "error": str(e)
        }


async def get_company_labs(
    company_name: str,
    state: Optional[str] = None,
    page: int = 1,
    page_size: int = 20
) -> Dict[str, str]:
    """Get all labs for a specific company.

    Args:
        company_name: Name of the company
        state: Optional state filter (pending, approved, active, extended, completed, denied)
        page: Page number (1-based)
        page_size: Number of labs per page

    Returns:
        Dictionary with company's labs
    """
    try:
        logger.info(f"Getting labs for company {company_name}")

        # Get company
        company = await db_service.get_company_by_name(company_name)
        if not company:
            return {
                "success": "false",
                "message": f"Company {company_name} not found",
                "company_name": company_name
            }

        # List labs for company
        labs, total_count = await db_service.list_labs(
            company_id=company.id,
            state=state,
            page=page,
            page_size=page_size
        )

        lab_list = []
        for lab in labs:
            lab_info = {
                "id": str(lab.id),
                "generated_name": lab.generated_name,
                "cluster_name": lab.cluster_name,
                "state": lab.state,
                "request_type": lab.request_type,
                "cloud_provider": lab.cloud_provider,
                "region": lab.region,
                "openshift_version": lab.openshift_version,
                "cluster_size": lab.cluster_size,
                "partner": str(lab.partner),
                "sponsor": lab.sponsor,
                "primary_contact": f"{lab.primary_first} {lab.primary_last} <{lab.primary_email}>",
                "start_date": lab.start_date.isoformat(),
                "end_date": lab.end_date.isoformat(),
                "created_at": lab.created_at.isoformat() if lab.created_at else ""
            }
            lab_list.append(lab_info)

        total_pages = (total_count + page_size - 1) // page_size

        return {
            "success": "true",
            "message": f"Found {total_count} labs for company {company_name}",
            "company_name": company_name,
            "company_id": str(company.id),
            "total_labs": str(total_count),
            "page": str(page),
            "page_size": str(page_size),
            "total_pages": str(total_pages),
            "state_filter": state or "all",
            "labs": str(lab_list)  # Convert to string for MCP tool return
        }

    except Exception as e:
        error_msg = f"Unexpected error getting labs for company {company_name}: {str(e)}"
        logger.error(error_msg)

        return {
            "success": "false",
            "message": error_msg,
            "company_name": company_name,
            "page": str(page),
            "page_size": str(page_size),
            "error": str(e)
        }


async def mark_company_curated(company_name: str, curated: int = 1) -> Dict[str, str]:
    """Mark a company as curated or remove curated status.

    Args:
        company_name: Name of the company
        curated: Whether to mark as curated (1) or remove curation (0)

    Returns:
        Dictionary with operation result
    """
    try:
        logger.info(f"{'Marking' if curated else 'Unmarking'} company {company_name} as curated")

        # Get company
        company = await db_service.get_company_by_name(company_name)
        if not company:
            return {
                "success": "false",
                "message": f"Company {company_name} not found",
                "company_name": company_name
            }

        if company.curated == curated:
            status = "curated" if curated == 1 else "not curated"
            return {
                "success": "false",
                "message": f"Company {company_name} is already {status}",
                "company_name": company_name,
                "curated": str(company.curated)
            }

        # Update company curation status
        # Note: We would need to add an update_company method to the database service
        # For now, we'll return a message indicating this needs to be implemented

        # TODO: Implement update_company method in database service
        logger.warning("Company update functionality not yet implemented in database service")

        return {
            "success": "false",
            "message": f"Company curation update not yet implemented. Please manually update company {company_name}",
            "company_name": company_name,
            "requested_curated": str(curated),
            "current_curated": str(company.curated),
            "todo": "Implement update_company method in database service"
        }

    except Exception as e:
        error_msg = f"Unexpected error updating company {company_name}: {str(e)}"
        logger.error(error_msg)

        return {
            "success": "false",
            "message": error_msg,
            "company_name": company_name,
            "error": str(e)
        }