# SAP Integration Reference — Phoenix Guardian

## Overview

Phoenix Guardian's Enterprise Healthcare Integration Layer bridges AI agent
outputs to SAP S/4HANA via OData-compatible REST APIs. Demo mode (default,
`SAP_DEMO_MODE=true`) requires zero SAP connectivity and returns responses
using real SAP document number formats. Going live requires only SAP BTP
credentials in `.env` — no code changes.

---

## SAP Module Reference

### 1. SAP S/4HANA Finance (FICO) — CodingAgent → Customer Invoice

**What happens:** CodingAgent generates ICD-10 diagnosis + CPT procedure codes
from the clinical encounter. `SAPIntegrationService.post_billing_to_fico()`
transforms these into a SAP FI customer invoice.

| Field | Value |
|-------|-------|
| **Phoenix Guardian endpoint** | `POST /api/v1/sap/billing` |
| **SAP OData service** | `API_BILLING_DOCUMENT_SRV` (S/4HANA 2023) |
| **SAP OData path** | `/sap/opu/odata/sap/API_BILLING_DOCUMENT_SRV/A_BillingDocument` |
| **SAP document type** | `DR` — Debitor Rechnung (Customer Invoice) |
| **Company code** | `HOSP` |
| **Tax code** | `I1` |
| **Doc number format** | `FI-5100XXXXX` |

**Field mapping:**

| Phoenix Guardian | SAP FI Field | Example |
|-----------------|-------------|---------|
| `patient_id` | Custom extension | `PAT-00123` |
| `encounter_id` | Header text | `ENC-00456` |
| `icd10_codes[]` | Diagnosis codes | `["J18.9", "Z87.891"]` |
| `cpt_codes[]` | Procedure codes | `["99213", "71046"]` |
| `currency_code` | Currency key | `INR` |

---

### 2. SAP MM — Materials Management — Orders → Purchase Requisition

**What happens:** OrdersAgent and PharmacyAgent generate medication prescriptions
and lab test orders. `create_purchase_requisition()` creates a SAP MM PR with
one line item per medication and lab test.

| Field | Value |
|-------|-------|
| **Phoenix Guardian endpoint** | `POST /api/v1/sap/procurement` |
| **SAP OData service** | `API_PURCHASEREQ_PROCESS_SRV` (S/4HANA 2023) |
| **SAP OData path** | `/sap/opu/odata/sap/API_PURCHASEREQ_PROCESS_SRV/A_PurchaseRequisitionHeader` |
| **SAP document type** | `NB` — Normal Bestellung (Standard Purchase Requisition) |
| **Doc number format** | `PR-0010XXXXX` |

**Line item GL coding by type:**

| Item Type | Plant | Storage Location | Purchasing Group | GL Account |
|-----------|-------|-----------------|-----------------|------------|
| Medication | `HOSP` | `SL01` (pharmacy) | `PH1` | `510000` (pharmacy expense) |
| Lab order | `HOSP` | `SL02` (lab) | `LB1` | `520000` (lab expense) |
| Account assignment | — | — | — | `K` (cost center) |

---

### 3. SAP GRC — Governance, Risk & Compliance — FraudAgent → Issue

**What happens:** FraudAgent detects billing anomalies (NCCI unbundling,
upcoding, phantom billing). `raise_grc_alert()` creates a SAP GRC compliance
issue with the fraud patterns mapped to SAP severity levels.

| Field | Value |
|-------|-------|
| **Phoenix Guardian endpoint** | `POST /api/v1/sap/compliance-alert` |
| **SAP OData service** | `GRC_PI_RISKMANAGEMENT_SRV` (SAP GRC 12.0) |
| **SAP OData path** | `/sap/opu/odata/sap/GRC_PI_RISKMANAGEMENT_SRV/Issues` |
| **Control objective** | `CO_BILLING_ACCURACY` |
| **Risk category** | `BILLING_INTEGRITY` |
| **Doc number format** | `GRC-ISSUE-XXXXX` |

**Severity mapping:**

| Phoenix Guardian `risk_level` | SAP GRC Severity | Description |
|-------------------------------|-----------------|-------------|
| `CRITICAL` | `1` | Kritisch — immediate action required |
| `HIGH` | `2` | Hoch — high priority |
| `MEDIUM` | `3` | Mittel — medium |
| `LOW` | `4` | Niedrig — low |
| `INFO` | `5` | Informational |

---

### 4. SAP Analytics Cloud (SAC) — PopulationHealthAgent → KPI Dataset

