# Phoenix Guardian — System Architecture

## Phoenix Guardian v5.0 — SAP-Integrated Architecture

_Updated: Phase 3 — Enterprise Healthcare Integration Layer_

### Full System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│              React 18 Frontend — SAP Fiori UI5                   │
│  ShellBar · LaunchpadPage · ERPDashboardPage · Recharts Charts   │
│  @ui5/webcomponents-react · TailwindCSS · Zustand Auth Store     │
│  (Netlify / localhost:3000)                                      │
└──────────────────────────┬──────────────────────────────────────┘
                           │ REST + OData ($top $skip $filter) + WebSocket
┌──────────────────────────▼──────────────────────────────────────┐
│              FastAPI Backend — OData-Compatible API              │
│  17 existing routes + /sap/billing + /sap/procurement           │
│  + /sap/compliance-alert + /sap/analytics + /sap/status         │
│  JWT Auth · BTP Role Collections · OData Response Envelopes     │
│  (Render / localhost:8000 · /api/docs → Swagger UI)             │
└──────────────────────────┬──────────────────────────────────────┘
                           │
          ┌────────────────┼──────────────────┐
          ▼                ▼                  ▼
  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐
  │  35 AI Agents│  │  ML Models   │  │   Security Layer         │
  │  4-Phase     │  │  XGBoost     │  │   PQC Kyber-1024         │
  │  Parallel    │  │  Readmission │  │   PHI Field Encryption   │
  │  Orchestrator│  │  TF-IDF      │  │   Honeytoken System      │
  │              │  │  Threat Det. │  │   ML Threat Detection    │
  │  CodingAgent │  │              │  │   HIPAA Audit Trail      │
  │  OrdersAgent │  │              │  │   JWT + RBAC             │
  │  FraudAgent  │  │              │  │                          │
  │  PharmacyAgt │  │              │  │                          │
  │  PopHealthAgt│  │              │  │                          │
  │  + 30 more   │  │              │  │                          │
  └──────┬───────┘  └──────┬───────┘  └──────────────────────────┘
         │                 │
         └────────┬─────────┘
                  │ Agent output dicts (patient_id, icd10_codes,
                  │ medications, fraud_findings, kpi_metrics, etc.)
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│          Enterprise Healthcare Integration Layer          ← NEW  │
│                                                                  │
│   sap_integration_service.py   (SAP iFlow pattern)              │
│   ├── post_billing_to_fico()   CodingAgent → FICO               │
│   ├── create_purchase_req()    OrdersAgent + PharmacyAgent → MM  │
│   ├── raise_grc_alert()        FraudAgent → GRC                 │
│   └── push_analytics_to_sac()  PopulationHealthAgent → SAC      │
│                                                                  │
│   adapter_registry.py          (SAP Integration Suite pattern)   │
│   ├── EpicFHIRAdapter          FHIR R4 → Epic EHR               │
│   ├── CernerFHIRAdapter        FHIR R4 → Cerner/Oracle Health   │
│   ├── MeditechAdapter          HL7 v2 → Meditech                │
│   └── AthenaHealthAdapter      REST → athenahealth              │
└──────────────────────────┬──────────────────────────────────────┘
                           │ OData REST APIs (real SAP endpoints)
                           │ OAuth2 Bearer (SAP BTP XSUAA)
          ┌────────────────┼────────────────────┐
          ▼                ▼                    ▼
  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
  │  SAP FICO    │  │   SAP MM     │  │   SAP GRC    │
  │  S/4HANA FI  │  │  Materials   │  │ Governance,  │
  │  Billing     │  │  Mgmt        │  │ Risk &       │
  │  Invoice DR  │  │  PR type NB  │  │ Compliance   │
  │  GL Posting  │  │  Plant HOSP  │  │ Issue Mgmt   │
  └──────────────┘  └──────────────┘  └──────────────┘
          ▼
  ┌──────────────────────────┐
  │   SAP Analytics Cloud    │
  │   PHOENIX_HOSPITAL_KPI   │
  │   dataset                │
  │   KPI Dashboards + BI    │
  └──────────────────────────┘
                  ▼
  ┌─────────────────────────────────────────────────────┐
  │   Ktern.AI (Kaar Technologies)                      │
  │   SAP transformation intelligence layer             │
  │   Phoenix Guardian analytics → S/4HANA migration   │
  └─────────────────────────────────────────────────────┘

─────────────────────────────────────────────────────────────────
         DATA PERSISTENCE LAYER (unchanged from v4)
─────────────────────────────────────────────────────────────────

  ┌─────────────────────────────────┐
  │  PostgreSQL 16  │  Redis 7.x    │
  │  SQLAlchemy ORM │  Caching      │
  │  Alembic Migrat.│  Pub/Sub      │
  └─────────────────────────────────┘
