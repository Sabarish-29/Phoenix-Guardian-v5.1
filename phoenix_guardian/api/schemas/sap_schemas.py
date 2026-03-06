"""Pydantic request / response models for SAP integration endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ── Request models ───────────────────────────────────────────────────────────

class BillingRequest(BaseModel):
    """POST /sap/billing — CodingAgent output → SAP FICO billing document."""
    patient_id: str = Field(..., example="PAT-00123", description="Phoenix-Guardian patient ID")
    encounter_id: str = Field(..., example="ENC-78901", description="Phoenix-Guardian encounter ID")
    icd10_codes: list[str] = Field(default_factory=list, example=["E11.9", "I10"], description="ICD-10 diagnosis codes")
    cpt_codes: list[str] = Field(default_factory=list, example=["99213"], description="CPT procedure codes")
    currency_code: str = Field("USD", example="USD", description="ISO 4217 currency code")
    company_code: str = Field("PG01", example="PG01", description="SAP company code")


class MedicationItem(BaseModel):
    """Single medication line item for procurement."""
    name: str = Field(..., example="Amoxicillin", description="Medication name")
    quantity: int = Field(..., example=21, description="Quantity to order")
    unit: str = Field("TAB", example="TAB", description="Unit of measure")


class LabOrderItem(BaseModel):
    """Single lab-order line item for procurement."""
    code: str = Field(..., example="80053", description="CPT lab code")
    name: str = Field("", example="Comprehensive Metabolic Panel", description="Lab test name")
    quantity: int = Field(1, example=1, description="Quantity")


class ProcurementRequest(BaseModel):
    """POST /sap/procurement — OrdersAgent output → SAP MM purchase requisition."""
    patient_id: str = Field(..., example="PAT-00123", description="Patient ID")
    encounter_id: str = Field(..., example="ENC-78901", description="Encounter ID")
    medications: list[MedicationItem] = Field(default_factory=list, description="Medications to order")
    lab_orders: list[LabOrderItem] = Field(default_factory=list, description="Lab orders to create")


class GRCAlertRequest(BaseModel):
    """POST /sap/compliance-alert — FraudAgent output → SAP GRC issue."""
    patient_id: str = Field(..., example="PAT-00123", description="Patient ID")
    encounter_id: str = Field(..., example="ENC-78901", description="Encounter ID")
    risk_level: str = Field("MEDIUM", example="HIGH", description="Risk level: LOW | MEDIUM | HIGH | CRITICAL")
    findings: str = Field("", example="Upcoding pattern detected", description="Description of findings")


class AnalyticsRequest(BaseModel):
    """POST /sap/analytics — PopulationHealthAgent output → SAP SAC KPI data."""
    patient_count_30d: int = Field(0, example=142, description="Patient encounters in last 30 days")
    readmission_rate: float = Field(0.0, example=0.069, description="30-day readmission rate")
    icu_occupancy_pct: float = Field(0.0, example=74.5, description="ICU occupancy percentage")


# ── Response models ──────────────────────────────────────────────────────────

class SAPODataResponse(BaseModel):
    """OData V4 JSON envelope returned by all SAP endpoints."""
    odata_context: str = Field(..., alias="@odata.context", description="OData context URI")
    value: dict[str, Any] = Field(..., description="OData value payload")

    model_config = {"populate_by_name": True}


class SAPModuleStatusResponse(BaseModel):
    """Single module status entry in GET /sap/status response."""
    module: str
    status: str
    latency_ms: int = 0
    message: str = ""
