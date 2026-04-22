/**
 * video-renderer/src/ui/pages/CurationPage.tsx
 *
 * Página de curadoria para o template "Did You Know?".
 *
 * Fluxo:
 *   1. Recebe tópico + perfil vindos do Dashboard
 *   2. Chama POST /dyk/generate → lista de fatos com candidatos de imagem
 *   3. Usuário edita texto de cada fato e escolhe uma imagem das candidatas
 *   4. Clica "Renderizar" → POST /dyk/render → polling do job
 */

import React, { useEffect, useRef, useState } from 'react';
import { apiFetch } from '../AppRouter';

// ── Types ─────────────────────────────────────────────────────────────────────
interface FactState {
  text: string;
  image_query: string;
  candidates: string[];
  chosen: string | null;
}

interface Job {
  status: 'running' | 'done' | 'error';
  log?: string[];
  finished_at?: string;
}

// ── Component ─────────────────────────────────────────────────────────────────
export default function CurationPage({
  initialTopic,
  profile,
  onBack,
}: {
  initialTopic: string;
  profile: string;
  onBack: () => void;
}) {
  const [topic, setTopic]   = useState(initialTopic);
  const [facts, setFacts]   = useState<FactState[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState('');

  const [activeJob, setActiveJob] = useState<Job | null>(null);
  const [running, setRunning]     = useState(false);
  const logRef  = useRef<HTMLDivElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Auto-gerar se tópico veio do Dashboard
  useEffect(() => {
    if (initialTopic) handleGenerate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [activeJob?.log?.length]);

  async function handleGenerate() {
    if (!topic.trim()) return;
    setLoading(true);
    setError('');
    setFacts([]);
    setActiveJob(null);
    try {
      const data = await apiFetch('/dyk/generate', {
        method: 'POST',
        body: JSON.stringify({ topic: topic.trim(), profile }),
      });
      setFacts(
        (data.facts as FactState[]).map(f => ({
          ...f,
          chosen: f.candidates[0] ?? null,
        }))
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  function startPolling(jobId: string) {
    pollRef.current = setInterval(async () => {
      try {
        const job: Job = await apiFetch(`/run/${jobId}`);
        setActiveJob(job);
        if (job.status !== 'running') {
          clearInterval(pollRef.current!);
          setRunning(false);
        }
      } catch {
        clearInterval(pollRef.current!);
        setRunning(false);
      }
    }, 800);
  }

  async function handleRender() {
    const missing = facts.findIndex(f => !f.chosen);
    if (missing !== -1) {
      alert(`Escolha uma imagem para o fato ${missing + 1} antes de renderizar.`);
      return;
    }
    setRunning(true);
    setActiveJob({ status: 'running', log: [] });
    try {
      const { job_id } = await apiFetch('/dyk/render', {
        method: 'POST',
        body: JSON.stringify({
          profile,
          facts: facts.map(f => ({ text: f.text, image_url: f.chosen })),
        }),
      });
      startPolling(job_id);
    } catch (e) {
      alert(e instanceof Error ? e.message : String(e));
      setRunning(false);
      setActiveJob(null);
    }
  }

  const allChosen = facts.length > 0 && facts.every(f => f.chosen);
  const isDone    = activeJob?.status === 'done';

  return (
    <div style={s.page}>
      {/* Header */}
      <div style={s.header}>
        <button style={s.backBtn} onClick={onBack}>← Voltar</button>
        <h1 style={s.title}>Did You Know? — Curadoria</h1>
        <span style={{ color: '#6b7280', fontSize: 13 }}>Perfil: <strong style={{ color: '#e5e7eb' }}>{profile}</strong></span>
      </div>

      {/* Topic input */}
      <div style={s.topicRow}>
        <input
          style={s.topicInput}
          value={topic}
          onChange={e => setTopic(e.target.value)}
          placeholder="Ex: Oceano, Roma Antiga, Inteligência Artificial..."
          onKeyDown={e => e.key === 'Enter' && !loading && handleGenerate()}
        />
        <button
          style={{ ...s.btnGenerate, ...(loading ? s.btnDisabled : {}) }}
          onClick={handleGenerate}
          disabled={loading}
        >
          {loading ? '⟳  Gerando fatos...' : '✦  Gerar fatos'}
        </button>
      </div>

      {error && <div style={s.errorBox}>{error}</div>}

      {/* Facts grid */}
      {facts.length > 0 && (
        <>
          <div style={s.factsGrid}>
            {facts.map((fact, i) => (
              <FactCard
                key={i}
                index={i}
                fact={fact}
                onChangeText={text => setFacts(prev => {
                  const next = [...prev];
                  next[i] = { ...next[i], text };
                  return next;
                })}
                onChoose={url => setFacts(prev => {
                  const next = [...prev];
                  next[i] = { ...next[i], chosen: url };
                  return next;
                })}
              />
            ))}
          </div>

          {/* Render button */}
          {!activeJob && (
            <button
              style={{ ...s.btnRender, ...(!allChosen || running ? s.btnDisabled : {}) }}
              onClick={handleRender}
              disabled={!allChosen || running}
            >
              ▶  Renderizar vídeo
            </button>
          )}
        </>
      )}

      {/* Job log */}
      {activeJob && (
        <div style={s.logCard}>
          <div style={s.logHeader}>
            <span style={s.logTitle}>Log do render</span>
            <StatusBadge status={activeJob.status} />
          </div>
          <div ref={logRef} style={s.logBox}>
            {activeJob.log?.map((line, i) => (
              <div key={i} style={s.logLine}>
                <span style={s.logArrow}>›</span>
                <span style={lineColor(line)}>{line}</span>
              </div>
            ))}
            {running && <span style={{ color: '#6366f1' }}>▌</span>}
          </div>
          {isDone && (
            <div style={s.doneBox}>
              Vídeo gerado com sucesso — veja em <strong>Shorts</strong>.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Fact card ──────────────────────────────────────────────────────────────────
function FactCard({
  index,
  fact,
  onChangeText,
  onChoose,
}: {
  index: number;
  fact: FactState;
  onChangeText: (text: string) => void;
  onChoose: (url: string) => void;
}) {
  return (
    <div style={fc.card}>
      <div style={fc.num}>Fato {index + 1}</div>

      {/* Editable text */}
      <textarea
        style={fc.textarea}
        value={fact.text}
        onChange={e => onChangeText(e.target.value)}
        rows={3}
      />
      <div style={fc.charCount}>{fact.text.length} / 130 chars</div>

      {/* Image candidates */}
      {fact.candidates.length > 0 ? (
        <div style={{
          ...fc.images,
          gridTemplateColumns: `repeat(${Math.min(fact.candidates.length, 3)}, 1fr)`,
        }}>
          {fact.candidates.map((url, j) => (
            <div
              key={j}
              style={{ ...fc.imgWrap, ...(fact.chosen === url ? fc.imgWrapChosen : {}) }}
              onClick={() => onChoose(url)}
            >
              <img
                src={url}
                alt=""
                style={fc.img}
                onError={e => { (e.target as HTMLImageElement).style.opacity = '0.3'; }}
              />
              {fact.chosen === url && <div style={fc.check}>✓</div>}
            </div>
          ))}
        </div>
      ) : (
        <div style={fc.noImages}>Nenhuma imagem encontrada para "{fact.image_query}"</div>
      )}

      {/* Query tag */}
      <div style={fc.query}>
        <span style={{ color: '#4b5563' }}>Query:</span> {fact.image_query}
      </div>
    </div>
  );
}

// ── Sub-components ─────────────────────────────────────────────────────────────
function StatusBadge({ status }: { status: string }) {
  const map: Record<string, [string, string]> = {
    running: ['#fbbf24', 'Executando'],
    done:    ['#22c55e', 'Concluído'],
    error:   ['#ef4444', 'Erro'],
  };
  const [color, text] = map[status] ?? ['#6b7280', status];
  return (
    <span style={{
      fontSize: 11, padding: '3px 9px', borderRadius: 20, fontWeight: 500,
      background: color + '22', color, border: `1px solid ${color}44`,
    }}>
      {text}
    </span>
  );
}

function lineColor(line: string): React.CSSProperties {
  if (line.includes('ERROR') || line.includes('error')) return { color: '#f87171' };
  if (line.includes('WARNING'))                          return { color: '#fbbf24' };
  if (line.includes('✓') || line.toLowerCase().includes('done') || line.includes('gerado'))
    return { color: '#4ade80' };
  return { color: '#d1d5db' };
}

// ── Styles — page ──────────────────────────────────────────────────────────────
const s: Record<string, React.CSSProperties> = {
  page: { padding: '28px 32px', boxSizing: 'border-box', minHeight: '100%' },
  header: {
    display: 'flex', alignItems: 'center', gap: 16, marginBottom: 24,
  },
  backBtn: {
    background: 'transparent', border: '1px solid #374151', borderRadius: 7,
    color: '#9ca3af', fontSize: 13, padding: '6px 14px', cursor: 'pointer',
  },
  title: { fontSize: 20, fontWeight: 600, color: '#f3f4f6', flex: 1, margin: 0 },
  topicRow: { display: 'flex', gap: 10, marginBottom: 20 },
  topicInput: {
    flex: 1, background: '#0f1117', border: '1px solid #374151', borderRadius: 7,
    padding: '10px 12px', color: '#e5e7eb', fontSize: 14, outline: 'none',
  },
  btnGenerate: {
    padding: '10px 20px', background: '#6366f1', border: 'none', borderRadius: 7,
    color: 'white', fontSize: 14, fontWeight: 600, cursor: 'pointer', whiteSpace: 'nowrap',
  },
  btnDisabled: { background: '#374151', cursor: 'not-allowed' },
  errorBox: {
    marginBottom: 16, padding: '10px 14px', background: '#7f1d1d22',
    border: '1px solid #7f1d1d', borderRadius: 7, color: '#f87171', fontSize: 13,
  },
  factsGrid: {
    display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 20,
  },
  btnRender: {
    width: '100%', padding: '13px 20px', background: '#059669',
    border: 'none', borderRadius: 8, color: 'white',
    fontSize: 15, fontWeight: 600, cursor: 'pointer', marginBottom: 20,
  },
  logCard: {
    background: '#161b27', border: '1px solid #1f2937', borderRadius: 12, padding: '18px 20px',
  },
  logHeader: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 },
  logTitle: { fontSize: 13, fontWeight: 600, color: '#9ca3af', textTransform: 'uppercase', letterSpacing: 1 },
  logBox: {
    background: '#0a0d14', border: '1px solid #1f2937', borderRadius: 8,
    padding: '12px 14px', height: 280, overflowY: 'auto',
    fontFamily: 'monospace', fontSize: 12, lineHeight: 1.6,
  },
  logLine: { display: 'flex', gap: 6 },
  logArrow: { color: '#374151', flexShrink: 0 },
  doneBox: {
    marginTop: 12, padding: '10px 14px', background: '#0522183a',
    border: '1px solid #166534', borderRadius: 7, color: '#4ade80', fontSize: 13,
  },
};

// ── Styles — fact card ────────────────────────────────────────────────────────
const fc: Record<string, React.CSSProperties> = {
  card: {
    background: '#161b27', border: '1px solid #1f2937', borderRadius: 10,
    padding: '16px', display: 'flex', flexDirection: 'column', gap: 8,
  },
  num: {
    fontSize: 11, fontWeight: 600, color: '#6366f1', textTransform: 'uppercase', letterSpacing: 1,
  },
  textarea: {
    width: '100%', background: '#0f1117', border: '1px solid #374151', borderRadius: 6,
    padding: '8px 10px', color: '#e5e7eb', fontSize: 13, lineHeight: 1.5,
    resize: 'vertical', boxSizing: 'border-box', fontFamily: 'inherit', outline: 'none',
  },
  charCount: { fontSize: 11, color: '#4b5563', textAlign: 'right' },
  images: { display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 6 },
  imgWrap: {
    position: 'relative', borderRadius: 6, overflow: 'hidden',
    border: '2px solid #374151', cursor: 'pointer', aspectRatio: '2/3',
  },
  imgWrapChosen: { borderColor: '#6366f1', boxShadow: '0 0 0 1px #6366f1' },
  img: { width: '100%', height: '100%', objectFit: 'cover', display: 'block' },
  check: {
    position: 'absolute', top: 4, right: 4, width: 20, height: 20,
    background: '#6366f1', borderRadius: '50%', display: 'flex',
    alignItems: 'center', justifyContent: 'center',
    fontSize: 11, color: 'white', fontWeight: 700,
  },
  noImages: { fontSize: 12, color: '#4b5563', fontStyle: 'italic', padding: '8px 0' },
  query: { fontSize: 11, color: '#6b7280' },
};
