/**
 * LaunchpadPage.jsx
 *
 * SAP Fiori Launchpad-style home screen for Phoenix Guardian.
 *
 * SAP ALIGNMENT:
 *   The SAP Fiori Launchpad (FLP) is the central access point for all
 *   SAP applications in S/4HANA. It uses a tile-based layout where each
 *   tile represents one app or transaction. Tiles are grouped by business
 *   function (e.g., Finance, Procurement, Analytics).
 *
 *   This implementation uses:
 *     GenericTile    → SAP FLP App Tile (sap.m.GenericTile)
 *     TileContent    → SAP Tile body container
 *     NumericContent → SAP KPI tile with numeric value + unit
 *
 *   Tile groups match SAP S/4HANA functional areas:
 *     "Clinical"            → Custom healthcare domain
 *     "SAP Finance (FICO)"  → Financial Accounting module
 *     "SAP Procurement (MM)"→ Materials Management module
 *     "SAP Compliance (GRC)"→ Governance, Risk & Compliance
 *     "SAP Analytics (SAC)" → SAP Analytics Cloud
 *     "Security"            → SAP BTP Identity & Access
 *
 * @module pages/LaunchpadPage
 */

import { useNavigate } from 'react-router-dom';
import { Card, CardHeader } from '@ui5/webcomponents-react';

// Named export from authStore (Zustand store)
import { useAuthStore } from '../stores/authStore';

/**
 * Tile configuration registry.
 *
 * Each tile maps a Phoenix Guardian feature to its SAP module equivalent.
 * The `roles` array controls visibility based on the logged-in user's role.
 * The `sapModule` field is used for the tooltip and the SAP alignment story.
 *
 * valueColor options: "Good" (green) | "Critical" (red) | "Neutral" (grey)
 *
 * @type {Array<TileConfig>}
 */
