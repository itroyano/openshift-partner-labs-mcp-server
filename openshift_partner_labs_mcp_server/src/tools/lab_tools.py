"""Lab management MCP tools for OpenShift Partner Labs."""

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from openshift_partner_labs_mcp_server.src.acm.client import acm_client
from openshift_partner_labs_mcp_server.src.acm.models import (
    ACMCreateClusterRequest,
    ACMDeleteClusterRequest,
    ACMHibernateClusterRequest,
    ACMResumeClusterRequest,
)
from openshift_partner_labs_mcp_server.src.database.models import (
    CompanyCreateRequest,
    LabCreateRequest,
    LabState,
    LabUpdateRequest,
    RequestType,
    CloudProvider,
    Region,
    ClusterSize,
)
from openshift_partner_labs_mcp_server.src.database.service import db_service
from openshift_partner_labs_mcp_server.utils.pylogger import get_python_logger

logger = get_python_logger()


async def create_lab(
    generated_name: str,
    cluster_name: str,
    openshift_version: str,
    cluster_size: str,
    request_type: str,
    cloud_provider: str,
    primary_first: str,
    primary_last: str,
    primary_email: str,
    secondary_first: str,
    secondary_last: str,
    secondary_email: str,
    region: str,
    project_name: str,
    lease_time: str,
    description: str,
    notes: str,
    start_date: str,
    end_date: str,
    sponsor: Optional[str] = None,
    company_name: Optional[str] = None,
    partner: int = 0,
    always_on: int = 0,
    hold: int = 0,
) -> Dict[str, str]:
    """Create a new OpenShift Partner Lab.

    Args:
        generated_name: Auto-generated friendly name (max 32 chars)
        cluster_name: Actual cluster name (max 32 chars)
        openshift_version: OpenShift version (e.g., "4.20.0")
        cluster_size: Size of cluster (small, medium, large, xlarge, custom)
        request_type: Type of request (general, engineering, rosa, rhoai, nvidia, ocpv)
        cloud_provider: Cloud provider (AWS, Azure, Google, IBM, Oracle, Alibaba, Linode, Vultr, DigitalO)
        primary_first: Primary contact first name
        primary_last: Primary contact last name
        primary_email: Primary contact email
        secondary_first: Secondary contact first name
        secondary_last: Secondary contact last name
        secondary_email: Secondary contact email
        region: Deployment region (na1, na2, emea, apac1, apac2, latam)
        project_name: Project identifier
        lease_time: Lease duration (1d, 1w, 1m, 2w, 2d)
        description: Lab description
        notes: Additional notes
        start_date: Lab start date (YYYY-MM-DD HH:MM:SS)
        end_date: Lab end date (YYYY-MM-DD HH:MM:SS)
        sponsor: Sponsor email (defaults to primary_email)
        company_name: Company name (optional)
        partner: Is this a partner lab (0=no, 1=yes)
        always_on: Keep cluster always running (0=no, 1=yes)
        hold: Put lab on hold (0=no, 1=yes)

    Returns:
        Dictionary with operation result and lab information
    """
    try:
        logger.info(f"Creating lab {generated_name}")

        # Initialize services if needed
        if not acm_client._custom_objects_api:
            await acm_client.initialize()

        # Parse dates
        try:
            start_datetime = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            end_datetime = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except ValueError:
            return {
                "success": "false",
                "message": "Invalid date format. Use YYYY-MM-DD HH:MM:SS format",
                "generated_name": generated_name
            }

        # Validate inputs
        if cluster_size not in [ClusterSize.SMALL, ClusterSize.MEDIUM, ClusterSize.LARGE, ClusterSize.XLARGE, ClusterSize.CUSTOM]:
            return {
                "success": "false",
                "message": f"Invalid cluster_size. Must be one of: {ClusterSize.SMALL}, {ClusterSize.MEDIUM}, {ClusterSize.LARGE}, {ClusterSize.XLARGE}, {ClusterSize.CUSTOM}",
                "generated_name": generated_name
            }

        # Check if lab name already exists
        existing_lab = await db_service.get_lab_by_name(generated_name)
        if existing_lab:
            return {
                "success": "false",
                "message": f"Lab with name {generated_name} already exists",
                "generated_name": generated_name
            }

        # Handle company
        company_id = None
        if company_name:
            company = await db_service.get_company_by_name(company_name)
            if not company:
                # Create new company
                company_request = CompanyCreateRequest(
                    company_name=company_name,
                    curated=0
                )
                company = await db_service.create_company(company_request)
            company_id = company.id

        # Create lab record in database
        lab_request = LabCreateRequest(
            generated_name=generated_name,
            cluster_name=cluster_name,
            openshift_version=openshift_version,
            cluster_size=cluster_size,
            company_id=company_id,
            request_type=request_type,
            partner=partner,
            sponsor=sponsor or primary_email,
            cloud_provider=cloud_provider,
            primary_first=primary_first,
            primary_last=primary_last,
            primary_email=primary_email,
            secondary_first=secondary_first,
            secondary_last=secondary_last,
            secondary_email=secondary_email,
            region=region,
            always_on=always_on,
            project_name=project_name,
            lease_time=lease_time,
            description=description,
            notes=notes,
            start_date=start_datetime,
            end_date=end_datetime,
            hold=hold
        )

        lab = await db_service.create_lab(lab_request)

        logger.info(f"Successfully created lab {generated_name}")

        return {
            "success": "true",
            "message": f"Lab {generated_name} created successfully",
            "lab_id": str(lab.id),
            "cluster_id": lab.cluster_id,
            "generated_name": generated_name,
            "cluster_name": cluster_name,
            "state": lab.state,
            "request_type": request_type,
            "cloud_provider": cloud_provider,
            "region": region,
            "openshift_version": openshift_version,
            "cluster_size": cluster_size,
            "sponsor": lab.sponsor,
            "company_name": company_name or "",
            "created_at": lab.created_at.isoformat() if lab.created_at else ""
        }

    except Exception as e:
        error_msg = f"Unexpected error creating lab {generated_name}: {str(e)}"
        logger.error(error_msg)

        return {
            "success": "false",
            "message": error_msg,
            "generated_name": generated_name,
            "error": str(e)
        }


