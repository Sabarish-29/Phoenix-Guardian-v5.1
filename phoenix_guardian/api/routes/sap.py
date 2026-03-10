"""SAP integration API routes.

Five endpoints that expose the SAPIntegrationService to authenticated users.
Each returns an OData V4 JSON envelope.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from phoenix_guardian.api.auth.utils import get_current_active_user
from phoenix_guardian.api.schemas.sap_schemas import (
    BillingRequest,
    ProcurementRequest,
    GRCAlertRequest,
    AnalyticsRequest,
)
from phoenix_guardian.models.user import User
from phoenix_guardian.services.sap_integration_service import sap_service

logger = logging.getLogger("phoenix_guardian.api.routes.sap")

router = APIRouter(prefix="/sap", tags=["SAP Integration"])


# ── 1. POST /sap/billing ────────────────────────────────────────────────────

@router.post(
    "/billing",
    summary="Post billing document to SAP FICO",
    description="Transforms CodingAgent ICD-10/CPT output into an SAP S/4HANA billing document (DR type).",
    response_description="OData V4 envelope with DocumentNumber",
)
async def post_billing(
    body: BillingRequest,
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    """CodingAgent → SAP FICO billing document."""
    logger.info("SAP billing  user=%s patient=%s encounter=%s", current_user.email, body.patient_id, body.encounter_id)
    result = await sap_service.post_billing_to_fico(body.dict())
    if not result.success:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=result.message or "SAP billing failed")
    return result.to_odata_dict()


# ── 2. POST /sap/procurement ────────────────────────────────────────────────

@router.post(
    "/procurement",
    summary="Create purchase requisition in SAP MM",
    description="Transforms OrdersAgent medication/lab output into an SAP MM purchase requisition (NB type).",
    response_description="OData V4 envelope with DocumentNumber",
)
async def post_procurement(
    body: ProcurementRequest,
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    """OrdersAgent → SAP MM purchase requisition."""
    logger.info("SAP procurement  user=%s patient=%s", current_user.email, body.patient_id)
    payload = body.dict()
    # Convert Pydantic sub-models to plain dicts for the service
    payload["medications"] = [m.dict() if hasattr(m, "dict") else m for m in body.medications]
    payload["lab_orders"] = [lo.dict() if hasattr(lo, "dict") else lo for lo in body.lab_orders]
    result = await sap_service.create_purchase_requisition(payload)
    if not result.success:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=result.message or "SAP procurement failed")
    return result.to_odata_dict()


# ── 3. POST /sap/compliance-alert ───────────────────────────────────────────

@router.post(
    "/compliance-alert",
    summary="Raise GRC compliance alert in SAP",
    description="Transforms FraudDetectionAgent findings into an SAP GRC issue for audit trail.",
    response_description="OData V4 envelope with DocumentNumber",
)
async def post_compliance_alert(
    body: GRCAlertRequest,
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    """FraudDetectionAgent → SAP GRC compliance issue."""
    logger.info("SAP GRC alert  user=%s risk=%s", current_user.email, body.risk_level)
    result = await sap_service.raise_grc_alert(body.dict())
    if not result.success:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=result.message or "SAP GRC alert failed")
    return result.to_odata_dict()


# ── 4. POST /sap/analytics ──────────────────────────────────────────────────

@router.post(
    "/analytics",
    summary="Push analytics to SAP Analytics Cloud",
    description="Pushes PopulationHealthAgent KPI data points to SAP SAC for dashboard consumption.",
    response_description="OData V4 envelope with DocumentNumber",
)
async def post_analytics(
    body: AnalyticsRequest,
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    """PopulationHealthAgent → SAP Analytics Cloud KPI data."""
    logger.info("SAP analytics  user=%s", current_user.email)
    result = await sap_service.push_analytics_to_sac(body.dict())
    if not result.success:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=result.message or "SAP analytics push failed")
    return result.to_odata_dict()


# ── 5. GET /sap/status ──────────────────────────────────────────────────────

@router.get(
    "/status",
    summary="SAP module connectivity status",
    description="Returns connection status for all four SAP modules (FICO, MM, GRC, SAC). Public endpoint — no authentication required.",
    response_description="OData V4 envelope with module statuses",
)
async def get_status() -> dict[str, Any]:
    """Return health/connectivity status for each SAP module (public)."""
    logger.info("SAP status check (public)")
    statuses = await sap_service.get_module_status()
    return {
        "@odata.context": "$metadata#SAPModuleStatus",
        "value": [
            {
                "module": s.module.value,
                "status": s.status.value,
                "latency_ms": s.latency_ms,
                "message": s.message,
            }
            for s in statuses
        ],
        "total": len(statuses),
    }