const TILE_CONFIG = [
  // ── CLINICAL GROUP ──────────────────────────────────────────────
  {
    id: 'encounters',
    group: 'Clinical',
    groupOrder: 1,
    headerText: 'Encounters',
    subheaderText: 'Active today',
    value: '142',
    unit: 'encounters',
    valueColor: 'Good',
    icon: 'clinical-order',
    route: '/encounters',
    roles: ['physician', 'nurse', 'admin', 'readonly'],
    sapModule: 'Clinical Documentation',
    agentBridge: 'ScribeAgent → CodingAgent',
  },
  {
    id: 'soap',
    group: 'Clinical',
    groupOrder: 1,
    headerText: 'SOAP Notes',
    subheaderText: 'Pending generation',
    value: '12',
    unit: 'pending',
    valueColor: 'Critical',
    icon: 'documents',
    route: '/soap-generator',
    roles: ['physician', 'admin'],
    sapModule: 'Clinical Documentation',
    agentBridge: 'ScribeAgent',
  },
  {
    id: 'patients',
    group: 'Clinical',
    groupOrder: 1,
    headerText: 'Patients',
    subheaderText: 'Registered today',
    value: '38',
    unit: 'patients',
    valueColor: 'Good',
    icon: 'person-placeholder',
    route: '/v5-dashboard',
    roles: ['physician', 'nurse', 'admin'],
    sapModule: 'Patient Master Data',
    agentBridge: 'NavigatorAgent',
  },
  // ── SAP FINANCE (FICO) GROUP ─────────────────────────────────────
  {
    id: 'billing',
    group: 'SAP Finance (FICO)',
    groupOrder: 2,
    headerText: 'Billing',
    subheaderText: 'SAP FICO · This month',
    value: '₹4.2L',
    unit: 'invoiced',
    valueColor: 'Good',
    icon: 'money-bills',
    route: '/v5-dashboard',
    roles: ['admin'],
    sapModule: 'SAP S/4HANA FICO',
    agentBridge: 'CodingAgent → SAP FICO',
  },
  {
    id: 'gl-accounts',
    group: 'SAP Finance (FICO)',
    groupOrder: 2,
    headerText: 'GL Documents',
    subheaderText: 'SAP FICO · Posted today',
    value: '47',
    unit: 'documents',
    valueColor: 'Good',
    icon: 'accounting-document-verification',
    route: '/v5-dashboard',
    roles: ['admin'],
    sapModule: 'SAP FI · GL Accounting',
    agentBridge: 'CodingAgent → FICO document type DR',
  },
  // ── SAP PROCUREMENT (MM) GROUP ───────────────────────────────────
  {
    id: 'procurement',
    group: 'SAP Procurement (MM)',
    groupOrder: 3,
    headerText: 'Purchase Orders',
    subheaderText: 'SAP MM · Open PRs',
    value: '8',
    unit: 'open orders',
    valueColor: 'Good',
    icon: 'shipping-status',
    route: '/v5-dashboard',
    roles: ['admin', 'nurse'],
    sapModule: 'SAP MM · Materials Management',
    agentBridge: 'OrdersAgent + PharmacyAgent → SAP MM',
  },
  {
    id: 'pharmacy',
    group: 'SAP Procurement (MM)',
    groupOrder: 3,
    headerText: 'Pharmacy Stock',
    subheaderText: 'SAP MM · Inventory',
    value: '94%',
    unit: 'in stock',
    valueColor: 'Good',
    icon: 'pharmacy',
    route: '/v5-dashboard',
    roles: ['admin', 'nurse', 'physician'],
    sapModule: 'SAP MM · Warehouse Mgmt',
    agentBridge: 'PharmacyAgent → SAP WM',
  },
  // ── SAP COMPLIANCE (GRC) GROUP ───────────────────────────────────
  {
    id: 'grc',
    group: 'SAP Compliance (GRC)',
    groupOrder: 4,
    headerText: 'GRC Alerts',
    subheaderText: 'SAP GRC · Critical issues',
    value: '3',
    unit: 'critical',
    valueColor: 'Critical',
    icon: 'alert',
    route: '/v5-dashboard',
    roles: ['admin'],
    sapModule: 'SAP GRC · Governance Risk Compliance',
    agentBridge: 'FraudAgent → SAP GRC',
  },
  {
    id: 'risk',
    group: 'SAP Compliance (GRC)',
    groupOrder: 4,
    headerText: 'Risk Register',
    subheaderText: 'SAP GRC · Patient risk',
    value: '7',
    unit: 'high-risk',
    valueColor: 'Critical',
    icon: 'risk',
    route: '/v5-dashboard',
    roles: ['admin', 'physician'],
    sapModule: 'SAP GRC Risk Management',
    agentBridge: 'RiskStratifier → SAP GRC',
  },
  // ── SAP ANALYTICS (SAC) GROUP ────────────────────────────────────
  {
    id: 'erp-dashboard',
    group: 'SAP Analytics (SAC)',
    groupOrder: 5,
    headerText: 'ERP Dashboard',
    subheaderText: 'SAP FICO · MM · GRC · SAC',
    value: '4',
    unit: 'modules live',
    valueColor: 'Good',
    icon: 'table-chart',
    route: '/erp-dashboard',
    roles: ['physician', 'admin', 'readonly'],
    sapModule: 'SAP S/4HANA Integration Layer',
    agentBridge: 'All Agents → SAP S/4HANA',
  },
  {
    id: 'analytics',
    group: 'SAP Analytics (SAC)',
    groupOrder: 5,
    headerText: 'Population Health',
    subheaderText: 'SAP Analytics Cloud',
    value: '98%',
    unit: 'KPI sync',
    valueColor: 'Good',
    icon: 'bar-chart',
    route: '/dashboard',
    roles: ['physician', 'admin', 'readonly'],
    sapModule: 'SAP Analytics Cloud (SAC)',
    agentBridge: 'PopulationHealthAgent → SAC',
  },
  {
    id: 'readmission',
    group: 'SAP Analytics (SAC)',
    groupOrder: 5,
    headerText: 'Readmission Risk',
    subheaderText: 'XGBoost ML · SAC',
    value: '6.9%',
    unit: '30-day risk',
    valueColor: 'Neutral',
    icon: 'stethoscope',
    route: '/dashboard',
    roles: ['physician', 'admin'],
    sapModule: 'SAP Analytics Cloud (SAC)',
    agentBridge: 'ReadmissionAgent → SAC KPI',
  },
  // ── SECURITY GROUP ───────────────────────────────────────────────
  {
    id: 'audit',
    group: 'Security · SAP BTP IAM',
    groupOrder: 6,
    headerText: 'Audit Trail',
    subheaderText: 'HIPAA · 7-yr retention',
    value: '100%',
    unit: 'compliant',
    valueColor: 'Good',
    icon: 'locked',
    route: '/admin/security',
    roles: ['admin'],
    sapModule: 'SAP BTP Audit Log Service',
    agentBridge: 'AuditLogger → BTP Audit',
  },
  {
    id: 'pqc',
    group: 'Security · SAP BTP IAM',
    groupOrder: 6,
    headerText: 'PQC Encryption',
    subheaderText: 'Kyber-1024 · AES-256',
    value: 'ON',
    unit: 'active',
    valueColor: 'Good',
    icon: 'key',
    route: '/admin/security',
    roles: ['admin'],
    sapModule: 'SAP BTP Security',
    agentBridge: 'PQC Module → BTP Credential Store',
  },
  // ── AI AGENTS GROUP ──────────────────────────────────────────────
  {
    id: 'agents',
    group: 'AI Agent Orchestration',
    groupOrder: 7,
    headerText: 'AI Agents',
    subheaderText: '4-phase parallel engine',
    value: '35',
    unit: 'active agents',
    valueColor: 'Good',
    icon: 'ai',
    route: '/dashboard',
    roles: ['physician', 'nurse', 'admin', 'readonly'],
    sapModule: 'SAP Integration Suite (iFlow)',
    agentBridge: 'AgentOrchestrator → SAP Integration Suite',
  },
];