async def approve_lab(generated_name: str) -> Dict[str, str]:
    """Approve a lab and initiate cluster creation via ACM.

    Args:
        generated_name: Name of the lab to approve

    Returns:
        Dictionary with operation result
    """
    try:
        logger.info(f"Approving lab {generated_name}")

        # Initialize services if needed
        if not acm_client._custom_objects_api:
            await acm_client.initialize()

        # Get lab from database
        lab = await db_service.get_lab_by_name(generated_name)
        if not lab:
            return {
                "success": "false",
                "message": f"Lab {generated_name} not found",
                "generated_name": generated_name
            }

        if lab.state != LabState.PENDING:
            return {
                "success": "false",
                "message": f"Lab {generated_name} is not in pending state (current: {lab.state})",
                "generated_name": generated_name
            }

        # Update lab status to approved
        await db_service.update_lab(
            lab.id,
            LabUpdateRequest(state=LabState.APPROVED)
        )

        # Create cluster via ACM
        acm_request = ACMCreateClusterRequest(
            cluster_name=lab.cluster_name,
            namespace="default",  # Could be made configurable
            base_domain=f"{lab.region}.example.com",  # Should be configurable
            cloud_provider=lab.cloud_provider.lower(),
            region=lab.region,
            worker_nodes=3,  # Could be based on cluster_size
            hibernation_enabled=True,
            labels={
                "lab_id": str(lab.id),
                "generated_name": lab.generated_name,
                "request_type": lab.request_type,
                "partner": str(lab.partner).lower()
            }
        )

        acm_response = await acm_client.create_cluster(acm_request)

        if acm_response.success:
            # Update lab status to active
            await db_service.update_lab(
                lab.id,
                LabUpdateRequest(state=LabState.ACTIVE)
            )

            # Create approval event (with error handling for missing table)
            await db_service.create_lab_event(
                lab.id,
                "approved",
                f"Lab {generated_name} approved and cluster creation initiated",
                {"acm_response": acm_response.details}
            )

            logger.info(f"Successfully approved lab {generated_name}")

            return {
                "success": "true",
                "message": f"Lab {generated_name} approved and cluster creation initiated",
                "lab_id": str(lab.id),
                "generated_name": generated_name,
                "cluster_name": lab.cluster_name,
                "state": "active",
                "acm_details": str(acm_response.details)
            }
        else:
            # Update lab status back to pending with error
            await db_service.update_lab(
                lab.id,
                LabUpdateRequest(state=LabState.PENDING)
            )

            # Create error event (with error handling for missing table)
            await db_service.create_lab_event(
                lab.id,
                "error_occurred",
                f"Failed to create cluster for lab {generated_name}: {acm_response.message}",
                {"acm_error": acm_response.details}
            )

            return {
                "success": "false",
                "message": f"Failed to create cluster for lab {generated_name}: {acm_response.message}",
                "lab_id": str(lab.id),
                "generated_name": generated_name,
                "error_details": str(acm_response.details)
            }

    except Exception as e:
        error_msg = f"Unexpected error approving lab {generated_name}: {str(e)}"
        logger.error(error_msg)

        return {
            "success": "false",
            "message": error_msg,
            "generated_name": generated_name,
            "error": str(e)
        }


