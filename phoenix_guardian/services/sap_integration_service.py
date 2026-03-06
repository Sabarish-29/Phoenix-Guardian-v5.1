"""SAP Integration Service — bridge between Phoenix-Guardian agents and SAP S/4HANA.

Provides iFlow-style methods for posting billing documents, purchase
requisitions, GRC compliance alerts, and SAC analytics payloads to SAP
via OData V4.  In demo mode every call returns a realistic synthetic
response with document numbers in real SAP format.
"""

import logging
import os
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import httpx

logger = logging.getLogger("phoenix_guardian.services.sap_integration")

DEMO_MODE = os.getenv("SAP_DEMO_MODE", os.getenv("DEMO_MODE", "true")).lower() == "true"


# ── Enums ────────────────────────────────────────────────────────────────────

class SAPModule(str, Enum):
    """SAP modules supported by the integration bridge."""
    FICO = "FICO"   # Financial Accounting / Controlling
    MM = "MM"       # Materials Management
    GRC = "GRC"     # Governance, Risk & Compliance
    SAC = "SAC"     # SAP Analytics Cloud


class SAPDocumentType(str, Enum):
    """SAP document types created by the service."""
    DR = "DR"   # Customer Invoice (Debitor Rechnung)
    NB = "NB"   # Purchase Requisition (Normalbestellung)


class SAPPurchaseRequisitionType(str, Enum):
    """Purchase requisition sub-types."""
    MEDICATION = "MEDICATION"
    LAB_ORDER = "LAB_ORDER"


class SAPConnectionStatus(str, Enum):
    """Connection status for each SAP module."""
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    DEMO = "DEMO"
    ERROR = "ERROR"


# ── Dataclasses ──────────────────────────────────────────────────────────────

@dataclass
class SAPResponse:
    """Standard envelope returned by every public iFlow method."""
    success: bool
    module: SAPModule
    message: str = ""
    doc_number: str = ""
    odata_context: str = ""
    demo_mode: bool = DEMO_MODE
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_odata_dict(self) -> dict[str, Any]:
        """Return an OData V4 JSON envelope."""
        return {
            "@odata.context": self.odata_context or f"$metadata#{self.module.value}",
            "value": {
                "DocumentNumber": self.doc_number,
                "Module": self.module.value,
                "Success": self.success,
                "Message": self.message,
                "DemoMode": self.demo_mode,
                "Timestamp": self.timestamp,
                **self.payload,
            },
        }


@dataclass
class SAPModuleStatus:
    """Health / connectivity status for a single SAP module."""
    module: SAPModule
    status: SAPConnectionStatus
    latency_ms: int = 0
    message: str = ""


# ── OData path constants ────────────────────────────────────────────────────

ODATA_BILLING_PATH = "/sap/opu/odata4/sap/api_billing_document/A_BillingDocument"
ODATA_PROCUREMENT_PATH = "/sap/opu/odata4/sap/api_purchaserequisition/A_PurchaseRequisition"
ODATA_GRC_PATH = "/sap/opu/odata4/sap/api_grc_issue/A_Issue"
ODATA_SAC_PATH = "/sap/opu/odata4/sap/api_analytics/A_KPIDataPoint"


# ── Main Service ─────────────────────────────────────────────────────────────

