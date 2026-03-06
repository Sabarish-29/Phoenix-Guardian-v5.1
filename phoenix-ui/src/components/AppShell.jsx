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
 *
 * @param {string|null|undefined} firstName
 * @param {string|null|undefined} lastName
 * @returns {string} Two uppercase initials
 */
function getInitials(firstName, lastName) {
  const first = firstName && typeof firstName === 'string' ? firstName.trim() : '';
  const last = lastName && typeof lastName === 'string' ? lastName.trim() : '';
  if (first && last) return (first[0] + last[0]).toUpperCase();
  if (first) return first.slice(0, 2).toUpperCase();
  return 'PG';
}

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

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        minHeight: '100vh',
        fontFamily: '"72", "72full", Arial, Helvetica, sans-serif',
      }}
    >
      {/* ── SAP Fiori ShellBar ─────────────────────────────────────
          primaryTitle   = Application name (shown in shell)
          secondaryTitle = Subtitle (shown on wider screens)
          showNotifications + notificationsCount = SAP Fiori notification badge
          showProductSwitch = SAP "waffle" product switcher icon
          profile       = User avatar with initials (SAP BTP user profile)
      ────────────────────────────────────────────────────────────── */}
      <ShellBar
        primaryTitle="Phoenix Guardian"
        secondaryTitle="Healthcare AI · SAP Integration Platform"
        notificationsCount="3"
        showNotifications
        showProductSwitch
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

      {/* ── Page content area ────────────────────────────────────── */}
      <main
        style={{
          flex: 1,
          backgroundColor: '#f5f6f7',  // SAP Fiori background color
          overflow: 'auto',
        }}
      >
        {children}
      </main>
    </div>
  );
}
