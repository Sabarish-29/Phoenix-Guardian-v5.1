/**
 * AppShell.jsx
 *
 * SAP Fiori ShellBar wrapper for Phoenix Guardian.
 *
 * SAP ALIGNMENT:
 *   The ShellBar is the mandatory top-level navigation component in
 *   all SAP Fiori applications. It follows SAP Fiori Design Guideline
 *   FD-3.1: "Every Fiori app must have a ShellBar as the global header."
 *   This implementation mirrors the S/4HANA Fiori Launchpad shell.
 *
 *   Component mappings:
 *     ShellBar         → SAP Fiori Shell (flp.ShellBar)
 *     ShellBarItem     → SAP Fiori Navigation Item
 *     Avatar           → SAP BTP User Profile
 *     notificationsCount → SAP Fiori Notification Badge
 *
 * @module components/AppShell
 */

import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ShellBar,
  ShellBarItem,
  Avatar,
} from '@ui5/webcomponents-react';

// IMPORTANT: These Assets imports register all UI5 icons and themes.
// They must be imported exactly once in the app — importing here is correct
// because AppShell wraps the entire application.
import '@ui5/webcomponents-fiori/dist/Assets.js';
import '@ui5/webcomponents-react/dist/Assets.js';
import '@ui5/webcomponents/dist/Assets.js';

// Named export from authStore (Zustand store)
import { useAuthStore } from '../stores/authStore';

/**
 * Get two-letter initials from a user's first and last name.
 * Falls back to 'PG' (Phoenix Guardian) if names are unavailable.
 */
function getInitials(firstName, lastName) {
  const first = firstName && typeof firstName === 'string' ? firstName.trim() : '';
  const last = lastName && typeof lastName === 'string' ? lastName.trim() : '';
  if (first && last) return (first[0] + last[0]).toUpperCase();
  if (first) return first.slice(0, 2).toUpperCase();
  return 'PG';
}

/* ── SAP-themed notification data ──────────────────────────────── */
const NOTIFICATIONS = [
  {
    id: 1,
    type: 'SAP',
    title: 'SAP FICO — Billing posted',
    message: 'Document FI-5100000089 created successfully',
    time: '2 min ago',
    color: '#107e3e',
  },
  {
    id: 2,
    type: 'SECURITY',
    title: 'Threat blocked',
    message: 'CRITICAL SQL_INJECTION blocked by SentinelAgent',
    time: '5 min ago',
    color: '#bb0000',
  },
  {
    id: 3,
    type: 'SAP',
    title: 'GRC Alert raised',
    message: 'HIGH risk: NCCI unbundling — GRC-ISSUE-00029',
    time: '8 min ago',
    color: '#e76500',
  },
];

/* ── App-switcher grid items ──────────────────────────────────── */
const SAP_APPS = [
  { name: 'ERP Dashboard', icon: '\uD83D\uDCCA', path: '/erp-dashboard', color: '#107e3e', desc: 'FICO·MM·GRC·SAC' },
  { name: 'SAP Launchpad', icon: '\uD83D\uDE80', path: '/launchpad',     color: '#0070f2', desc: 'Fiori Tiles' },
  { name: 'Admin Console', icon: '\uD83D\uDEE1\uFE0F', path: '/admin',          color: '#bb0000', desc: 'Security' },
  { name: 'Encounters',    icon: '\uD83C\uDFE5', path: '/encounters',    color: '#6366f1', desc: 'Clinical' },
  { name: 'Dashboard',     icon: '\uD83C\uDFE0', path: '/dashboard',     color: '#374151', desc: 'Home' },
  { name: 'Security',      icon: '\uD83D\uDD12', path: '/admin/security',color: '#f59e0b', desc: 'Threats' },
];

/**
 * AppShell — Fiori ShellBar wrapper component.
 *
 * Renders the SAP Fiori global header above all page content.
 * Provides app-level navigation matching SAP Fiori Launchpad patterns.
 *
 * @param {object}           props
 * @param {React.ReactNode}  props.children  Page content to render below the shell
 * @returns {JSX.Element}
 */