**What happens:** PopulationHealthAgent and ReadmissionAgent compute hospital
KPIs (readmission rate via XGBoost, ICU occupancy, avg length of stay).
`push_analytics_to_sac()` pushes these to the `PHOENIX_HOSPITAL_KPI` dataset,
triggering live refresh of the hospital executive SAC dashboard.

| Field | Value |
|-------|-------|
| **Phoenix Guardian endpoint** | `POST /api/v1/sap/analytics` |
| **SAP API** | SAP Analytics Cloud REST API |
| **SAP path** | `/api/v1/datasphere/datasets` |
| **Dataset name** | `PHOENIX_HOSPITAL_KPI` |
| **Doc number format** | `SAC-KPI-XXXXX` |

**KPIs pushed to SAC (9 metrics):**

| KPI | Source | SAC Story Widget |
|-----|--------|-----------------|
| `PatientCount30Day` | PopulationHealthAgent | KPI tile |
| `ReadmissionRatePct` | ReadmissionAgent (XGBoost) | Trend chart |
| `ICUOccupancyPct` | PopulationHealthAgent | Gauge |
| `AvgLengthOfStayDays` | PopulationHealthAgent | Bar chart |
| `HighRiskPatientCount` | RiskStratifier | Alert tile |
| `SAPFICODocToday` | SAPIntegrationService | ERP ops KPI |
| `SAPMMDocToday` | SAPIntegrationService | ERP ops KPI |
| `SAPGRCAlertToday` | SAPIntegrationService | Compliance KPI |
| `AIAgentCount` | hardcoded (35) | Platform KPI |

---

## Integration Adapter Registry

All EHR connectors implement `BaseIntegrationAdapter` — the same interface
contract as SAP Integration Suite adapters (SOAP, REST, FHIR, HL7 all share
one interface in SAP IS).

```python
# Same calling code for any EHR system — runtime polymorphism
adapter = adapter_registry.get("epic_fhir")   # or cerner_fhir, hl7_meditech
await adapter.connect()
response = await adapter.send_message(message)
```

| Adapter ID | EHR System | Protocol | Backing file |
|------------|-----------|----------|-------------|
| `epic_fhir` | Epic | FHIR R4 REST | `epic_connector.py` |
| `cerner_fhir` | Cerner / Oracle Health | FHIR R4 REST | `cerner_connector.py` |
| `hl7_meditech` | Meditech | HL7 v2 | `meditech_connector.py` |
| `athenahealth` | athenahealth | REST API | `athenahealth_connector.py` |

**Adding a new EHR (Open/Closed Principle):**
```python
class NewEHRAdapter(BaseIntegrationAdapter):
    async def connect(self): ...
    async def send_message(self, m): ...
    async def health_check(self): ...
    def get_info(self): ...

adapter_registry.register("new_ehr", NewEHRAdapter())
# Done — zero changes to existing orchestration code
```

---

## Going Live with Real SAP

1. Set `SAP_DEMO_MODE=false` in `.env`
2. Set `SAP_API_BASE_URL=https://your-tenant.hana.ondemand.com`
3. Set BTP XSUAA credentials:
   ```
   SAP_CLIENT_ID=phoenix_guardian_prod
   SAP_CLIENT_SECRET=<from BTP Cockpit → Security → OAuth2>
   ```
4. Required BTP scopes: `FICO_WRITE`, `MM_PR_WRITE`, `GRC_ISSUE_CREATE`, `SAC_DATASET_WRITE`
5. Restart the backend — `SAPIntegrationService` automatically switches to live OData calls

**No code changes required.** The switch is purely configuration.

---

## Ktern.AI Integration Potential

[Ktern.AI](https://ktern.com) is Kaar Technologies' intelligent SAP digital
transformation platform. It uses AI to automate SAP process analysis, project
planning, and S/4HANA migration — including process mining, risk assessment,
and test case automation.

Phoenix Guardian's clinical AI analytics can feed Ktern.AI in a hospital
S/4HANA transformation engagement:

| Phoenix Guardian Output | Ktern.AI Input |
|------------------------|---------------|
| PopulationHealthAgent hospital KPIs | Business process benchmarks |
| CodingAgent ICD-10/CPT billing patterns | FICO process complexity scoring |
| FraudAgent compliance findings | GRC risk landscape for transformation roadmap |
| OrdersAgent procurement data | MM process maturity assessment |
| ReadmissionAgent ML predictions | Workforce and capacity planning baseline |

In a real Kaar Tech hospital engagement, Ktern.AI plans the S/4HANA migration.
Phoenix Guardian provides the clinical domain intelligence that makes that plan
more accurate and faster to deliver.