async def deny_lab(generated_name: str, reason: str = "Not approved") -> Dict[str, str]:
    """Deny a lab request.

    Args:
        generated_name: Name of the lab to deny
        reason: Reason for denial

    Returns:
        Dictionary with operation result
    """
    try:
        logger.info(f"Denying lab {generated_name}")

        # Get lab from database
        lab = await db_service.get_lab_by_name(generated_name)
        if not lab:
            return {
                "success": "false",
                "message": f"Lab {generated_name} not found",
                "generated_name": generated_name
            }

        if lab.state not in [LabState.PENDING, LabState.APPROVED]:
            return {
                "success": "false",
                "message": f"Lab {generated_name} cannot be denied in current state: {lab.state}",
                "generated_name": generated_name
            }

        # Update lab status to denied
        await db_service.update_lab(
            lab.id,
            LabUpdateRequest(
                state=LabState.DENIED,
                notes=f"{lab.notes}\n\nDenial reason: {reason}" if lab.notes else f"Denial reason: {reason}"
            )
        )

        # Create denial event (with error handling for missing table)
        await db_service.create_lab_event(
            lab.id,
            "denied",
            f"Lab {generated_name} denied: {reason}"
        )

        logger.info(f"Successfully denied lab {generated_name}")

        return {
            "success": "true",
            "message": f"Lab {generated_name} denied successfully",
            "lab_id": str(lab.id),
            "generated_name": generated_name,
            "state": "denied",
            "reason": reason
        }

    except Exception as e:
        error_msg = f"Unexpected error denying lab {generated_name}: {str(e)}"
        logger.error(error_msg)

        return {
            "success": "false",
            "message": error_msg,
            "generated_name": generated_name,
            "error": str(e)
        }


async def complete_lab(generated_name: str) -> Dict[str, str]:
    """Mark a lab as completed and clean up resources.

    Args:
        generated_name: Name of the lab to complete

    Returns:
        Dictionary with operation result
    """
    try:
        logger.info(f"Completing lab {generated_name}")

        # Initialize services if needed
        if not acm_client._custom_objects_api:
            await acm_client.initialize()

        # Get lab from database
        lab = await db_service.get_lab_by_name(generated_name)
        if not lab:
            return {
                "success": "false",
                "message": f"Lab {generated_name} not found",
                "generated_name": generated_name
            }

        if lab.state not in [LabState.ACTIVE, LabState.EXTENDED]:
            return {
                "success": "false",
                "message": f"Lab {generated_name} cannot be completed in current state: {lab.state}",
                "generated_name": generated_name
            }

        # Delete cluster via ACM
        acm_request = ACMDeleteClusterRequest(
            cluster_name=lab.cluster_name,
            namespace="default",
            force=False
        )

        acm_response = await acm_client.delete_cluster(acm_request)

        if acm_response.success:
            # Update lab status to completed
            await db_service.update_lab(
                lab.id,
                LabUpdateRequest(state=LabState.COMPLETED)
            )

            # Create completion event (with error handling for missing table)
            await db_service.create_lab_event(
                lab.id,
                "completed",
                f"Lab {generated_name} completed and cluster deletion initiated",
                {"acm_response": acm_response.details}
            )

            logger.info(f"Successfully completed lab {generated_name}")

            return {
                "success": "true",
                "message": f"Lab {generated_name} completed and cluster deletion initiated",
                "lab_id": str(lab.id),
                "generated_name": generated_name,
                "state": "completed"
            }
        else:
            # Create error event but still mark as completed (with error handling for missing table)
            await db_service.create_lab_event(
                lab.id,
                "error_occurred",
                f"Failed to delete cluster for lab {generated_name}: {acm_response.message}",
                {"acm_error": acm_response.details}
            )

            await db_service.update_lab(
                lab.id,
                LabUpdateRequest(state=LabState.COMPLETED)
            )

            return {
                "success": "true",
                "message": f"Lab {generated_name} marked as completed but cluster deletion failed: {acm_response.message}",
                "lab_id": str(lab.id),
                "generated_name": generated_name,
                "state": "completed",
                "warning": "Cluster deletion failed",
                "error_details": str(acm_response.details)
            }

    except Exception as e:
        error_msg = f"Unexpected error completing lab {generated_name}: {str(e)}"
        logger.error(error_msg)

        return {
            "success": "false",
            "message": error_msg,
            "generated_name": generated_name,
            "error": str(e)
        }


