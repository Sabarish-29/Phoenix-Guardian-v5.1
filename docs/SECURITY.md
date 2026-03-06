# Security Documentation — Phoenix Guardian

This document describes the security architecture of the Phoenix Guardian
Healthcare AI Platform. For HIPAA compliance details, see
[HIPAA_COMPLIANCE.md](HIPAA_COMPLIANCE.md). For incident response
procedures, see [INCIDENT_RESPONSE.md](INCIDENT_RESPONSE.md).


---

## SAP BTP Identity & Access Management (IAM) Alignment

Phoenix Guardian's authentication and authorization architecture is
aligned with SAP Business Technology Platform (BTP) identity patterns,
specifically the XSUAA (Extended Services for User Account and
Authentication) service model.

### Overview

| Phoenix Guardian Concept | SAP BTP Equivalent |
|--------------------------|-------------------|
| JWT Bearer Token (PyJWT) | XSUAA OAuth2 access token |
| RBAC role string (PHYSICIAN, ADMIN, etc.) | BTP Role (sap.xssec role) |
| Role group → permission set | BTP Role Collection |
| Route-level Depends(require_role([...])) | XSUAA scope check |
| 7-year HIPAA audit log | BTP Audit Log Service |
| bcrypt password hash | BTP Identity Authentication Service (IAS) |

### Role Collections (SAP BTP Pattern)

In SAP BTP, a **Role Collection** bundles one or more Roles and is
assigned to users or user groups. Phoenix Guardian replicates this
pattern through its RBAC system:

| Phoenix Guardian Collection | Assigned Roles | SAP BTP Equivalent | Access Level |
|----------------------------|---------------|-------------------|--------------|
| `PG_PHYSICIAN` | PHYSICIAN, SCRIBE | Fiori Business User | Clinical full access |
| `PG_ADMIN` | ADMIN | BTP Sub-account Admin | System administrator |
| `PG_NURSE` | NURSE | Fiori Business User | Care workflow access |
| `PG_FINANCE_VIEWER` | ADMIN (read-only scope) | FICO Report Viewer | Billing read access |
| `PG_ANALYTICS_VIEWER` | All roles (read-only) | SAC Analytics Viewer | Dashboard read access |
| `PG_READONLY` | READONLY | Fiori Guest User | View-only access |

### OAuth2 Scope Definitions (XSUAA-Compatible)

SAP BTP XSUAA uses OAuth2 scopes to define fine-grained permissions.
Phoenix Guardian's permission model maps to equivalent scopes:

```
# Clinical scopes
encounter:read         → View clinical encounter records
encounter:write        → Create and update encounter records
encounter:delete       → Delete encounter records (ADMIN only)
soap_note:read         → View AI-generated SOAP notes
soap_note:write        → Generate and edit SOAP notes

# SAP ERP integration scopes (Phase 2 — in development)
billing:read           → View SAP FICO invoice documents
billing:write          → Post ICD-10/CPT codes to SAP FICO
procurement:read       → View SAP MM purchase orders
procurement:write      → Create SAP MM purchase requisitions
grc:read               → View SAP GRC compliance issues
grc:alert              → Raise SAP GRC compliance alerts
analytics:read         → View SAP Analytics Cloud KPIs
analytics:write        → Push KPI data to SAP SAC

# Platform scopes
admin:users            → Manage user accounts and role assignments
admin:system           → System configuration and audit access
security:console       → Access to security monitoring console
pqc:manage             → Post-quantum encryption key management
```

### Authentication Flow (XSUAA-Aligned)

```
1. Client POST /auth/login → {email, password}
        ↓
2. Server validates credentials (bcrypt verify)
        ↓
3. JWT issued with payload:
   {
     "sub": "user_id",
     "role": "PHYSICIAN",          ← maps to BTP Role
     "exp": <unix_timestamp>,
     "iss": "phoenix-guardian"     ← maps to BTP XSUAA issuer
   }
   (mirrors XSUAA access token structure)
        ↓
4. Client sends: Authorization: Bearer <token>
        ↓
5. FastAPI dependency: get_current_user() validates JWT
   → role extracted from token claims
   → require_role([...]) checks scope (like XSUAA scope check)
        ↓
6. Every access event written to HIPAA audit trail
   (mirrors SAP BTP Audit Log Service)
```

### Production SAP BTP Deployment Notes

In a production hospital SAP BTP deployment, the JWT issuer would be
replaced with the SAP XSUAA service URL. The token validation logic in
`phoenix_guardian/api/auth/utils.py` is structured to accept a
configurable issuer, making the migration to XSUAA straightforward:

1. Set `JWT_ISSUER` env var to the BTP XSUAA URL
2. Configure `SAP_BTP_CLIENT_ID` and `SAP_BTP_CLIENT_SECRET`  
3. The existing `require_role()` dependency maps directly to XSUAA
   scope-based authorization

> **Implementation status:** JWT authentication and RBAC are fully
> implemented. SAP BTP XSUAA integration is planned for Phase 2
> (enterprise deployment configuration).
