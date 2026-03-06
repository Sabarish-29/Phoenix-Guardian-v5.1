"""Patient data endpoints with honeytoken detection.

Provides access to patient medical records from the EHR system.
Includes honeytoken detection for security monitoring.
"""

import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from phoenix_guardian.api.dependencies import get_navigator
from phoenix_guardian.agents.navigator_agent import NavigatorAgent
from phoenix_guardian.database import get_db
from phoenix_guardian.models import SecurityIncident
from phoenix_guardian.security import (
    HoneytokenGenerator,
    MRN_RANGE_MIN,
    MRN_RANGE_MAX,
    MRN_HONEYTOKEN_PREFIX,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def is_honeytoken_mrn(mrn: str) -> bool:
    """
    Check if an MRN is a honeytoken.
    
    Honeytokens are identified by:
    - MRN prefix: MRN-9XXXXX (900000-999999 range)
    - HT prefix: HT-xxxxxxxx
    - 999 prefix (legacy)
    
    Args:
        mrn: Medical Record Number to check
        
    Returns:
        True if this is a honeytoken, False otherwise
    """
    if not mrn:
        return False
    
    # Check for HT- prefix
    if mrn.upper().startswith("HT-"):
        return True
    
    # Check for MRN- prefix with 9XXXXX range
    if mrn.upper().startswith(MRN_HONEYTOKEN_PREFIX):
        try:
            mrn_number = int(mrn.replace(MRN_HONEYTOKEN_PREFIX, ""))
            if MRN_RANGE_MIN <= mrn_number <= MRN_RANGE_MAX:
                return True
        except ValueError:
            pass
    
    # Check for 999 prefix (legacy)
    if mrn.startswith("999"):
        return True
    
    # Check for bare number in honeytoken range
    try:
        mrn_number = int(mrn)
        if MRN_RANGE_MIN <= mrn_number <= MRN_RANGE_MAX:
            return True
    except ValueError:
        pass
    
    return False


def log_honeytoken_access(
    mrn: str,
    user_id: Optional[int],
    user_email: Optional[str],
    ip_address: str,
    db: Session,
    action: str = "access",
    user_agent: Optional[str] = None
) -> None:
    """
    Log when someone accesses a honeytoken (SECURITY ALERT!).
    
    Args:
        mrn: The honeytoken MRN that was accessed
        user_id: ID of user who accessed it
        user_email: Email of user
        ip_address: IP address of the access
        db: Database session
        action: Type of action (access, read, update, delete)
        user_agent: Browser user agent
    """
    incident = SecurityIncident.create_honeytoken_incident(
        patient_id=mrn,
        user_id=user_id,
        user_email=user_email,
        ip_address=ip_address,
        action=action,
        user_agent=user_agent
    )
    
    db.add(incident)
    db.commit()
    
    # Log alert (in production, this would send email/Slack/PagerDuty)
    logger.warning(
        f"🚨 SECURITY ALERT: Honeytoken accessed! "
        f"MRN={mrn}, User={user_email or user_id}, IP={ip_address}, Action={action}"
    )


@router.get("")
async def list_patients(
    request: Request,
    db: Session = Depends(get_db),
    # ── OData-compatible query parameters (SAP S/4HANA alignment) ──
    odata_top: Optional[int] = Query(
        default=100,
        alias="$top",
        ge=1,
        le=1000,
        description=(
            "OData: Maximum number of records to return. "
            "Mirrors SAP S/4HANA OData $top system query option."
        ),
    ),
    odata_skip: Optional[int] = Query(
        default=0,
        alias="$skip",
        ge=0,
        description=(
            "OData: Number of records to skip (for pagination). "
            "Mirrors SAP S/4HANA OData $skip system query option."
        ),
    ),
    odata_filter: Optional[str] = Query(
        default=None,
        alias="$filter",
        description=(
            "OData: Filter expression. "
            "Supported format: 'field_name eq \\'value\\''. "
            "Example: 'mrn eq \\'MRN001\\''. "
            "Mirrors SAP S/4HANA OData $filter system query option."
        ),
    ),
    odata_orderby: Optional[str] = Query(
        default=None,
        alias="$orderby",
        description=(
            "OData: Sort expression. "
            "Format: 'field_name' or 'field_name desc'. "
            "Example: 'name desc'. "
            "Mirrors SAP S/4HANA OData $orderby system query option."
        ),
    ),
    odata_expand: Optional[str] = Query(
        default=None,
        alias="$expand",
        description=(
            "OData: Comma-separated related entities to include. "
            "Example: 'encounters,medications'. "
            "Mirrors SAP S/4HANA OData $expand system query option. "
            "(Expansion not yet implemented — accepted for future use.)"
        ),
    ),
) -> Dict[str, Any]:
    """
    List patients with OData-compatible query parameters.

    Returns an OData JSON envelope matching SAP S/4HANA service layer
    response format. Supports $top, $skip, $filter, $orderby, $expand
    system query options as defined in OData v4 specification.

    In demo mode, returns realistic mock patient data. In production,
    this endpoint would query the patient master data table.

    SAP Alignment:
        This endpoint mirrors the format of SAP S/4HANA OData services
        such as API_BUSINESS_PARTNER. The @odata.context and
        @odata.count metadata fields are consumed natively by SAP Fiori
        and SAP Analytics Cloud (SAC) components.

    Args:
        request:       FastAPI request object
        db:            Database session
        odata_top:     Max records to return (OData $top)
        odata_skip:    Records to skip — use with $top for pagination
        odata_filter:  Filter expression e.g. "mrn eq 'MRN001'"
        odata_orderby: Sort expression e.g. "name desc"
        odata_expand:  Related entities to expand (future implementation)

    Returns:
        dict: OData envelope with @odata.context, @odata.count, value[]
    """
    # Demo mode: return mock patient records
    demo_mode = os.getenv("DEMO_MODE", "false").lower() == "true"

    demo_patients: List[Dict[str, Any]] = [
        {"mrn": "MRN001", "name": "John Smith", "dob": "1965-03-15",
         "gender": "M", "status": "active"},
        {"mrn": "MRN002", "name": "Jane Doe", "dob": "1978-07-22",
         "gender": "F", "status": "active"},
        {"mrn": "MRN003", "name": "Robert Johnson", "dob": "1950-11-08",
         "gender": "M", "status": "active"},
        {"mrn": "MRN004", "name": "Maria Garcia", "dob": "1982-01-30",
         "gender": "F", "status": "active"},
        {"mrn": "MRN005", "name": "David Wilson", "dob": "1971-09-12",
         "gender": "M", "status": "inactive"},
    ]

    patients = demo_patients

    # ── Apply OData $filter ─────────────────────────────────────────
    if odata_filter:
        try:
            if " eq '" in odata_filter:
                field_name, _, raw_value = odata_filter.partition(" eq '")
                field_name = field_name.strip()
                field_value = raw_value.rstrip("'").strip()
                patients = [
                    p for p in patients
                    if str(p.get(field_name, "")) == field_value
                ]
        except Exception:
            pass

    # ── Apply OData $orderby ────────────────────────────────────────
    if odata_orderby:
        try:
            parts = odata_orderby.strip().split()
            if parts:
                field_name = parts[0]
                direction = parts[1].lower() if len(parts) > 1 else "asc"
                patients.sort(
                    key=lambda x: x.get(field_name, ""),
                    reverse=(direction == "desc"),
                )
        except Exception:
            pass

    # ── Count BEFORE applying $top/$skip (OData @odata.count) ──────
    odata_total_count = len(patients)

    # ── Apply OData $skip and $top ─────────────────────────────────
    skip = odata_skip if odata_skip is not None else 0
    top = odata_top if odata_top is not None else 100
    patients = patients[skip : skip + top]

    # ── OData response envelope ─────────────────────────────────────
    return {
        "@odata.context": "$metadata#Patients",
        "@odata.count": odata_total_count,
        "value": patients,
    }


@router.get("/{mrn}")
async def get_patient(
    mrn: str,
    request: Request,
    include_fields: Optional[str] = None,
    navigator: NavigatorAgent = Depends(get_navigator),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Fetch patient data by Medical Record Number - with honeytoken detection.

    If a honeytoken is accessed, logs security incident but returns fake data
    to avoid tipping off the attacker.

    Args:
        mrn: Patient Medical Record Number
        request: FastAPI request object
        include_fields: Optional comma-separated list of fields to include
                       (demographics, conditions, medications, allergies,
                        vitals, labs, last_encounter)
        navigator: Navigator agent for patient lookup
        db: Database session

    Returns:
        Complete patient medical history

    Raises:
        HTTPException: If patient not found
    """
    # Get client info
    ip_address = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent")
    
    # Check if this is a honeytoken
    if is_honeytoken_mrn(mrn):
        # Log the security incident
        log_honeytoken_access(
            mrn=mrn,
            user_id=None,  # Would come from auth in production
            user_email=None,
            ip_address=ip_address,
            db=db,
            action="read",
            user_agent=user_agent
        )
        
        # Generate fake but realistic patient data (trap the attacker)
        generator = HoneytokenGenerator()
        fake_patient = generator.generate(attack_type="unauthorized_access")
        
        # Return fake data that looks real
        return {
            "mrn": mrn,
            "demographics": {
                "name": fake_patient.patient_name,
                "mrn": fake_patient.mrn,
                "phone": fake_patient.phone,
                "email": fake_patient.email,
                "address": fake_patient.address,
            },
            "conditions": ["Hypertension", "Type 2 Diabetes"],
            "medications": ["Metformin 500mg", "Lisinopril 10mg"],
            "allergies": ["Penicillin"],
            "honeytoken_triggered": True,  # Internal flag (not shown to user)
        }
    
    # Normal patient lookup
    # Build context
    context: Dict[str, Any] = {"patient_mrn": mrn}

    # Parse include_fields if provided
    if include_fields:
        fields_list: List[str] = [
            f.strip() for f in include_fields.split(",") if f.strip()
        ]
        if fields_list:
            context["include_fields"] = fields_list

    result = await navigator.execute(context)

    if not result.success:
        raise HTTPException(
            status_code=404,
            detail=f"Patient with MRN '{mrn}' not found",
        )

    return result.data