```

### Component → SAP Mapping (Full Reference)

| Phoenix Guardian Layer | Component | SAP Equivalent | SAP Module |
|------------------------|-----------|----------------|------------|
| **Frontend** | Fiori ShellBar | SAP Fiori Launchpad Shell | SAP Fiori |
| **Frontend** | LaunchpadPage tiles | SAP FLP App Tiles (GenericTile) | SAP Fiori |
| **Frontend** | ERPDashboardPage | SAP Integration Suite Monitor | SAP IS |
| **Frontend** | JWT Role Collections | SAP BTP XSUAA Role Collections | SAP BTP |
| **API Layer** | OData query params | SAP OData v4 system options | SAP OData |
| **API Layer** | POST /sap/billing | SAP FICO billing iFlow inbound | SAP IS |
| **API Layer** | POST /sap/procurement | SAP MM PR iFlow inbound | SAP IS |
| **API Layer** | POST /sap/compliance-alert | SAP GRC issue iFlow | SAP IS |
| **API Layer** | POST /sap/analytics | SAP SAC dataset update | SAP IS |
| **Agents** | CodingAgent (ICD-10/CPT) | SAP FI billing coding | SAP FICO |
| **Agents** | OrdersAgent | SAP MM purchase requisition | SAP MM |
| **Agents** | PharmacyAgent | SAP MM inventory management | SAP MM + WM |
| **Agents** | FraudAgent | SAP GRC compliance monitoring | SAP GRC |
| **Agents** | PopulationHealthAgent | SAP SAC predictive analytics | SAP SAC |
| **Agents** | ReadmissionAgent | SAP SAC KPI + CO planning | SAP SAC + CO |
| **Agents** | AgentOrchestrator (4-phase) | SAP IS iFlow pipeline | SAP IS |
| **Integration** | SAPIntegrationService | SAP Integration Suite iFlows | SAP IS |
| **Integration** | AdapterRegistry | SAP IS Adapter Catalog | SAP IS |
| **Integration** | EpicFHIRAdapter | SAP IS FHIR adapter | SAP IS |
| **Integration** | CernerFHIRAdapter | SAP IS FHIR adapter | SAP IS |
| **Integration** | MeditechAdapter | SAP IS HL7 v2 adapter | SAP IS |
| **Security** | JWT + RBAC | SAP BTP XSUAA OAuth2 | SAP BTP |
| **Security** | PQC Kyber-1024 | SAP BTP Credential Store | SAP BTP |
| **Security** | HIPAA Audit Log | SAP BTP Audit Log Service | SAP BTP |
| **Security** | Honeytokens | SAP Enterprise Threat Detection | SAP ETD |
| **Infra** | Docker + Kubernetes | SAP BTP Cloud Foundry | SAP BTP |
| **Infra** | GitHub Actions CI/CD | SAP BTP Transport Management | SAP BTP TMS |
| **Infra** | Render (backend) | SAP BTP Kyma Runtime | SAP BTP |
| **Infra** | Temporal.io SAGA | SAP Process Orchestration | SAP PO |

### Enterprise Hospital Workflow — End to End

```
Step 1:  Doctor completes clinical encounter in Phoenix Guardian UI
Step 2:  ScribeAgent generates SOAP note (Subjective, Objective, Assessment, Plan)
Step 3:  CodingAgent generates ICD-10 diagnosis + CPT procedure codes
              └─→ POST /sap/billing → SAPIntegrationService.post_billing_to_fico()
              └─→ SAP FICO: Customer invoice (doc type DR) + GL posting
Step 4:  OrdersAgent suggests lab tests and medication prescriptions
Step 5:  PharmacyAgent validates formulary and generates e-prescription
              └─→ POST /sap/procurement → create_purchase_requisition()
              └─→ SAP MM: Purchase Requisition (type NB, Plant HOSP)
Step 6:  FraudAgent validates billing codes for anomalies (NCCI, upcoding)
              └─→ POST /sap/compliance-alert → raise_grc_alert()
              └─→ SAP GRC: Compliance issue + remediation workflow
Step 7:  ReadmissionAgent computes 30-day readmission risk (XGBoost)
Step 8:  PopulationHealthAgent updates population analytics
              └─→ POST /sap/analytics → push_analytics_to_sac()
              └─→ SAP Analytics Cloud: PHOENIX_HOSPITAL_KPI dataset refresh
Step 9:  Hospital CFO sees updated KPIs on SAC dashboard
Step 10: Finance team approves FICO invoices → payment processing
```

### Design Patterns Used (Interview Ready)

| Pattern | Implementation | SAP Equivalent |
|---------|---------------|----------------|
| **Polymorphism** | `BaseIntegrationAdapter` ABC with EpicFHIR, Cerner, Meditech subclasses | SAP IS adapter interface |
| **Registry** | `AdapterRegistry` — add new EHR with one `register()` call | SAP Integration Directory |
| **Strategy** | Each adapter implements `send_message()` differently | SAP IS adapter strategy |
| **Open/Closed** | New EHR systems added without changing orchestration | SAP IS extensibility |
| **Repository** | SQLAlchemy ORM for all data access | SAP ABAP persistence layer |
| **Factory** | `SAPIntegrationService` creates typed responses per module | SAP IS message factory |
| **SAGA** | Temporal.io workflow with compensation rollback | SAP Process Orchestration |
| **Circuit Breaker** | Agent orchestrator retry + fallback | SAP IS error handling iFlow |