async def extend_lab(generated_name: str, new_end_date: str) -> Dict[str, str]:
    """Extend a lab's duration.

    Args:
        generated_name: Name of the lab to extend
        new_end_date: New end date (YYYY-MM-DD HH:MM:SS)

    Returns:
        Dictionary with operation result
    """
    try:
        logger.info(f"Extending lab {generated_name}")

        # Get lab from database
        lab = await db_service.get_lab_by_name(generated_name)
        if not lab:
            return {
                "success": "false",
                "message": f"Lab {generated_name} not found",
                "generated_name": generated_name
            }

        if lab.state not in [LabState.ACTIVE, LabState.EXTENDED]:
            return {
                "success": "false",
                "message": f"Lab {generated_name} cannot be extended in current state: {lab.state}",
                "generated_name": generated_name
            }

        # Parse new end date
        try:
            new_end_datetime = datetime.fromisoformat(new_end_date.replace('Z', '+00:00'))
        except ValueError:
            return {
                "success": "false",
                "message": "Invalid date format. Use YYYY-MM-DD HH:MM:SS format",
                "generated_name": generated_name
            }

        if new_end_datetime <= lab.end_date:
            return {
                "success": "false",
                "message": f"New end date must be after current end date ({lab.end_date})",
                "generated_name": generated_name
            }

        # Update lab
        original_end_date = lab.end_date
        await db_service.update_lab(
            lab.id,
            LabUpdateRequest(
                state=LabState.EXTENDED,
                end_date=new_end_datetime
            )
        )

        # Create extension event (with error handling for missing table)
        await db_service.create_lab_event(
            lab.id,
            "extended",
            f"Lab {generated_name} extended from {original_end_date} to {new_end_datetime}",
            {
                "original_end_date": original_end_date.isoformat(),
                "new_end_date": new_end_datetime.isoformat()
            }
        )

        logger.info(f"Successfully extended lab {generated_name}")

        return {
            "success": "true",
            "message": f"Lab {generated_name} extended successfully",
            "lab_id": str(lab.id),
            "generated_name": generated_name,
            "state": "extended",
            "original_end_date": original_end_date.isoformat(),
            "new_end_date": new_end_datetime.isoformat()
        }

    except Exception as e:
        error_msg = f"Unexpected error extending lab {generated_name}: {str(e)}"
        logger.error(error_msg)

        return {
            "success": "false",
            "message": error_msg,
            "generated_name": generated_name,
            "error": str(e)
        }


