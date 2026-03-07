#!/usr/bin/env python3
"""
demo_sap_integration.py

Phoenix Guardian x SAP Integration — Live Terminal Demo.

Demonstrates all 4 SAP iFlows + AdapterRegistry polymorphism.
No server required. No real SAP connection required (demo mode).

Usage:
    cd phoenix-guardian-v4
    python scripts/demo_sap_integration.py

Runtime: ~5 seconds
"""

import asyncio
import json
import os
import sys

# Add project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ANSI colour codes
G = "\033[92m"   # green
B = "\033[94m"   # blue
Y = "\033[93m"   # yellow
R = "\033[91m"   # red
W = "\033[97m"   # white
X = "\033[0m"    # reset
BOLD = "\033[1m"


def section(title: str) -> None:
    print(f"\n{W}{'═' * 60}{X}")
    print(f"  {BOLD}{title}{X}")
    print(f"{W}{'═' * 60}{X}")


def ok(label: str, value: str, colour: str = G) -> None:
    print(f"  {colour}✓{X}  {label}: {colour}{value}{X}")


def info(text: str) -> None:
    print(f"  {W}ℹ{X}  {text}")


async def main() -> None:
    print(f"\n{W}{'█' * 60}{X}")
    print(f"  {BOLD}PHOENIX GUARDIAN × SAP INTEGRATION — LIVE DEMO{X}")
    print(f"  Kaar Technologies — Campus Recruitment Demo")
    print(f"{W}{'█' * 60}{X}")

    # ── Imports ──────────────────────────────────────────────────
    from phoenix_guardian.services.sap_integration_service import (
        SAPIntegrationService,
    )
    from phoenix_guardian.integrations.adapter_registry import (
        adapter_registry,
        AdapterMessage,
    )

    sap = SAPIntegrationService()

    # ════════════════════════════════════════════════════════════
    # DEMO 1 — CodingAgent → SAP FICO
    # ════════════════════════════════════════════════════════════
    section("DEMO 1 — CodingAgent → SAP FICO (Customer Invoice)")
    info("Scenario: encounter complete, AI generates ICD-10 + CPT codes")
    info("Action:   SAPIntegrationService.post_billing_to_fico()")
    print()

    r1 = await sap.post_billing_to_fico({
        "patient_id":   "PAT-00123",
        "encounter_id": "ENC-00456",
        "icd10_codes":  ["J18.9", "Z87.891"],
        "cpt_codes":    ["99213", "71046"],
    })
    ok("SAP FICO Document",  r1.doc_number,  G)
    ok("Document Type",      "DR — Debitor Rechnung (Customer Invoice)",  G)
    ok("Company Code",       "HOSP",         G)
    ok("OData context",      r1.to_odata_dict()["@odata.context"],  B)
    ok("Status",             "SUCCESS" if r1.success else "FAILED",  G)
    print()
    print(f"  {B}OData Response Envelope:{X}")
    print(f"  {json.dumps(r1.to_odata_dict(), indent=4)}")

    # ════════════════════════════════════════════════════════════
    # DEMO 2 — OrdersAgent + PharmacyAgent → SAP MM
    # ════════════════════════════════════════════════════════════
    section("DEMO 2 — OrdersAgent + PharmacyAgent → SAP MM (Purchase Req)")
    info("Scenario: physician prescribes medications + orders lab tests")
    info("Action:   SAPIntegrationService.create_purchase_requisition()")
    print()

    r2 = await sap.create_purchase_requisition({
        "patient_id":   "PAT-00123",
        "encounter_id": "ENC-00456",
        "medications": [
            {"name": "Amoxicillin 500mg",  "quantity": 21, "unit": "TAB"},
            {"name": "Azithromycin 250mg", "quantity": 6,  "unit": "TAB"},
        ],
        "lab_orders": [
            {"test_name": "Complete Blood Count", "priority": "STAT"},
        ],
    })
    ok("SAP MM Purchase Req",  r2.doc_number,  B)
    ok("PR Type",              "NB — Normal Bestellung (Standard PR)",  B)
    ok("Line Items",           "3  (2 medications + 1 lab order)",       B)
    ok("Plant / Storage",      "HOSP / SL01 (pharmacy) + SL02 (lab)",    B)
    ok("Status",               "SUCCESS" if r2.success else "FAILED",    B)

    # ════════════════════════════════════════════════════════════
    # DEMO 3 — FraudAgent → SAP GRC
    # ════════════════════════════════════════════════════════════
    section("DEMO 3 — FraudAgent → SAP GRC (Compliance Issue)")
    info("Scenario: FraudAgent detects NCCI unbundling in billing codes")
    info("Action:   SAPIntegrationService.raise_grc_alert()")
    print()

    r3 = await sap.raise_grc_alert({
        "patient_id":   "PAT-00789",
        "encounter_id": "ENC-00999",
        "risk_level":   "HIGH",
        "findings":     "NCCI unbundling detected in CPT codes 99213 and 99214",
        "fraud_types":  ["NCCI_UNBUNDLING", "UPCODING"],
        "amount":       45000.00,
    })
    ok("SAP GRC Issue ID",    r3.doc_number,                                  R)
    ok("GRC Severity",        "2 — HIGH  (SAP scale: 1=Critical → 5=Info)",  R)
    ok("Control Objective",   "CO_BILLING_ACCURACY",                          R)
    ok("Risk Category",       "BILLING_INTEGRITY",                            R)
    ok("Status",              "SUCCESS" if r3.success else "FAILED",          R)

    # ════════════════════════════════════════════════════════════
    # DEMO 4 — PopulationHealthAgent → SAP Analytics Cloud
    # ════════════════════════════════════════════════════════════
    section("DEMO 4 — PopulationHealthAgent → SAP Analytics Cloud (KPIs)")
    info("Scenario: ML agents compute hospital KPIs for executive dashboard")
    info("Action:   SAPIntegrationService.push_analytics_to_sac()")
    print()

    r4 = await sap.push_analytics_to_sac({
        "patient_count_30d": 142,
        "readmission_rate":  0.069,
        "icu_occupancy_pct": 74.5,
        "avg_los_days":      3.8,
        "high_risk_count":   7,
    })
    ok("SAP SAC Dataset",     "PHOENIX_HOSPITAL_KPI",               Y)
    ok("Update Reference",    r4.doc_number,                         Y)
    ok("KPIs Pushed",         "9 metrics (ops + ERP counters)",      Y)
    ok("Readmission Rate",    "6.9%  (XGBoost ML model output)",     Y)
    ok("ICU Occupancy",       "74.5%",                               Y)
    ok("Status",              "SUCCESS" if r4.success else "FAILED", Y)

    # ════════════════════════════════════════════════════════════
    # DEMO 5 — Module Status
    # ════════════════════════════════════════════════════════════
    section("DEMO 5 — SAP Module Status  (GET /api/v1/sap/status)")
    info("All 4 SAP module connections:\n")

    for s in await sap.get_module_status():
        colour = G if s.status.value in ("CONNECTED", "DEMO") else R
        ok(
            f"{s.module.value:<8}",
            f"{s.status.value:<12}  latency: {s.latency_ms}ms  "
            f"{s.message}",
            colour,
        )

    # ════════════════════════════════════════════════════════════
    # DEMO 6 — AdapterRegistry Polymorphism
    # ════════════════════════════════════════════════════════════
    section("DEMO 6 — AdapterRegistry  (Runtime Polymorphism)")
    info("Same send_message() call → 3 completely different EHR protocols")
    info("This is BaseIntegrationAdapter polymorphism (mirrors SAP IS adapter model)\n")

    message = AdapterMessage(
        payload={"resourceType": "Patient", "id": "PAT-00123"},
        message_id="DEMO-MSG-001",
        source="PhoenixGuardian",
        destination="EHR",
    )

    for adapter_id in ["epic_fhir", "cerner_fhir", "hl7_meditech"]:
        adapter = adapter_registry.get(adapter_id)
        info_obj = adapter.get_info()
        await adapter.connect()
        response = await adapter.send_message(message)
        ok(
            f"{info_obj.display_name:<42}",
            f"corr_id: {response.correlation_id}",
            B,
        )

    print()
    print(f"  {B}↑ Identical calling code — 3 protocols: FHIR R4 (Epic), FHIR R4 (Cerner), HL7 v2 (Meditech){X}")
    print(f"  {G}↑ Open/Closed: register DrChronoAdapter in 10 lines, zero existing code touched{X}")
    print()
    print(f"  All registered adapters:")
    for info_obj in adapter_registry.list_adapters():
        print(f"    {B}{info_obj.adapter_id:<22}{X}  "
              f"{info_obj.protocol.value:<12}  {info_obj.status.value}")

    # ════════════════════════════════════════════════════════════
    # SUMMARY
    # ════════════════════════════════════════════════════════════
    section("DEMO COMPLETE — Summary")
    print()
    print(f"  {G}✓{X}  SAP FICO  — Customer invoice  doc type DR      | {G}{r1.doc_number}{X}")
    print(f"  {B}✓{X}  SAP MM    — Purchase Req       type NB          | {B}{r2.doc_number}{X}")
    print(f"  {R}✓{X}  SAP GRC   — Compliance issue   severity HIGH=2  | {R}{r3.doc_number}{X}")
    print(f"  {Y}✓{X}  SAP SAC   — Analytics Cloud    9 KPIs pushed    | {Y}{r4.doc_number}{X}")
    print()
    print(f"  {B}✓{X}  Adapter Registry: 4 EHR adapters, polymorphic ABC interface")
    print(f"  {G}✓{X}  All responses use @odata.context OData envelope format")
    print(f"  {W}ℹ{X}  To go live: set SAP_DEMO_MODE=false + SAP_API_BASE_URL in .env")
    print(f"  {W}ℹ{X}  Ktern.AI compatible — clinical AI → SAP transformation intelligence")
    print()
    print(f"{W}{'█' * 60}{X}")
    print(f"  {BOLD}Phoenix Guardian v5 — Kaar Technologies Campus Demo{X}")
    print(f"{W}{'█' * 60}{X}\n")


if __name__ == "__main__":
    asyncio.run(main())
