/**
 * video-renderer/src/ui/pages/ShortsPage.tsx
 *
 * Página 3 — Galeria de shorts gerados em output/shorts/
 */

import React, { useEffect, useState } from 'react';
import { apiFetch } from '../AppRouter';

interface ShortFile {
  name: string;
  path: string;
  size_mb: number;
  created_at: string;
}

export default function ShortsPage() {
  const [shorts,  setShorts]  = useState<ShortFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [copied,  setCopied]  = useState<string | null>(null);
  const [error,   setError]   = useState('');

  async function load() {
    setLoading(true);
    setError('');
    try {
      const data = await apiFetch('/shorts');
      setShorts(data);
    } catch {
      setError('API offline. Inicie o servidor: uvicorn api:app --reload --port 8000');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  function copy(path: string) {
    navigator.clipboard.writeText(path);
    setCopied(path);
    setTimeout(() => setCopied(null), 1500);
  }

  async function openFolder(path: string) {
    try {
      await apiFetch('/open-folder', { method: 'POST', body: JSON.stringify({ path }) });
    } catch {
      copy(path);
      alert(`Endpoint /open-folder não disponível.\nCaminho copiado:\n${path}`);
    }
  }

  const totalMb = shorts.reduce((a, s) => a + s.size_mb, 0);

  return (
    <div style={s.page}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <h1 style={s.pageTitle}>Shorts gerados</h1>
        <button style={s.btnRefresh} onClick={load}>↻ Atualizar</button>
      </div>

      {error && (
        <div style={s.errorBox}>{error}</div>
      )}

      {loading && !error && <p style={{ color: '#6b7280' }}>Carregando...</p>}

      {!loading && !error && shorts.length === 0 && (
        <div style={s.empty}>
          <div style={s.emptyIcon}>▣</div>
          <p style={s.emptyTitle}>Nenhum short gerado ainda</p>
          <p style={s.emptyHint}>Vá para Pipeline e gere seu primeiro short.</p>
        </div>
      )}

      {!loading && shorts.length > 0 && (
        <>
          {/* Stats */}
          <div style={s.statsRow}>
            <Stat label="Total" value={String(shorts.length)} />
            <Stat label="Tamanho total" value={`${totalMb.toFixed(1)} MB`} />
            <Stat label="Mais recente" value={fmtDate(shorts[0].created_at)} />
          </div>

          {/* Grid */}
          <div style={s.grid}>
            {shorts.map(short => (
              <div key={short.name} style={s.card}>
                <div style={s.thumb}>
                  <span style={s.thumbPlay}>▶</span>
                  <span style={s.thumbLabel}>MP4</span>
                </div>
                <div style={s.cardBody}>
                  <p style={s.fileName} title={short.name}>{short.name}</p>
                  <div style={s.meta}>
                    <span style={s.metaItem}>{short.size_mb} MB</span>
                    <span style={s.metaDot}>·</span>
                    <span style={s.metaItem}>{fmtDate(short.created_at)}</span>
                  </div>
                  <div style={s.actions}>
                    <button style={s.btnCopy}   onClick={() => copy(short.path)}>
                      {copied === short.path ? '✓ Copiado' : '⎘ Caminho'}
                    </button>
                    <button style={s.btnFolder} onClick={() => openFolder(short.path)}>
                      ↗ Abrir pasta
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────
function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div style={s.statCard}>
      <span style={s.statLabel}>{label}</span>
      <span style={s.statValue}>{value}</span>
    </div>
  );
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleString('pt-BR', {
    day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit',
  });
}

// ── Styles ────────────────────────────────────────────────────────────────────
const s: Record<string, React.CSSProperties> = {
  page:      { padding: '28px 32px', boxSizing: 'border-box' },
  pageTitle: { fontSize: 22, fontWeight: 600, color: '#f3f4f6', margin: 0 },
  btnRefresh: { padding: '7px 14px', background: 'transparent', border: '1px solid #374151', borderRadius: 7, color: '#9ca3af', fontSize: 12, cursor: 'pointer' },
  errorBox:  { background: '#1f0a0a', border: '1px solid #7f1d1d', borderRadius: 10, padding: '14px 18px', color: '#fca5a5', fontSize: 13, marginBottom: 16 },
  statsRow:  { display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 24 },
  statCard:  { background: '#161b27', border: '1px solid #1f2937', borderRadius: 10, padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 4 },
  statLabel: { fontSize: 11, color: '#6b7280', textTransform: 'uppercase' as const, letterSpacing: 0.5 },
  statValue: { fontSize: 20, fontWeight: 600, color: '#f3f4f6' },
  grid:      { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(210px, 1fr))', gap: 14 },
  card:      { background: '#161b27', border: '1px solid #1f2937', borderRadius: 12, overflow: 'hidden' },
  thumb:     { height: 120, background: '#0a0d14', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 6, borderBottom: '1px solid #1f2937' },
  thumbPlay: { fontSize: 26, color: '#374151' },
  thumbLabel: { fontSize: 10, color: '#4b5563', letterSpacing: 1, textTransform: 'uppercase' as const },
  cardBody:  { padding: '12px 14px' },
  fileName:  { fontSize: 12, fontWeight: 600, color: '#d1d5db', whiteSpace: 'nowrap' as const, overflow: 'hidden', textOverflow: 'ellipsis', marginBottom: 4 },
  meta:      { display: 'flex', gap: 4, alignItems: 'center', marginBottom: 10 },
  metaItem:  { fontSize: 11, color: '#6b7280' },
  metaDot:   { fontSize: 11, color: '#374151' },
  actions:   { display: 'flex', gap: 6 },
  btnCopy:   { flex: 1, padding: '6px 0', fontSize: 11, background: 'transparent', border: '1px solid #374151', borderRadius: 6, color: '#9ca3af', cursor: 'pointer' },
  btnFolder: { flex: 1, padding: '6px 0', fontSize: 11, background: '#1e1b4b', border: '1px solid #4f46e5', borderRadius: 6, color: '#a5b4fc', cursor: 'pointer' },
  empty:     { display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '80px 0', gap: 8 },
  emptyIcon:  { fontSize: 40, color: '#1f2937' },
  emptyTitle: { fontSize: 16, color: '#4b5563', fontWeight: 500 },
  emptyHint:  { fontSize: 13, color: '#374151' },
};