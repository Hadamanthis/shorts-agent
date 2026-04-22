/**
 * video-renderer/src/ui/AppRouter.tsx
 *
 * Shell da interface de gestão com sidebar e navegação entre páginas.
 * Registrado em Root.tsx como <Composition id="UI" component={AppRouter} />.
 */

import React, { useState } from 'react';
import DashboardPage from './pages/DashboardPage';
import ConfigPage from './pages/ConfigPage';
import ShortsPage from './pages/ShortsPage';
import CurationPage from './pages/CurationPage';

// ── API helper ────────────────────────────────────────────────────────────────
export const API_BASE = 'http://localhost:8000';

export async function apiFetch(path: string, opts?: RequestInit) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  });
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`);
  return res.json();
}

// ── Types ─────────────────────────────────────────────────────────────────────
type Page = 'dashboard' | 'config' | 'shorts' | 'curation';

interface CurationConfig { topic: string; profile: string; }

const NAV: { id: Page; label: string; icon: string }[] = [
  { id: 'dashboard', label: 'Pipeline',   icon: '▶' },
  { id: 'config',    label: 'Configurar', icon: '⚙' },
  { id: 'shorts',    label: 'Shorts',     icon: '▣' },
];

// ── Component ─────────────────────────────────────────────────────────────────
export default function AppRouter() {
  const [page, setPage]           = useState<Page>('dashboard');
  const [curation, setCuration]   = useState<CurationConfig | null>(null);

  function goToCuration(topic: string, profile: string) {
    setCuration({ topic, profile });
    setPage('curation');
  }

  return (
    <div style={s.root}>
      <aside style={s.sidebar}>
        <div style={s.logo}>
          <span style={s.logoIcon}>⬡</span>
          <span style={s.logoText}>
            shorts<strong>agent</strong>
          </span>
        </div>

        <nav style={s.nav}>
          {NAV.map((n) => (
            <button
              key={n.id}
              style={{ ...s.navBtn, ...(page === n.id ? s.navActive : {}) }}
              onClick={() => setPage(n.id)}
            >
              <span style={s.navIcon}>{n.icon}</span>
              <span>{n.label}</span>
            </button>
          ))}
        </nav>

        <div style={s.sidebarFooter}>
          <span style={s.footerDot} />
          <span style={{ fontSize: 11, color: '#6b7280' }}>API :8000</span>
        </div>
      </aside>

      <main style={s.main}>
        {page === 'dashboard' && <DashboardPage onGoToCuration={goToCuration} />}
        {page === 'config'    && <ConfigPage />}
        {page === 'shorts'    && <ShortsPage />}
        {page === 'curation'  && curation && (
          <CurationPage
            initialTopic={curation.topic}
            profile={curation.profile}
            onBack={() => setPage('dashboard')}
          />
        )}
      </main>
    </div>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────
const s: Record<string, React.CSSProperties> = {
  root: {
    display: 'flex',
    width: '100%',
    height: '100%',
    fontFamily: "'Segoe UI', system-ui, sans-serif",
    background: '#0f1117',
    color: '#e5e7eb',
    overflow: 'hidden',
  },
  sidebar: {
    width: 200,
    background: '#161b27',
    borderRight: '1px solid #1f2937',
    display: 'flex',
    flexDirection: 'column',
    padding: '20px 12px',
    flexShrink: 0,
  },
  logo: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '4px 8px 20px',
    borderBottom: '1px solid #1f2937',
    marginBottom: 12,
  },
  logoIcon: { fontSize: 20, color: '#6366f1' },
  logoText:  { fontSize: 14, color: '#e5e7eb', letterSpacing: -0.3 },
  nav: { display: 'flex', flexDirection: 'column', gap: 2, flex: 1 },
  navBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    padding: '9px 10px',
    borderRadius: 8,
    border: 'none',
    background: 'transparent',
    color: '#9ca3af',
    fontSize: 13,
    cursor: 'pointer',
    textAlign: 'left',
  },
  navActive: { background: '#1e2535', color: '#e5e7eb' },
  navIcon: { fontSize: 13, width: 18, textAlign: 'center' },
  sidebarFooter: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    padding: '12px 8px 0',
    borderTop: '1px solid #1f2937',
  },
  footerDot: {
    width: 6,
    height: 6,
    borderRadius: '50%',
    background: '#22c55e',
  },
  main: {
    flex: 1,
    overflowY: 'auto',
    height: '100%',
  },
};