async def get_lab_status(generated_name: str) -> Dict[str, str]:
    """Get detailed status information for a lab.

    Args:
        generated_name: Name of the lab

    Returns:
        Dictionary with lab status information
    """
    try:
        logger.info(f"Getting status for lab {generated_name}")

        # Get lab from database
        lab = await db_service.get_lab_by_name(generated_name)
        if not lab:
            return {
                "success": "false",
                "message": f"Lab {generated_name} not found",
                "generated_name": generated_name
            }

        # Get company info if available
        company_name = ""
        if lab.company_id:
            company = await db_service.get_company_by_id(lab.company_id)
            if company:
                company_name = company.company_name

        return {
            "success": "true",
            "message": f"Lab {generated_name} status retrieved",
            "lab_id": str(lab.id),
            "cluster_id": lab.cluster_id,
            "generated_name": lab.generated_name,
            "cluster_name": lab.cluster_name,
            "state": lab.state,
            "openshift_version": lab.openshift_version,
            "cluster_size": lab.cluster_size,
            "request_type": lab.request_type,
            "partner": str(lab.partner),
            "sponsor": lab.sponsor,
            "cloud_provider": lab.cloud_provider,
            "region": lab.region,
            "always_on": str(lab.always_on),
            "project_name": lab.project_name,
            "lease_time": lab.lease_time,
            "description": lab.description,
            "notes": lab.notes,
            "primary_contact": f"{lab.primary_first} {lab.primary_last} <{lab.primary_email}>",
            "secondary_contact": f"{lab.secondary_first} {lab.secondary_last} <{lab.secondary_email}>",
            "company_name": company_name,
            "start_date": lab.start_date.isoformat(),
            "end_date": lab.end_date.isoformat(),
            "hold": str(lab.hold),
            "created_at": lab.created_at.isoformat() if lab.created_at else "",
            "updated_at": lab.updated_at.isoformat() if lab.updated_at else ""
        }

    except Exception as e:
        error_msg = f"Unexpected error getting status for lab {generated_name}: {str(e)}"
        logger.error(error_msg)

        return {
            "success": "false",
            "message": error_msg,
            "generated_name": generated_name,
            "error": str(e)
        }


async def list_labs(
    state: Optional[str] = None,
    request_type: Optional[str] = None,
    cloud_provider: Optional[str] = None,
    region: Optional[str] = None,
    partner_only: bool = False,
    company_name: Optional[str] = None,
    page: int = 1,
    page_size: int = 20
) -> Dict[str, str]:
    """List labs with optional filtering.

    Args:
        state: Filter by state (pending, approved, active, extended, completed, denied)
        request_type: Filter by request type (general, engineering, rosa, rhoai, nvidia, ocpv)
        cloud_provider: Filter by cloud provider
        region: Filter by region (na1, na2, emea, apac1, apac2, latam)
        partner_only: Show only partner labs
        company_name: Filter by company name
        page: Page number (1-based)
        page_size: Number of labs per page

    Returns:
        Dictionary with list of labs
    """
    try:
        logger.info(f"Listing labs with filters: state={state}, request_type={request_type}")

        # Get company ID if company name provided
        company_id = None
        if company_name:
            company = await db_service.get_company_by_name(company_name)
            if not company:
                return {
                    "success": "false",
                    "message": f"Company {company_name} not found",
                    "company_name": company_name
                }
            company_id = company.id

        # List labs
        labs, total_count = await db_service.list_labs(
            state=state,
            request_type=request_type,
            cloud_provider=cloud_provider,
            region=region,
            partner_only=partner_only,
            company_id=company_id,
            page=page,
            page_size=page_size
        )

        lab_list = []
        for lab in labs:
            # Get company name if available
            lab_company_name = ""
            if lab.company_id:
                company = await db_service.get_company_by_id(lab.company_id)
                if company:
                    lab_company_name = company.company_name

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
                "company_name": lab_company_name,
                "start_date": lab.start_date.isoformat(),
                "end_date": lab.end_date.isoformat(),
                "created_at": lab.created_at.isoformat() if lab.created_at else ""
            }
            lab_list.append(lab_info)

        total_pages = (total_count + page_size - 1) // page_size

        filters_applied = []
        if state:
            filters_applied.append(f"state={state}")
        if request_type:
            filters_applied.append(f"request_type={request_type}")
        if cloud_provider:
            filters_applied.append(f"cloud_provider={cloud_provider}")
        if region:
            filters_applied.append(f"region={region}")
        if partner_only:
            filters_applied.append("partner_only=true")
        if company_name:
            filters_applied.append(f"company={company_name}")

        return {
            "success": "true",
            "message": f"Found {total_count} labs matching filters: {', '.join(filters_applied) if filters_applied else 'none'}",
            "total_labs": str(total_count),
            "page": str(page),
            "page_size": str(page_size),
            "total_pages": str(total_pages),
            "filters": ", ".join(filters_applied) if filters_applied else "none",
            "labs": str(lab_list)  # Convert to string for MCP tool return
        }

    except Exception as e:
        error_msg = f"Unexpected error listing labs: {str(e)}"
        logger.error(error_msg)

        return {
            "success": "false",
            "message": error_msg,
            "page": str(page),
            "page_size": str(page_size),
            "error": str(e)
        }