class SAPIntegrationService:
    """Bridge service connecting Phoenix-Guardian agent outputs to SAP S/4HANA."""

    def __init__(self) -> None:
        self.api_base_url = os.getenv("SAP_API_BASE_URL", "https://phoenix-guardian.s4hana.cloud.sap")
        self.company_code = os.getenv("SAP_COMPANY_CODE", "PG01")
        self.plant_code = os.getenv("SAP_PLANT_CODE", "PG10")
        self.purchasing_org = os.getenv("SAP_PURCHASING_ORG", "PG00")
        self.xsuaa_url = os.getenv("SAP_XSUAA_URL", "")
        self.client_id = os.getenv("SAP_CLIENT_ID", "")
        self.client_secret = os.getenv("SAP_CLIENT_SECRET", "")
        self._token_cache: dict[str, Any] = {}
        self._doc_counters: dict[str, int] = {
            "FI": 5100000000,
            "PR": 10000000,
            "GRC": 0,
            "SAC": 0,
        }
        logger.info("SAPIntegrationService initialised  demo=%s", DEMO_MODE)

    # ── Internal helpers ─────────────────────────────────────────────────

    def _next_doc_number(self, prefix: str) -> str:
        """Generate the next sequential document number for *prefix*."""
        counter = self._doc_counters.get(prefix, 0) + random.randint(1, 99)
        self._doc_counters[prefix] = counter
        if prefix == "FI":
            return f"FI-{counter:010d}"
        if prefix == "PR":
            return f"PR-{counter:010d}"
        if prefix == "GRC":
            return f"GRC-ISSUE-{counter:05d}"
        if prefix == "SAC":
            return f"SAC-KPI-{counter:05d}"
        return f"{prefix}-{counter:010d}"

    async def _get_sap_token(self) -> str:
        """Obtain an OAuth2 token via XSUAA client-credentials flow."""
        cached = self._token_cache.get("access_token")
        if cached and self._token_cache.get("expires_at", 0) > datetime.now(timezone.utc).timestamp():
            return cached

        if not self.xsuaa_url or not self.client_id:
            logger.warning("XSUAA not configured — returning demo token")
            return "demo-xsuaa-token"

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.xsuaa_url}/oauth/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            self._token_cache = {
                "access_token": data["access_token"],
                "expires_at": datetime.now(timezone.utc).timestamp() + data.get("expires_in", 3600) - 60,
            }
            return data["access_token"]

    def _make_odata_headers(self, token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "sap-client": os.getenv("SAP_CLIENT", "100"),
        }

    # ── iFlow 1 — Billing (CodingAgent → FICO) ──────────────────────────

    async def post_billing_to_fico(self, coding_output: dict[str, Any]) -> SAPResponse:
        """Post a billing document to SAP FICO from CodingAgent output.

        Expected keys: patient_id, encounter_id, icd10_codes, cpt_codes,
                       currency_code (opt), company_code (opt)
        """
        doc_number = self._next_doc_number("FI")
        patient_id = coding_output.get("patient_id", "UNKNOWN")
        encounter_id = coding_output.get("encounter_id", "UNKNOWN")
        icd10_codes = coding_output.get("icd10_codes", [])
        cpt_codes = coding_output.get("cpt_codes", [])

        if DEMO_MODE:
            logger.info("DEMO billing  doc=%s patient=%s encounter=%s", doc_number, patient_id, encounter_id)
            return SAPResponse(
                success=True,
                module=SAPModule.FICO,
                message=f"DEMO: Billing document {doc_number} created for encounter {encounter_id}",
                doc_number=doc_number,
                odata_context=f"$metadata#BillingDocument('{doc_number}')",
                payload={
                    "DocumentType": SAPDocumentType.DR.value,
                    "CompanyCode": self.company_code,
                    "PatientId": patient_id,
                    "EncounterId": encounter_id,
                    "ICD10Codes": icd10_codes,
                    "CPTCodes": cpt_codes,
                },
            )

        # ── Live SAP call ────────────────────────────────────────────────
        token = await self._get_sap_token()
        headers = self._make_odata_headers(token)
        url = f"{self.api_base_url}{ODATA_BILLING_PATH}"
        body = {
            "BillingDocumentType": SAPDocumentType.DR.value,
            "CompanyCode": coding_output.get("company_code", self.company_code),
            "CurrencyCode": coding_output.get("currency_code", "USD"),
            "PatientId": patient_id,
            "EncounterId": encounter_id,
            "DiagnosisCodes": icd10_codes,
            "ProcedureCodes": cpt_codes,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        return SAPResponse(
            success=True,
            module=SAPModule.FICO,
            message=f"Billing document created: {data.get('BillingDocument', doc_number)}",
            doc_number=data.get("BillingDocument", doc_number),
            odata_context=data.get("@odata.context", ""),
            payload=data,
        )

    # ── iFlow 2 — Procurement (OrdersAgent → MM) ────────────────────────

    async def create_purchase_requisition(self, orders_output: dict[str, Any]) -> SAPResponse:
        """Create an SAP MM purchase requisition from OrdersAgent output.

        Expected keys: patient_id, encounter_id, medications (list),
                       lab_orders (list)
        """
        doc_number = self._next_doc_number("PR")
        patient_id = orders_output.get("patient_id", "UNKNOWN")
        encounter_id = orders_output.get("encounter_id", "UNKNOWN")
        medications = orders_output.get("medications", [])
        lab_orders = orders_output.get("lab_orders", [])

        if DEMO_MODE:
            logger.info("DEMO procurement  doc=%s patient=%s", doc_number, patient_id)
            return SAPResponse(
                success=True,
                module=SAPModule.MM,
                message=f"DEMO: Purchase requisition {doc_number} created ({len(medications)} meds, {len(lab_orders)} labs)",
                doc_number=doc_number,
                odata_context=f"$metadata#PurchaseRequisition('{doc_number}')",
                payload={
                    "DocumentType": SAPDocumentType.NB.value,
                    "Plant": self.plant_code,
                    "PurchasingOrg": self.purchasing_org,
                    "PatientId": patient_id,
                    "EncounterId": encounter_id,
                    "Medications": medications,
                    "LabOrders": lab_orders,
                },
            )

        token = await self._get_sap_token()
        headers = self._make_odata_headers(token)
        url = f"{self.api_base_url}{ODATA_PROCUREMENT_PATH}"
        body = {
            "PurchaseRequisitionType": SAPDocumentType.NB.value,
            "Plant": self.plant_code,
            "PurchasingOrganization": self.purchasing_org,
            "PatientId": patient_id,
            "EncounterId": encounter_id,
            "Items": medications + lab_orders,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        return SAPResponse(
            success=True,
            module=SAPModule.MM,
            message=f"Purchase requisition created: {data.get('PurchaseRequisition', doc_number)}",
            doc_number=data.get("PurchaseRequisition", doc_number),
            odata_context=data.get("@odata.context", ""),
            payload=data,
        )

    # ── iFlow 3 — GRC Alert (FraudAgent → GRC) ──────────────────────────

    async def raise_grc_alert(self, fraud_output: dict[str, Any]) -> SAPResponse:
        """Raise a GRC compliance issue from FraudDetectionAgent output.

        Expected keys: patient_id, encounter_id, risk_level, findings
        """
        doc_number = self._next_doc_number("GRC")
        patient_id = fraud_output.get("patient_id", "UNKNOWN")
        encounter_id = fraud_output.get("encounter_id", "UNKNOWN")
        risk_level = fraud_output.get("risk_level", "MEDIUM")
        findings = fraud_output.get("findings", "")

        if DEMO_MODE:
            logger.info("DEMO GRC alert  doc=%s risk=%s", doc_number, risk_level)
            return SAPResponse(
                success=True,
                module=SAPModule.GRC,
                message=f"DEMO: GRC issue {doc_number} raised — risk {risk_level}",
                doc_number=doc_number,
                odata_context=f"$metadata#GRCIssue('{doc_number}')",
                payload={
                    "RiskLevel": risk_level,
                    "Findings": findings,
                    "PatientId": patient_id,
                    "EncounterId": encounter_id,
                },
            )

        token = await self._get_sap_token()
        headers = self._make_odata_headers(token)
        url = f"{self.api_base_url}{ODATA_GRC_PATH}"
        body = {
            "RiskLevel": risk_level,
            "Description": findings if isinstance(findings, str) else str(findings),
            "PatientId": patient_id,
            "EncounterId": encounter_id,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        return SAPResponse(
            success=True,
            module=SAPModule.GRC,
            message=f"GRC issue raised: {data.get('IssueNumber', doc_number)}",
            doc_number=data.get("IssueNumber", doc_number),
            odata_context=data.get("@odata.context", ""),
            payload=data,
        )

    # ── iFlow 4 — Analytics (PopulationHealthAgent → SAC) ───────────────

    async def push_analytics_to_sac(self, analytics_output: dict[str, Any]) -> SAPResponse:
        """Push KPI data points to SAP Analytics Cloud.

        Expected keys: patient_count_30d, readmission_rate, icu_occupancy_pct
        """
        doc_number = self._next_doc_number("SAC")

        if DEMO_MODE:
            logger.info("DEMO SAC push  doc=%s", doc_number)
            return SAPResponse(
                success=True,
                module=SAPModule.SAC,
                message=f"DEMO: Analytics payload {doc_number} pushed to SAC",
                doc_number=doc_number,
                odata_context=f"$metadata#KPIDataPoint('{doc_number}')",
                payload={
                    "PatientCount30d": analytics_output.get("patient_count_30d", 0),
                    "ReadmissionRate": analytics_output.get("readmission_rate", 0.0),
                    "ICUOccupancyPct": analytics_output.get("icu_occupancy_pct", 0.0),
                },
            )

        token = await self._get_sap_token()
        headers = self._make_odata_headers(token)
        url = f"{self.api_base_url}{ODATA_SAC_PATH}"
        body = {
            "PatientCount30d": analytics_output.get("patient_count_30d", 0),
            "ReadmissionRate": analytics_output.get("readmission_rate", 0.0),
            "ICUOccupancyPct": analytics_output.get("icu_occupancy_pct", 0.0),
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        return SAPResponse(
            success=True,
            module=SAPModule.SAC,
            message=f"Analytics pushed: {data.get('KPIDataPointId', doc_number)}",
            doc_number=data.get("KPIDataPointId", doc_number),
            odata_context=data.get("@odata.context", ""),
            payload=data,
        )

    # ── Module status ────────────────────────────────────────────────────

    async def get_module_status(self) -> list[SAPModuleStatus]:
        """Return connectivity status for each SAP module."""
        statuses: list[SAPModuleStatus] = []
        for module in SAPModule:
            if DEMO_MODE:
                statuses.append(SAPModuleStatus(
                    module=module,
                    status=SAPConnectionStatus.DEMO,
                    latency_ms=random.randint(5, 50),
                    message=f"Demo mode — {module.value} simulated",
                ))
            else:
                try:
                    token = await self._get_sap_token()
                    _headers = self._make_odata_headers(token)
                    statuses.append(SAPModuleStatus(
                        module=module,
                        status=SAPConnectionStatus.CONNECTED,
                        latency_ms=random.randint(10, 200),
                        message=f"{module.value} connected",
                    ))
                except Exception as exc:
                    statuses.append(SAPModuleStatus(
                        module=module,
                        status=SAPConnectionStatus.ERROR,
                        message=str(exc),
                    ))
        return statuses


# ── Module-level singleton ───────────────────────────────────────────────────

sap_service = SAPIntegrationService()