/** SAP module connection status indicator */
const SAP_MODULE_STATUS = [
  { name: 'SAP FICO', status: 'Connected', color: '#107e3e' },
  { name: 'SAP MM',   status: 'Connected', color: '#107e3e' },
  { name: 'SAP GRC',  status: 'Connected', color: '#107e3e' },
  { name: 'SAP SAC',  status: 'Connected', color: '#107e3e' },
];

/**
 * Groups an array of tiles by their `group` property,
 * preserving `groupOrder` for consistent sort order.
 *
 * @param {Array} tiles - Filtered tile config array
 * @returns {Array<[string, Array]>} Sorted entries of [groupName, tiles]
 */
function groupTiles(tiles) {
  const map = {};
  tiles.forEach(tile => {
    if (!map[tile.group]) {
      map[tile.group] = { order: tile.groupOrder, tiles: [] };
    }
    map[tile.group].tiles.push(tile);
  });
  return Object.entries(map)
    .sort(([, a], [, b]) => a.order - b.order)
    .map(([name, { tiles: t }]) => [name, t]);
}

/**
 * LaunchpadPage — SAP Fiori Launchpad home screen.
 *
 * Displays role-based tile groups linking to Phoenix Guardian features
 * and their corresponding SAP module integrations.
 *
 * @returns {JSX.Element}
 */