export default function AppShell({ children }) {
  const navigate = useNavigate();

  // Access auth state — named export useAuthStore from Zustand
  const user = useAuthStore((state) => state.user);
  const userName = user
    ? `${user.firstName ?? ''} ${user.lastName ?? ''}`.trim() || user.email
    : null;

  const initials = getInitials(user?.firstName, user?.lastName);

  // ── Notification panel state ──────────────────────────────────
  const [showNotifications, setShowNotifications] = useState(false);
  const notifRef = useRef(null);

  // ── App-switcher state ────────────────────────────────────────
  const [showAppSwitcher, setShowAppSwitcher] = useState(false);
  const switcherRef = useRef(null);

  // Close dropdowns when clicking outside
  useEffect(() => {
    function handleClickOutside(e) {
      if (notifRef.current && !notifRef.current.contains(e.target)) {
        setShowNotifications(false);
      }
      if (switcherRef.current && !switcherRef.current.contains(e.target)) {
        setShowAppSwitcher(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        minHeight: '100vh',
        fontFamily: '"72", "72full", Arial, Helvetica, sans-serif',
      }}
    >
      {/* ── SAP Fiori ShellBar ─────────────────────────────────────── */}
      <ShellBar
        primaryTitle="Phoenix Guardian"
        secondaryTitle="Healthcare AI · SAP Integration Platform"
        notificationsCount="3"
        showNotifications
        showProductSwitch
        onNotificationsClick={() => {
          setShowNotifications((v) => !v);
          setShowAppSwitcher(false);
        }}
        onProductSwitchClick={() => {
          setShowAppSwitcher((v) => !v);
          setShowNotifications(false);
        }}
        profile={
          <Avatar
            initials={initials}
            colorScheme="Accent6"
            size="XS"
            aria-label={`User: ${userName ?? 'Unknown'}`}
          />
        }
        onLogoClick={() => navigate('/launchpad')}
        style={{ position: 'sticky', top: 0, zIndex: 100 }}
      >
        {/* SAP Fiori Navigation Items — mirror S/4HANA app tiles */}
        <ShellBarItem
          icon="home"
          text="Launchpad"
          onClick={() => navigate('/launchpad')}
        />
        <ShellBarItem
          icon="clinical-order"
          text="Encounters"
          onClick={() => navigate('/encounters')}
        />
        <ShellBarItem
          icon="money-bills"
          text="ERP Finance"
          onClick={() => navigate('/erp-dashboard')}
        />
        <ShellBarItem
          icon="process"
          text="Integrations"
          onClick={() => navigate('/erp-dashboard')}
        />
        <ShellBarItem
          icon="activity-2"
          text="Analytics"
          onClick={() => navigate('/dashboard')}
        />
      </ShellBar>

      {/* ── Notification dropdown ──────────────────────────────────── */}
      {showNotifications && (
        <div
          ref={notifRef}
          style={{
            position: 'fixed',
            top: 44,
            right: 80,
            width: 340,
            backgroundColor: '#1e2736',
            border: '1px solid #374151',
            borderRadius: 8,
            boxShadow: '0 10px 25px rgba(0,0,0,0.5)',
            zIndex: 1001,
            overflow: 'hidden',
          }}
        >
          <div style={{
            padding: '12px 16px',
            borderBottom: '1px solid #374151',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <span style={{ color: '#f9fafb', fontWeight: 600, fontSize: 14 }}>Notifications</span>
            <span style={{ color: '#6b7280', fontSize: 12 }}>3 unread</span>
          </div>
          {NOTIFICATIONS.map((n) => (
            <div
              key={n.id}
              style={{
                padding: '12px 16px',
                borderBottom: '1px solid #1f2937',
                backgroundColor: 'rgba(255,255,255,0.03)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{
                  backgroundColor: n.color,
                  color: 'white',
                  fontSize: 10,
                  padding: '2px 6px',
                  borderRadius: 4,
                  fontWeight: 700,
                }}>{n.type}</span>
                <span style={{ color: '#f9fafb', fontSize: 13, fontWeight: 500 }}>{n.title}</span>
              </div>
              <p style={{ color: '#9ca3af', fontSize: 12, margin: '4px 0 2px 0' }}>{n.message}</p>
              <span style={{ color: '#6b7280', fontSize: 11 }}>{n.time}</span>
            </div>
          ))}
          <div style={{ padding: '10px 16px', textAlign: 'center' }}>
            <span
              style={{ color: '#60a5fa', fontSize: 13, cursor: 'pointer' }}
              onClick={() => {
                navigate('/admin/security');
                setShowNotifications(false);
              }}
            >
              View all notifications →
            </span>
          </div>
        </div>
      )}

      {/* ── App-switcher dropdown ──────────────────────────────────── */}
      {showAppSwitcher && (
        <div
          ref={switcherRef}
          style={{
            position: 'fixed',
            top: 44,
            right: 16,
            width: 296,
            backgroundColor: '#1e2736',
            border: '1px solid #374151',
            borderRadius: 8,
            boxShadow: '0 10px 25px rgba(0,0,0,0.5)',
            zIndex: 1001,
            padding: 12,
          }}
        >
          <div style={{ marginBottom: 10, padding: '0 4px' }}>
            <span style={{
              color: '#9ca3af',
              fontSize: 12,
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}>
              Phoenix Guardian Apps
            </span>
          </div>
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: 8,
          }}>
            {SAP_APPS.map((app) => (
              <div
                key={app.path}
                onClick={() => {
                  navigate(app.path);
                  setShowAppSwitcher(false);
                }}
                style={{
                  padding: 12,
                  backgroundColor: '#111827',
                  borderRadius: 6,
                  cursor: 'pointer',
                  border: '1px solid transparent',
                  textAlign: 'center',
                  transition: 'border-color 0.2s',
                }}
                onMouseEnter={(e) => { e.currentTarget.style.borderColor = app.color; }}
                onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'transparent'; }}
              >
                <div style={{ fontSize: 24, marginBottom: 4 }}>{app.icon}</div>
                <div style={{ color: '#f9fafb', fontSize: 12, fontWeight: 600 }}>{app.name}</div>
                <div style={{ color: '#6b7280', fontSize: 10 }}>{app.desc}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Page content area ────────────────────────────────────── */}
      <main
        style={{
          flex: 1,
          backgroundColor: '#f5f6f7',  // SAP Fiori background color
          overflow: 'auto',
        }}
        onClick={() => {
          setShowNotifications(false);
          setShowAppSwitcher(false);
        }}
      >
        {children}
      </main>
    </div>
  );
}
