"""Unit tests for SAPIntegrationService (Phase 2 — iFlow API).

Tests all four iFlow methods, module status, OData envelope, and doc-number
format assertions.
"""

import asyncio
import os

import pytest

# Ensure SAP demo mode for all tests
os.environ["SAP_DEMO_MODE"] = "true"
os.environ["DEMO_MODE"] = "true"

from phoenix_guardian.services.sap_integration_service import (
    SAPConnectionStatus,
    SAPIntegrationService,
    SAPModule,
    SAPModuleStatus,
    SAPResponse,
    sap_service,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def sap_service():
    """Fresh SAPIntegrationService instance for each test."""
    return SAPIntegrationService()


@pytest.fixture
def coding_output():
    """Sample CodingAgent billing payload."""
    return {
        "patient_id": "PAT-TEST-001",
        "encounter_id": "ENC-TEST-001",
        "icd10_codes": ["E11.9", "I10"],
        "cpt_codes": ["99213"],
    }


@pytest.fixture
def orders_output():
    """Sample OrdersAgent procurement payload."""
    return {
        "patient_id": "PAT-TEST-002",
        "encounter_id": "ENC-TEST-002",
        "medications": [{"name": "Amoxicillin", "quantity": 21, "unit": "TAB"}],
        "lab_orders": [{"code": "80053", "name": "CMP", "quantity": 1}],
    }


@pytest.fixture
def fraud_output():
    """Sample FraudAgent GRC alert payload."""
    return {
        "patient_id": "PAT-TEST-003",
        "encounter_id": "ENC-TEST-003",
        "risk_level": "HIGH",
        "findings": "Upcoding anomaly detected in billing pattern",
    }


@pytest.fixture
def population_health_output():
    """Sample PopulationHealthAgent analytics payload."""
    return {
        "patient_count_30d": 142,
        "readmission_rate": 0.069,
        "icu_occupancy_pct": 74.5,
    }


# ── SAPModule enum tests ────────────────────────────────────────────────────

class TestSAPModule:
    def test_fico_value(self):
        assert SAPModule.FICO.value == "FICO"

    def test_mm_value(self):
        assert SAPModule.MM.value == "MM"

    def test_grc_value(self):
        assert SAPModule.GRC.value == "GRC"

    def test_sac_value(self):
        assert SAPModule.SAC.value == "SAC"

    def test_four_modules(self):
        assert len(SAPModule) == 4


# ── SAPResponse / OData envelope tests ──────────────────────────────────────

class TestSAPResponse:
    def test_to_odata_dict_structure(self):
        resp = SAPResponse(
            success=True,
            module=SAPModule.FICO,
            doc_number="FI-5100000042",
            message="test",
        )
        envelope = resp.to_odata_dict()
        assert "@odata.context" in envelope
        assert "value" in envelope
        assert envelope["value"]["DocumentNumber"] == "FI-5100000042"
        assert envelope["value"]["Module"] == "FICO"
        assert envelope["value"]["Success"] is True

    def test_odata_context_default(self):
        resp = SAPResponse(success=True, module=SAPModule.MM, doc_number="PR-0010000001")
        envelope = resp.to_odata_dict()
        assert envelope["@odata.context"] == "$metadata#MM"


# ── iFlow 1: Billing (post_billing_to_fico) ─────────────────────────────────

class TestPostBillingToFico:
    def test_success(self, sap_service, coding_output):
        result = asyncio.run(sap_service.post_billing_to_fico(coding_output))
        assert result.success is True
        assert result.module == SAPModule.FICO

    def test_doc_number_prefix(self, sap_service, coding_output):
        result = asyncio.run(sap_service.post_billing_to_fico(coding_output))
        assert result.doc_number.startswith("FI-")

    def test_message_contains_encounter(self, sap_service, coding_output):
        result = asyncio.run(sap_service.post_billing_to_fico(coding_output))
        assert "ENC-TEST-001" in result.message

    def test_odata_envelope(self, sap_service, coding_output):
        result = asyncio.run(sap_service.post_billing_to_fico(coding_output))
        envelope = result.to_odata_dict()
        assert "@odata.context" in envelope
        assert "value" in envelope
        assert "DocumentNumber" in envelope["value"]

    def test_demo_mode_flag(self, sap_service, coding_output):
        result = asyncio.run(sap_service.post_billing_to_fico(coding_output))
        assert result.demo_mode is True

    def test_empty_codes(self, sap_service):
        result = asyncio.run(sap_service.post_billing_to_fico({
            "patient_id": "P1", "encounter_id": "E1"
        }))
        assert result.success is True
        assert result.doc_number.startswith("FI-")


# ── iFlow 2: Procurement (create_purchase_requisition) ──────────────────────

class TestCreatePurchaseRequisition:
    def test_success(self, sap_service, orders_output):
        result = asyncio.run(sap_service.create_purchase_requisition(orders_output))
        assert result.success is True
        assert result.module == SAPModule.MM

    def test_doc_number_prefix(self, sap_service, orders_output):
        result = asyncio.run(sap_service.create_purchase_requisition(orders_output))
        assert result.doc_number.startswith("PR-")

    def test_message_mentions_meds(self, sap_service, orders_output):
        result = asyncio.run(sap_service.create_purchase_requisition(orders_output))
        assert "1 meds" in result.message

    def test_empty_orders(self, sap_service):
        result = asyncio.run(sap_service.create_purchase_requisition({
            "patient_id": "P1", "encounter_id": "E1",
            "medications": [], "lab_orders": [],
        }))
        assert result.success is True
        assert result.doc_number.startswith("PR-")


# ── iFlow 3: GRC Alert (raise_grc_alert) ────────────────────────────────────

class TestRaiseGrcAlert:
    def test_success(self, sap_service, fraud_output):
        result = asyncio.run(sap_service.raise_grc_alert(fraud_output))
        assert result.success is True
        assert result.module == SAPModule.GRC

    def test_doc_number_prefix(self, sap_service, fraud_output):
        result = asyncio.run(sap_service.raise_grc_alert(fraud_output))
        assert result.doc_number.startswith("GRC-ISSUE-")

    def test_risk_level_in_message(self, sap_service, fraud_output):
        result = asyncio.run(sap_service.raise_grc_alert(fraud_output))
        assert "HIGH" in result.message


# ── iFlow 4: SAC Analytics (push_analytics_to_sac) ──────────────────────────

class TestPushAnalyticsToSac:
    def test_success(self, sap_service, population_health_output):
        result = asyncio.run(sap_service.push_analytics_to_sac(population_health_output))
        assert result.success is True
        assert result.module == SAPModule.SAC

    def test_doc_number_prefix(self, sap_service, population_health_output):
        result = asyncio.run(sap_service.push_analytics_to_sac(population_health_output))
        assert result.doc_number.startswith("SAC-KPI-")

    def test_module_value(self, sap_service, population_health_output):
        result = asyncio.run(sap_service.push_analytics_to_sac(population_health_output))
        assert result.module.value == "SAC"


# ── Module Status Tests ──────────────────────────────────────────────────────

class TestGetModuleStatus:
    def test_returns_all_four_modules(self, sap_service):
        statuses = asyncio.run(sap_service.get_module_status())
        assert len(statuses) == 4
        modules = {s.module for s in statuses}
        assert SAPModule.FICO in modules
        assert SAPModule.MM in modules
        assert SAPModule.GRC in modules
        assert SAPModule.SAC in modules

    def test_demo_status_label(self, sap_service):
        statuses = asyncio.run(sap_service.get_module_status())
        for s in statuses:
            assert s.status == SAPConnectionStatus.DEMO

    def test_status_has_latency(self, sap_service):
        statuses = asyncio.run(sap_service.get_module_status())
        for s in statuses:
            assert s.latency_ms >= 0


# ── Singleton ────────────────────────────────────────────────────────────────

class TestSingleton:
    def test_module_level_instance_exists(self):
        from phoenix_guardian.services.sap_integration_service import sap_service as singleton
        assert singleton is not None
        assert isinstance(singleton, SAPIntegrationService)