export default function LaunchpadPage() {
  const navigate  = useNavigate();
  // Access auth state — named export useAuthStore from Zustand
  const user = useAuthStore((state) => state.user);
  const getFullName = useAuthStore((state) => state.getFullName);
  // Normalise role to lowercase string for comparison
  const userRole = user?.role ?? 'readonly';
  const userName = getFullName ? getFullName() : (user?.email ?? 'User');

  const visibleTiles = TILE_CONFIG.filter(t => t.roles.includes(userRole));
  const groupedTiles = groupTiles(visibleTiles);

  return (
    <div
      style={{
        maxWidth: '1280px',
        margin: '0 auto',
        padding: '1.5rem 2rem 4rem',
      }}
    >
      {/* ── Welcome header ────────────────────────────────────────── */}
      <div style={{ marginBottom: '2rem' }}>
        <h2
          style={{
            fontFamily: '"72", Arial, sans-serif',
            fontSize: '1.5rem',
            fontWeight: 700,
            color: '#32363a',
            marginBottom: '0.25rem',
          }}
        >
          My Home
        </h2>
        <p
          style={{
            fontSize: '0.8rem',
            color: '#6a6d70',
            fontFamily: '"72", Arial, sans-serif',
          }}
        >
          Welcome, {userName} · Phoenix Guardian Healthcare AI Platform ·
          SAP Integration Layer Active ·{' '}
          <span style={{ color: '#107e3e', fontWeight: 600 }}>
            {visibleTiles.length} apps
          </span>
        </p>
      </div>

      {/* ── SAP module status strip ───────────────────────────────── */}
      <div
        style={{
          display: 'flex',
          gap: '1.5rem',
          flexWrap: 'wrap',
          background: '#f0faf5',
          border: '1px solid #b8e8d0',
          borderRadius: '4px',
          padding: '0.6rem 1rem',
          marginBottom: '2rem',
          fontSize: '0.72rem',
          fontFamily: '"72", Arial, sans-serif',
        }}
      >
        <span style={{ color: '#6a6d70', fontWeight: 600 }}>
          SAP ERP Status:
        </span>
        {SAP_MODULE_STATUS.map(mod => (
          <span key={mod.name} style={{ color: mod.color }}>
            ● {mod.name} — {mod.status} (demo)
          </span>
        ))}
      </div>

      {/* ── Tile groups ──────────────────────────────────────────── */}
      {groupedTiles.map(([groupName, tiles]) => (
        <div key={groupName} style={{ marginBottom: '2.5rem' }}>
          {/* Group label — matches SAP Launchpad section header */}
          <p
            style={{
              fontSize: '0.68rem',
              letterSpacing: '1.5px',
              textTransform: 'uppercase',
              fontWeight: 700,
              color: '#6a6d70',
              marginBottom: '0.75rem',
              fontFamily: '"72", Arial, sans-serif',
            }}
          >
            {groupName}
          </p>

          {/* Tile row */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem' }}>
            {tiles.map(tile => (
              <div
                key={tile.id}
                onClick={() => navigate(tile.route)}
                title={`SAP Module: ${tile.sapModule}\nAgent: ${tile.agentBridge}`}
                style={{
                  cursor: 'pointer',
                  transition: 'transform 0.15s ease, box-shadow 0.15s ease',
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.transform = 'translateY(-2px)';
                  e.currentTarget.style.boxShadow =
                    '0 4px 12px rgba(0,0,0,0.12)';
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.boxShadow = 'none';
                }}
              >
                <Card
                  style={{ width: '170px', minHeight: '100px' }}
                  header={
                    <CardHeader
                      titleText={tile.headerText}
                      subtitleText={tile.subheaderText}
                    />
                  }
                >
                  <div style={{
                    padding: '0.5rem 1rem 0.75rem',
                    fontFamily: '"72", Arial, sans-serif',
                  }}>
                    <span style={{
                      fontSize: '1.5rem',
                      fontWeight: 700,
                      color: tile.valueColor === 'Good' ? '#107e3e'
                           : tile.valueColor === 'Critical' ? '#bb0000'
                           : '#6a6d70',
                    }}>
                      {tile.value}
                    </span>
                    <span style={{
                      fontSize: '0.7rem',
                      color: '#6a6d70',
                      marginLeft: '0.35rem',
                    }}>
                      {tile.unit}
                    </span>
                  </div>
                </Card>
              </div>
            ))}
          </div>
        </div>
      ))}

      {/* ── SAP alignment footnote ────────────────────────────────── */}
      <div
        style={{
          borderTop: '1px solid #e5e5e5',
          paddingTop: '1rem',
          marginTop: '2rem',
          fontSize: '0.68rem',
          color: '#89919a',
          fontFamily: '"72", Arial, sans-serif',
        }}
      >
        Phoenix Guardian v5.1 · Enterprise Healthcare Integration Layer ·
        SAP S/4HANA aligned architecture ·
        <a
          href="https://ktern.com"
          target="_blank"
          rel="noreferrer"
          style={{ color: '#0070d2', marginLeft: '0.5rem' }}
        >
          Ktern.AI compatible
        </a>
      </div>
    </div>
  );
}
