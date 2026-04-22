/**
 * video-renderer/src/ui/pages/ConfigPage.tsx
 *
 * Página 2 — Editar config.yaml e perfis de canal via API.
 *
 * Abas:
 *   Conteúdo  → tom padrão, tamanho do hook, tamanho do comentário
 *   Reddit    → subreddit, listing, score mínimo, limites de clip
 *   Perfis    → criar e deletar perfis de canal
 */

import React, { useEffect, useState } from 'react';
import { apiFetch } from '../AppRouter';

type Tab = 'content' | 'reddit' | 'profiles';

interface Profile {
  language: string;
  niche: string;
  account_name: string;
  avatar_path: string;
  background_video: string;
  music_path: string;
}

export default function ConfigPage() {
  const [tab,    setTab]    = useState<Tab>('content');
  const [config, setConfig] = useState<any>(null);
  const [saving, setSaving] = useState(false);
  const [saved,  setSaved]  = useState(false);
  const [error,  setError]  = useState('');

  useEffect(() => {
    apiFetch('/config').then(setConfig).catch(() =>
      setError('API offline. Inicie o servidor: uvicorn api:app --reload --port 8000')
    );
  }, []);

  async function save(patch: object) {
    setSaving(true);
    setSaved(false);
    try {
      const res = await apiFetch('/config', { method: 'PATCH', body: JSON.stringify(patch) });
      setConfig(res.config);
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch {
      setError('Erro ao salvar. Verifique se a API está rodando.');
    } finally {
      setSaving(false);
    }
  }

  if (error) return <Offline message={error} />;
  if (!config) return <Loading />;

  return (
    <div style={s.page}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <h1 style={s.pageTitle}>Configurar</h1>
        {saved && <span style={s.savedBadge}>✓ Salvo</span>}
      </div>

      <div style={s.tabs}>
        {(['content', 'reddit', 'profiles'] as Tab[]).map(t => (
          <button
            key={t}
            style={{ ...s.tabBtn, ...(tab === t ? s.tabActive : {}) }}
            onClick={() => setTab(t)}
          >
            {{ content: 'Conteúdo', reddit: 'Reddit', profiles: 'Perfis' }[t]}
          </button>
        ))}
      </div>

      {tab === 'content'  && <ContentTab  config={config} onSave={c => save({ content: c })} saving={saving} />}
      {tab === 'reddit'   && <RedditTab   config={config} onSave={c => save({ reddit: c })}  saving={saving} />}
      {tab === 'profiles' && <ProfilesTab onRefresh={() => apiFetch('/config').then(setConfig)} />}
    </div>
  );
}

// ── Aba: Conteúdo ─────────────────────────────────────────────────────────────
function ContentTab({ config, onSave, saving }: { config: any; onSave: (c: any) => void; saving: boolean }) {
  const [form, setForm] = useState({ ...config.content });
  const upd = (k: string, v: any) => setForm((f: any) => ({ ...f, [k]: v }));

  return (
    <div style={s.tabPanel}>
      <Field label="Tom padrão do comentário" hint="Usado quando --comment-tone não é passado na CLI">
        <select style={s.select} value={form.comment_tone} onChange={e => upd('comment_tone', e.target.value)}>
          {['surpreso', 'humoristico', 'reflexivo', 'emocional'].map(t => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
      </Field>

      <Field label="Tamanho máximo do hook (zona 1)" hint={`${form.curiosity_max_chars} caracteres`}>
        <div style={s.rangeRow}>
          <input type="range" min={60} max={200} step={5} style={s.range}
            value={form.curiosity_max_chars} onChange={e => upd('curiosity_max_chars', Number(e.target.value))} />
          <span style={s.rangeVal}>{form.curiosity_max_chars}</span>
        </div>
      </Field>

      <Field label="Tamanho máximo do comentário (zona 3)" hint={`${form.comment_max_chars} caracteres`}>
        <div style={s.rangeRow}>
          <input type="range" min={80} max={400} step={10} style={s.range}
            value={form.comment_max_chars} onChange={e => upd('comment_max_chars', Number(e.target.value))} />
          <span style={s.rangeVal}>{form.comment_max_chars}</span>
        </div>
      </Field>

      <SaveButton saving={saving} onClick={() => onSave(form)} />
    </div>
  );
}

// ── Aba: Reddit ───────────────────────────────────────────────────────────────
function RedditTab({ config, onSave, saving }: { config: any; onSave: (c: any) => void; saving: boolean }) {
  const [form, setForm] = useState({ ...config['comentario-reddit'] });
  const upd = (k: string, v: any) => setForm((f: any) => ({ ...f, [k]: v }));

  return (
    <div style={s.tabPanel}>
      <Field label="Subreddit padrão">
        <input style={s.input} value={form.subreddit} onChange={e => upd('subreddit', e.target.value)} />
      </Field>

      <Field label="Tipo de listing">
        <select style={s.select} value={form.listing} onChange={e => upd('listing', e.target.value)}>
          {['hot', 'top', 'rising'].map(l => <option key={l} value={l}>{l}</option>)}
        </select>
      </Field>

      <Field label="Filtro de tempo (só para listing = top)">
        <select style={s.select} value={form.time_filter} onChange={e => upd('time_filter', e.target.value)}>
          {['hour', 'day', 'week', 'month', 'year', 'all'].map(l => <option key={l} value={l}>{l}</option>)}
        </select>
      </Field>

      <Field label="Score mínimo do post" hint={String(form.min_score)}>
        <div style={s.rangeRow}>
          <input type="range" min={0} max={10000} step={100} style={s.range}
            value={form.min_score} onChange={e => upd('min_score', Number(e.target.value))} />
          <span style={s.rangeVal}>{form.min_score}</span>
        </div>
      </Field>

      <Field label="Posts buscados do Reddit" hint={`${form.fetch_limit} posts`}>
        <div style={s.rangeRow}>
          <input type="range" min={10} max={100} step={5} style={s.range}
            value={form.fetch_limit} onChange={e => upd('fetch_limit', Number(e.target.value))} />
          <span style={s.rangeVal}>{form.fetch_limit}</span>
        </div>
      </Field>

      <Field label="Comentários para contexto do LLM" hint={`${form.max_comments} comentários`}>
        <div style={s.rangeRow}>
          <input type="range" min={3} max={30} step={1} style={s.range}
            value={form.max_comments} onChange={e => upd('max_comments', Number(e.target.value))} />
          <span style={s.rangeVal}>{form.max_comments}</span>
        </div>
      </Field>

      <Field label="Duração máxima do vídeo aceito" hint={`${form.max_post_duration}s`}>
        <div style={s.rangeRow}>
          <input type="range" min={15} max={600} step={15} style={s.range}
            value={form.max_post_duration} onChange={e => upd('max_post_duration', Number(e.target.value))} />
          <span style={s.rangeVal}>{form.max_post_duration}s</span>
        </div>
      </Field>

      <Field label="Duração máxima do clip recortado" hint={`${form.max_clip_duration}s`}>
        <div style={s.rangeRow}>
          <input type="range" min={5} max={60} step={5} style={s.range}
            value={form.max_clip_duration} onChange={e => upd('max_clip_duration', Number(e.target.value))} />
          <span style={s.rangeVal}>{form.max_clip_duration}s</span>
        </div>
      </Field>

      <SaveButton saving={saving} onClick={() => onSave(form)} label="Salvar configurações Reddit" />
    </div>
  );
}

// ── Aba: Perfis ───────────────────────────────────────────────────────────────
function ProfilesTab({ onRefresh }: { onRefresh: () => void }) {
  const [profiles, setProfiles] = useState<Record<string, Profile>>({});
  const [creating, setCreating] = useState(false);
  const blank = { name: '', language: 'pt-BR', niche: '', account_name: '',
                  avatar_path: 'assets/profiles/synthvator.png',
                  background_video: 'assets/backgrounds/bg_default.mp4',
                  music_path: 'assets/music/bg_music.mp3' };
  const [form, setForm] = useState(blank);

  useEffect(() => { apiFetch('/profiles').then(setProfiles).catch(() => {}); }, []);

  const upd = (k: string, v: string) => setForm(f => ({ ...f, [k]: v }));

  async function create() {
    if (!form.name || !form.niche) return;
    await apiFetch('/profiles', { method: 'POST', body: JSON.stringify(form) });
    const p = await apiFetch('/profiles');
    setProfiles(p);
    setCreating(false);
    setForm(blank);
    onRefresh();
  }

  async function remove(name: string) {
    if (!confirm(`Deletar perfil "${name}"?`)) return;
    await apiFetch(`/profiles/${name}`, { method: 'DELETE' });
    const p = await apiFetch('/profiles');
    setProfiles(p);
    onRefresh();
  }

  return (
    <div style={s.tabPanel}>
      {Object.entries(profiles).map(([name, p]) => (
        <div key={name} style={s.profileCard}>
          <div style={s.profileAvatar}>{name[0].toUpperCase()}</div>
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={s.profileName}>{name}</span>
              <span style={s.langBadge}>{p.language}</span>
            </div>
            <div style={s.profileSub}>{p.niche} · @{p.account_name}</div>
          </div>
          <button style={s.btnDelete} onClick={() => remove(name)}>✕</button>
        </div>
      ))}

      {!creating ? (
        <button style={s.btnNew} onClick={() => setCreating(true)}>+ Novo perfil</button>
      ) : (
        <div style={s.createBox}>
          <p style={s.createTitle}>Novo perfil</p>
          {[
            { k: 'name',         l: 'Nome do perfil',      ph: 'MeuCanal' },
            { k: 'niche',        l: 'Nicho',               ph: 'filmes e séries' },
            { k: 'account_name', l: '@ do canal',          ph: 'meucanal' },
            { k: 'avatar_path',  l: 'Caminho do avatar',   ph: 'assets/profiles/avatar.png' },
          ].map(f => (
            <div key={f.k} style={{ marginBottom: 10 }}>
              <label style={s.label}>{f.l}</label>
              <input style={s.input} value={(form as any)[f.k]}
                onChange={e => upd(f.k, e.target.value)} placeholder={f.ph} />
            </div>
          ))}
          <div style={{ marginBottom: 10 }}>
            <label style={s.label}>Idioma</label>
            <select style={s.select} value={form.language} onChange={e => upd('language', e.target.value)}>
              <option value="pt-BR">pt-BR</option>
              <option value="en-US">en-US</option>
              <option value="es-ES">es-ES</option>
            </select>
          </div>
          <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
            <button style={s.btnSave}   onClick={create}>Criar</button>
            <button style={s.btnCancel} onClick={() => { setCreating(false); setForm(blank); }}>Cancelar</button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Shared sub-components ─────────────────────────────────────────────────────
function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 18 }}>
      <div style={{ marginBottom: 6 }}>
        <label style={s.label}>{label}</label>
        {hint && <span style={s.hint}> — {hint}</span>}
      </div>
      {children}
    </div>
  );
}

function SaveButton({ saving, onClick, label = 'Salvar' }: { saving: boolean; onClick: () => void; label?: string }) {
  return (
    <button
      style={{ ...s.btnSave, ...(saving ? s.btnDisabled : {}), marginTop: 8, width: 'auto', padding: '9px 24px' }}
      onClick={onClick}
      disabled={saving}
    >
      {saving ? 'Salvando...' : label}
    </button>
  );
}

function Loading() {
  return <div style={{ padding: 40, color: '#6b7280' }}>Carregando configurações...</div>;
}

function Offline({ message }: { message: string }) {
  return (
    <div style={{ padding: 40 }}>
      <div style={{ background: '#1f0a0a', border: '1px solid #7f1d1d', borderRadius: 10, padding: '16px 20px', color: '#fca5a5', fontSize: 13 }}>
        ⚠ {message}
      </div>
    </div>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────
const s: Record<string, React.CSSProperties> = {
  page:      { padding: '28px 32px', boxSizing: 'border-box' },
  pageTitle: { fontSize: 22, fontWeight: 600, color: '#f3f4f6', margin: 0 },
  savedBadge: { fontSize: 12, color: '#22c55e', background: '#052e16', padding: '4px 12px', borderRadius: 20, border: '1px solid #166534' },
  tabs:    { display: 'flex', gap: 4, marginBottom: 20, background: '#161b27', borderRadius: 10, padding: 4, width: 'fit-content' },
  tabBtn:  { padding: '7px 18px', borderRadius: 7, border: 'none', background: 'transparent', color: '#9ca3af', fontSize: 13, cursor: 'pointer' },
  tabActive: { background: '#1f2937', color: '#e5e7eb' },
  tabPanel:  { background: '#161b27', border: '1px solid #1f2937', borderRadius: 12, padding: '22px 26px', maxWidth: 600 },
  label: { fontSize: 13, color: '#d1d5db', fontWeight: 500 },
  hint:  { fontSize: 12, color: '#6b7280' },
  input: { width: '100%', background: '#0f1117', border: '1px solid #374151', borderRadius: 7, padding: '8px 10px', color: '#e5e7eb', fontSize: 13, boxSizing: 'border-box' as const },
  select: { width: '100%', background: '#0f1117', border: '1px solid #374151', borderRadius: 7, padding: '8px 10px', color: '#e5e7eb', fontSize: 13 },
  rangeRow: { display: 'flex', alignItems: 'center', gap: 12 },
  range:    { flex: 1, accentColor: '#6366f1' },
  rangeVal: { fontSize: 13, color: '#a5b4fc', minWidth: 40, textAlign: 'right' as const },
  btnSave:   { padding: '9px 20px', background: '#6366f1', border: 'none', borderRadius: 8, color: 'white', fontSize: 13, fontWeight: 600, cursor: 'pointer' },
  btnCancel: { padding: '9px 20px', background: '#1f2937', border: '1px solid #374151', borderRadius: 8, color: '#d1d5db', fontSize: 13, cursor: 'pointer' },
  btnDisabled: { background: '#374151', cursor: 'not-allowed' },
  btnNew: { padding: '9px 18px', background: '#1f2937', border: '1px dashed #374151', borderRadius: 8, color: '#9ca3af', fontSize: 13, cursor: 'pointer', marginTop: 4 },
  profileCard: { display: 'flex', alignItems: 'center', gap: 12, background: '#0f1117', border: '1px solid #1f2937', borderRadius: 9, padding: '12px 14px', marginBottom: 8 },
  profileAvatar: { width: 36, height: 36, borderRadius: '50%', background: '#312e81', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14, fontWeight: 700, color: '#a5b4fc', flexShrink: 0 },
  profileName: { fontSize: 14, fontWeight: 600, color: '#e5e7eb' },
  profileSub:  { fontSize: 12, color: '#6b7280', marginTop: 2 },
  langBadge:   { fontSize: 10, color: '#6366f1', background: '#1e1b4b', padding: '2px 7px', borderRadius: 20 },
  btnDelete:   { background: 'transparent', border: 'none', color: '#4b5563', fontSize: 16, cursor: 'pointer', padding: 4 },
  createBox:   { background: '#0f1117', border: '1px solid #374151', borderRadius: 10, padding: '18px 20px', marginTop: 12 },
  createTitle: { fontSize: 14, fontWeight: 600, color: '#e5e7eb', marginBottom: 14 },
};