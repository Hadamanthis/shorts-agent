/**
 * video-renderer/src/ui/pages/CurationPage.tsx
 *
 * Curadoria para "Did You Know?" com drag-and-drop.
 *
 * Layout:
 *   1. Row de card slots no topo — 1 coluna por card (imagem + fato por slot)
 *   2. Pool de imagens — todas as candidatas de todas as fontes
 *   3. Pool de fatos   — fatos gerados pelo LLM
 *
 * Interação:
 *   - Arraste uma imagem do pool para o slot de imagem de um card
 *   - Arraste um fato do pool para o slot de fato de um card
 *   - Clique × no slot para devolver o item ao pool
 *   - Arraste um slot de imagem/fato para outro slot para trocar posições
 */

import React, { useEffect, useRef, useState } from 'react';
import { apiFetch } from '../AppRouter';

// ── Types ─────────────────────────────────────────────────────────────────────
interface RawFact  { text: string; image_query: string; candidates: string[] }
interface CardSlot { image: string | null; fact: string | null }
interface Job      { status: 'running' | 'done' | 'error'; log?: string[] }

type DragPayload =
  | { kind: 'pool-image'; url: string }
  | { kind: 'pool-fact';  text: string }
  | { kind: 'slot-image'; fromSlot: number }
  | { kind: 'slot-fact';  fromSlot: number };

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
  const [topic,   setTopic]   = useState(initialTopic);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState('');

  // Sequência de cards
  const [slots, setSlots]           = useState<CardSlot[]>([]);
  // Pools de itens disponíveis
  const [imagePool, setImagePool]   = useState<string[]>([]);
  const [factPool,  setFactPool]    = useState<string[]>([]);

  // Drag state
  const dragRef = useRef<DragPayload | null>(null);
  const [dropTarget, setDropTarget] = useState<string | null>(null);

  // Job / render
  const [activeJob, setActiveJob] = useState<Job | null>(null);
  const [running,   setRunning]   = useState(false);
  const logRef  = useRef<HTMLDivElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (initialTopic) handleGenerate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [activeJob?.log?.length]);

  // ── Geração ────────────────────────────────────────────────────────────────
  async function handleGenerate() {
    if (!topic.trim()) return;
    setLoading(true);
    setError('');
    setSlots([]);
    setImagePool([]);
    setFactPool([]);
    setActiveJob(null);
    try {
      const data = await apiFetch('/dyk/generate', {
        method: 'POST',
        body: JSON.stringify({ topic: topic.trim(), profile }),
      });
      const facts: RawFact[] = data.facts;
      const numCards = facts.length;

      // Slots vazios (1 por fato gerado)
      setSlots(Array.from({ length: numCards }, () => ({ image: null, fact: null })));

      // Pool de fatos
      setFactPool(facts.map(f => f.text));

      // Pool de imagens — todas as candidatas de todas as fontes, sem duplicatas
      const allImages = Array.from(new Set(facts.flatMap(f => f.candidates)));
      setImagePool(allImages);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  // ── Drag helpers ───────────────────────────────────────────────────────────
  function onDragStart(payload: DragPayload) {
    dragRef.current = payload;
  }

  function onDragOver(e: React.DragEvent, targetId: string) {
    e.preventDefault();
    setDropTarget(targetId);
  }

  function onDragLeave() {
    setDropTarget(null);
  }

  function onDrop(e: React.DragEvent, targetId: string) {
    e.preventDefault();
    setDropTarget(null);
    const payload = dragRef.current;
    if (!payload) return;
    dragRef.current = null;

    const [kind, idxStr] = targetId.split('-');
    const slotIdx = parseInt(idxStr, 10);

    setSlots(prev => {
      const next = prev.map(s => ({ ...s }));

      if (kind === 'img') {
        if (payload.kind === 'pool-image') {
          const displaced = next[slotIdx].image;
          next[slotIdx].image = payload.url;
          if (displaced) setImagePool(p => [...p, displaced]);
          setImagePool(p => p.filter(u => u !== payload.url));
        } else if (payload.kind === 'slot-image') {
          const from = payload.fromSlot;
          const a = next[from].image;
          const b = next[slotIdx].image;
          next[from].image  = b;
          next[slotIdx].image = a;
        }
      } else if (kind === 'txt') {
        if (payload.kind === 'pool-fact') {
          const displaced = next[slotIdx].fact;
          next[slotIdx].fact = payload.text;
          if (displaced) setFactPool(p => [...p, displaced]);
          setFactPool(p => p.filter(t => t !== payload.text));
        } else if (payload.kind === 'slot-fact') {
          const from = payload.fromSlot;
          const a = next[from].fact;
          const b = next[slotIdx].fact;
          next[from].fact  = b;
          next[slotIdx].fact = a;
        }
      }
      return next;
    });
  }

  function removeImage(slotIdx: number) {
    setSlots(prev => {
      const next = prev.map(s => ({ ...s }));
      const url = next[slotIdx].image;
      next[slotIdx].image = null;
      if (url) setImagePool(p => [...p, url]);
      return next;
    });
  }

  function removeFact(slotIdx: number) {
    setSlots(prev => {
      const next = prev.map(s => ({ ...s }));
      const text = next[slotIdx].fact;
      next[slotIdx].fact = null;
      if (text) setFactPool(p => [...p, text]);
      return next;
    });
  }

  // ── Render ─────────────────────────────────────────────────────────────────
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
    const incomplete = slots.findIndex(s => !s.image || !s.fact);
    if (incomplete !== -1) {
      alert(`Card ${incomplete + 1} está incompleto. Atribua uma imagem e um fato.`);
      return;
    }
    setRunning(true);
    setActiveJob({ status: 'running', log: [] });
    try {
      const { job_id } = await apiFetch('/dyk/render', {
        method: 'POST',
        body: JSON.stringify({
          profile,
          facts: slots.map(s => ({ text: s.fact, image_url: s.image })),
        }),
      });
      startPolling(job_id);
    } catch (e) {
      alert(e instanceof Error ? e.message : String(e));
      setRunning(false);
      setActiveJob(null);
    }
  }

  const allFilled = slots.length > 0 && slots.every(s => s.image && s.fact);
  const isDone    = activeJob?.status === 'done';

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div style={s.page}>
      {/* Header */}
      <div style={s.header}>
        <button style={s.backBtn} onClick={onBack}>← Voltar</button>
        <h1 style={s.title}>Did You Know? — Curadoria</h1>
        <span style={{ color: '#6b7280', fontSize: 13 }}>
          Perfil: <strong style={{ color: '#e5e7eb' }}>{profile}</strong>
        </span>
      </div>

      {/* Topic */}
      <div style={s.topicRow}>
        <input
          style={s.topicInput}
          value={topic}
          onChange={e => setTopic(e.target.value)}
          placeholder="Ex: Oceano, Roma Antiga, Buracos Negros..."
          onKeyDown={e => e.key === 'Enter' && !loading && handleGenerate()}
        />
        <button
          style={{ ...s.btnGenerate, ...(loading ? s.btnDisabled : {}) }}
          onClick={handleGenerate}
          disabled={loading}
        >
          {loading ? '⟳  Gerando...' : '✦  Gerar fatos'}
        </button>
      </div>

      {error && <div style={s.errorBox}>{error}</div>}

      {slots.length > 0 && (
        <>
          {/* ── Sequência de cards ── */}
          <section style={s.section}>
            <div style={s.sectionLabel}>
              Sequência do vídeo
              <span style={s.hint}>Arraste imagens e fatos dos pools abaixo para cada card</span>
            </div>
            <div style={s.sequence}>
              {slots.map((slot, i) => (
                <div key={i} style={sq.card}>
                  <div style={sq.cardNum}>Card {i + 1}</div>

                  {/* Image slot */}
                  <div
                    style={{
                      ...sq.imgSlot,
                      ...(dropTarget === `img-${i}` ? sq.slotOver : {}),
                      ...(slot.image ? sq.slotFilled : {}),
                    }}
                    onDragOver={e => onDragOver(e, `img-${i}`)}
                    onDragLeave={onDragLeave}
                    onDrop={e => onDrop(e, `img-${i}`)}
                  >
                    {slot.image ? (
                      <>
                        <img
                          src={slot.image}
                          alt=""
                          style={sq.slotImg}
                          draggable
                          onDragStart={() => onDragStart({ kind: 'slot-image', fromSlot: i })}
                        />
                        <button style={sq.removeBtn} onClick={() => removeImage(i)}>×</button>
                      </>
                    ) : (
                      <span style={sq.slotEmpty}>🖼 imagem</span>
                    )}
                  </div>

                  {/* Fact slot */}
                  <div
                    style={{
                      ...sq.txtSlot,
                      ...(dropTarget === `txt-${i}` ? sq.slotOver : {}),
                      ...(slot.fact ? sq.slotFilledTxt : {}),
                    }}
                    onDragOver={e => onDragOver(e, `txt-${i}`)}
                    onDragLeave={onDragLeave}
                    onDrop={e => onDrop(e, `txt-${i}`)}
                  >
                    {slot.fact ? (
                      <>
                        <span
                          style={sq.slotTxt}
                          draggable
                          onDragStart={() => onDragStart({ kind: 'slot-fact', fromSlot: i })}
                        >
                          {slot.fact}
                        </span>
                        <button style={sq.removeBtn} onClick={() => removeFact(i)}>×</button>
                      </>
                    ) : (
                      <span style={sq.slotEmpty}>✎ fato</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* ── Pool de imagens ── */}
          <section style={s.section}>
            <div style={s.sectionLabel}>
              Imagens disponíveis
              <span style={s.hint}>{imagePool.length} restantes</span>
            </div>
            {imagePool.length === 0 ? (
              <div style={s.poolEmpty}>Todas as imagens foram atribuídas.</div>
            ) : (
              <div style={pl.imgGrid}>
                {imagePool.map((url, i) => (
                  <div
                    key={url + i}
                    style={pl.imgWrap}
                    draggable
                    onDragStart={() => onDragStart({ kind: 'pool-image', url })}
                  >
                    <img
                      src={url}
                      alt=""
                      style={pl.img}
                      onError={e => { (e.target as HTMLImageElement).style.opacity = '0.25'; }}
                    />
                    <div style={pl.dragHint}>drag</div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* ── Pool de fatos ── */}
          <section style={s.section}>
            <div style={s.sectionLabel}>
              Fatos disponíveis
              <span style={s.hint}>{factPool.length} restantes</span>
            </div>
            {factPool.length === 0 ? (
              <div style={s.poolEmpty}>Todos os fatos foram atribuídos.</div>
            ) : (
              <div style={pl.factGrid}>
                {factPool.map((text, i) => (
                  <div
                    key={text + i}
                    style={pl.factCard}
                    draggable
                    onDragStart={() => onDragStart({ kind: 'pool-fact', text })}
                  >
                    <span style={pl.factText}>{text}</span>
                    <span style={pl.dragHintFact}>drag</span>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* ── Botão renderizar ── */}
          {!activeJob && (
            <button
              style={{ ...s.btnRender, ...(!allFilled || running ? s.btnDisabled : {}) }}
              onClick={handleRender}
              disabled={!allFilled || running}
            >
              ▶  Renderizar vídeo
            </button>
          )}
        </>
      )}

      {/* ── Job log ── */}
      {activeJob && (
        <div style={s.logCard}>
          <div style={s.logHeader}>
            <span style={s.logTitle}>Log do render</span>
            <StatusBadge status={activeJob.status} />
          </div>
          <div ref={logRef} style={s.logBox}>
            {activeJob.log?.map((line, i) => (
              <div key={i} style={{ display: 'flex', gap: 6 }}>
                <span style={{ color: '#374151', flexShrink: 0 }}>›</span>
                <span style={lineColor(line)}>{line}</span>
              </div>
            ))}
            {running && <span style={{ color: '#6366f1' }}>▌</span>}
          </div>
          {isDone && (
            <div style={s.doneBox}>Vídeo gerado com sucesso — veja em <strong>Shorts</strong>.</div>
          )}
        </div>
      )}
    </div>
  );
}

// ── StatusBadge ───────────────────────────────────────────────────────────────
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

// ── Styles — page ─────────────────────────────────────────────────────────────
const s: Record<string, React.CSSProperties> = {
  page:       { padding: '24px 28px', boxSizing: 'border-box', minHeight: '100%' },
  header:     { display: 'flex', alignItems: 'center', gap: 14, marginBottom: 18 },
  backBtn:    {
    background: 'transparent', border: '1px solid #374151', borderRadius: 7,
    color: '#9ca3af', fontSize: 13, padding: '6px 14px', cursor: 'pointer',
  },
  title:      { fontSize: 18, fontWeight: 600, color: '#f3f4f6', flex: 1, margin: 0 },
  topicRow:   { display: 'flex', gap: 10, marginBottom: 20 },
  topicInput: {
    flex: 1, background: '#0f1117', border: '1px solid #374151', borderRadius: 7,
    padding: '9px 12px', color: '#e5e7eb', fontSize: 14, outline: 'none',
  },
  btnGenerate: {
    padding: '9px 18px', background: '#6366f1', border: 'none', borderRadius: 7,
    color: 'white', fontSize: 13, fontWeight: 600, cursor: 'pointer', whiteSpace: 'nowrap',
  },
  btnDisabled: { background: '#374151', cursor: 'not-allowed' },
  errorBox: {
    marginBottom: 16, padding: '10px 14px', background: '#7f1d1d22',
    border: '1px solid #7f1d1d', borderRadius: 7, color: '#f87171', fontSize: 13,
  },
  section:      { marginBottom: 20 },
  sectionLabel: {
    fontSize: 11, fontWeight: 600, color: '#6b7280', textTransform: 'uppercase',
    letterSpacing: 1, marginBottom: 10, display: 'flex', alignItems: 'center', gap: 10,
  },
  hint:         { fontWeight: 400, color: '#4b5563', fontSize: 11, textTransform: 'none', letterSpacing: 0 },
  sequence:     { display: 'flex', gap: 10, overflowX: 'auto', paddingBottom: 6 },
  poolEmpty:    { color: '#4b5563', fontStyle: 'italic', fontSize: 12 },
  btnRender: {
    width: '100%', padding: '12px', background: '#059669', border: 'none',
    borderRadius: 8, color: 'white', fontSize: 14, fontWeight: 600, cursor: 'pointer',
    marginBottom: 20,
  },
  logCard: {
    background: '#161b27', border: '1px solid #1f2937', borderRadius: 12, padding: '16px 18px',
  },
  logHeader: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 },
  logTitle:  { fontSize: 11, fontWeight: 600, color: '#9ca3af', textTransform: 'uppercase', letterSpacing: 1 },
  logBox: {
    background: '#0a0d14', border: '1px solid #1f2937', borderRadius: 8,
    padding: '10px 12px', height: 240, overflowY: 'auto',
    fontFamily: 'monospace', fontSize: 12, lineHeight: 1.6,
  },
  doneBox: {
    marginTop: 10, padding: '10px 14px', background: '#0522183a',
    border: '1px solid #166534', borderRadius: 7, color: '#4ade80', fontSize: 13,
  },
};

// ── Styles — sequence card ────────────────────────────────────────────────────
const sq: Record<string, React.CSSProperties> = {
  card: {
    flexShrink: 0, width: 160,
    background: '#161b27', border: '1px solid #1f2937',
    borderRadius: 10, padding: 10,
    display: 'flex', flexDirection: 'column', gap: 8,
  },
  cardNum: {
    fontSize: 10, fontWeight: 600, color: '#6366f1',
    textTransform: 'uppercase', letterSpacing: 1,
  },
  imgSlot: {
    position: 'relative', width: '100%', aspectRatio: '2/3',
    border: '2px dashed #374151', borderRadius: 7,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    background: '#0f1117', overflow: 'hidden', cursor: 'default',
  },
  slotOver:      { borderColor: '#6366f1', background: '#1e1b4b' },
  slotFilled:    { border: '2px solid #374151' },
  slotFilledTxt: { border: '2px solid #374151', background: '#0f1117' },
  slotImg: { width: '100%', height: '100%', objectFit: 'cover', cursor: 'grab' },
  slotEmpty: { color: '#4b5563', fontSize: 11, pointerEvents: 'none' },
  txtSlot: {
    position: 'relative', minHeight: 56, padding: '8px 28px 8px 8px',
    border: '2px dashed #374151', borderRadius: 7,
    display: 'flex', alignItems: 'flex-start',
    background: '#0f1117',
  },
  slotTxt: {
    fontSize: 11, color: '#d1d5db', lineHeight: 1.4,
    cursor: 'grab', userSelect: 'none',
    display: '-webkit-box', WebkitLineClamp: 4,
    WebkitBoxOrient: 'vertical', overflow: 'hidden',
  },
  removeBtn: {
    position: 'absolute', top: 4, right: 4,
    background: '#374151', border: 'none', borderRadius: '50%',
    width: 18, height: 18, color: '#9ca3af',
    fontSize: 12, cursor: 'pointer', lineHeight: '18px',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    padding: 0,
  },
};

// ── Styles — pools ────────────────────────────────────────────────────────────
const pl: Record<string, React.CSSProperties> = {
  imgGrid: {
    display: 'flex', flexWrap: 'wrap', gap: 8,
  },
  imgWrap: {
    position: 'relative', width: 80, aspectRatio: '2/3',
    border: '2px solid #1f2937', borderRadius: 7, overflow: 'hidden',
    cursor: 'grab', flexShrink: 0,
  },
  img: { width: '100%', height: '100%', objectFit: 'cover', display: 'block' },
  dragHint: {
    position: 'absolute', bottom: 3, right: 5,
    fontSize: 9, color: 'rgba(255,255,255,0.4)', pointerEvents: 'none',
  },
  factGrid: { display: 'flex', flexDirection: 'column', gap: 6 },
  factCard: {
    position: 'relative', background: '#161b27',
    border: '1px solid #1f2937', borderRadius: 8,
    padding: '10px 36px 10px 12px', cursor: 'grab',
  },
  factText: { fontSize: 13, color: '#d1d5db', lineHeight: 1.45 },
  dragHintFact: {
    position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)',
    fontSize: 10, color: '#4b5563',
  },
};
