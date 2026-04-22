/**
 * video-renderer/src/ui/pages/CurationPage.tsx
 *
 * Curadoria Did You Know com drag-and-drop, edição inline e cards customizáveis.
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
  const [topic,      setTopic]      = useState(initialTopic);
  const [numCards,   setNumCards]   = useState(5);
  const [loading,    setLoading]    = useState(false);
  const [error,      setError]      = useState('');

  const [slots,      setSlots]      = useState<CardSlot[]>([]);
  const [imagePool,  setImagePool]  = useState<string[]>([]);
  const [factPool,   setFactPool]   = useState<string[]>([]);
  const [customUrl,  setCustomUrl]  = useState('');

  const [musicList,     setMusicList]     = useState<{name: string}[]>([]);
  const [selectedMusic, setSelectedMusic] = useState<string>('');

  const dragRef    = useRef<DragPayload | null>(null);
  const [dropTarget, setDropTarget] = useState<string | null>(null);

  const [activeJob, setActiveJob] = useState<Job | null>(null);
  const [running,   setRunning]   = useState(false);
  const logRef  = useRef<HTMLDivElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    apiFetch('/music').then((list: {name: string}[]) => setMusicList(list)).catch(() => {});
    if (initialTopic) handleGenerate();
  }, []); // eslint-disable-line

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [activeJob?.log?.length]);

  // ── Geração ────────────────────────────────────────────────────────────────
  async function handleGenerate() {
    if (!topic.trim()) return;
    setLoading(true); setError(''); setSlots([]); setImagePool([]); setFactPool([]); setActiveJob(null);
    try {
      const data = await apiFetch('/dyk/generate', {
        method: 'POST',
        body: JSON.stringify({ topic: topic.trim(), profile, num_facts: numCards * 2 }),
      });
      const facts: RawFact[] = data.facts;
      // Slots = numCards vazios; pool tem todos os fatos (2x)
      setSlots(Array.from({ length: numCards }, () => ({ image: null, fact: null })));
      setFactPool(facts.map(f => f.text));
      setImagePool(Array.from(new Set(facts.flatMap(f => f.candidates))));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  // ── Slots ──────────────────────────────────────────────────────────────────
  function addCard() {
    setSlots(prev => [...prev, { image: null, fact: null }]);
  }

  function updateSlotFact(idx: number, text: string) {
    setSlots(prev => prev.map((s, i) => i === idx ? { ...s, fact: text } : s));
  }

  function removeImage(idx: number) {
    setSlots(prev => {
      const url = prev[idx].image;
      if (url) setImagePool(p => [...p, url]);
      return prev.map((s, i) => i === idx ? { ...s, image: null } : s);
    });
  }

  function removeFact(idx: number) {
    setSlots(prev => {
      const text = prev[idx].fact;
      if (text) setFactPool(p => [...p, text]);
      return prev.map((s, i) => i === idx ? { ...s, fact: null } : s);
    });
  }

  function addCustomImage() {
    const url = customUrl.trim();
    if (!url) return;
    setImagePool(p => [...p, url]);
    setCustomUrl('');
  }

  // ── Drag-and-drop ──────────────────────────────────────────────────────────
  function onDragStart(payload: DragPayload) { dragRef.current = payload; }

  function onDragOver(e: React.DragEvent, targetId: string) {
    e.preventDefault(); setDropTarget(targetId);
  }

  function onDragLeave() { setDropTarget(null); }

  function onDrop(e: React.DragEvent, targetId: string) {
    e.preventDefault(); setDropTarget(null);
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
          setImagePool(p => {
            const filtered = p.filter(u => u !== payload.url);
            return displaced ? [...filtered, displaced] : filtered;
          });
        } else if (payload.kind === 'slot-image') {
          const a = next[payload.fromSlot].image;
          next[payload.fromSlot].image = next[slotIdx].image;
          next[slotIdx].image = a;
        }
      } else if (kind === 'txt') {
        if (payload.kind === 'pool-fact') {
          const displaced = next[slotIdx].fact;
          next[slotIdx].fact = payload.text;
          setFactPool(p => {
            const filtered = p.filter(t => t !== payload.text);
            return displaced ? [...filtered, displaced] : filtered;
          });
        } else if (payload.kind === 'slot-fact') {
          const a = next[payload.fromSlot].fact;
          next[payload.fromSlot].fact = next[slotIdx].fact;
          next[slotIdx].fact = a;
        }
      }
      return next;
    });
  }

  // ── Render ─────────────────────────────────────────────────────────────────
  function startPolling(jobId: string) {
    pollRef.current = setInterval(async () => {
      try {
        const job: Job = await apiFetch(`/run/${jobId}`);
        setActiveJob(job);
        if (job.status !== 'running') { clearInterval(pollRef.current!); setRunning(false); }
      } catch { clearInterval(pollRef.current!); setRunning(false); }
    }, 800);
  }

  async function handleRender() {
    const incomplete = slots.findIndex(s => !s.image || !s.fact);
    if (incomplete !== -1) { alert(`Card ${incomplete + 1} está incompleto.`); return; }
    setRunning(true); setActiveJob({ status: 'running', log: [] });
    try {
      const { job_id } = await apiFetch('/dyk/render', {
        method: 'POST',
        body: JSON.stringify({
          profile,
          facts: slots.map(s => ({ text: s.fact, image_url: s.image })),
          music_name: selectedMusic || undefined,
        }),
      });
      startPolling(job_id);
    } catch (e) {
      alert(e instanceof Error ? e.message : String(e));
      setRunning(false); setActiveJob(null);
    }
  }

  const allFilled = slots.length > 0 && slots.every(s => s.image && s.fact);

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
          <div style={s.numCardsWrap}>
          <label style={s.numCardsLabel}>Cards</label>
          <input
            type="number" min={1} max={20} style={s.numCardsInput}
            value={numCards}
            onChange={e => setNumCards(Math.max(1, Math.min(20, parseInt(e.target.value) || 5)))}
          />
        </div>
        <button
          style={{ ...s.btnGenerate, ...(loading ? s.btnDisabled : {}) }}
          onClick={handleGenerate} disabled={loading}
        >
          {loading ? '⟳  Gerando...' : '✦  Gerar fatos'}
        </button>
      </div>

      {/* Music selector */}
      {musicList.length > 0 && (
        <div style={s.musicRow}>
          <span style={s.musicLabel}>🎵 Música</span>
          <select
            style={s.musicSelect}
            value={selectedMusic}
            onChange={e => setSelectedMusic(e.target.value)}
          >
            <option value="">Padrão do perfil</option>
            {musicList.map(m => (
              <option key={m.name} value={m.name}>{m.name}</option>
            ))}
          </select>
        </div>
      )}

      {error && <div style={s.errorBox}>{error}</div>}

      {slots.length > 0 && (
        <>
          {/* ── Sequência ── */}
          <section style={s.section}>
            <div style={s.sectionLabel}>
              Sequência do vídeo
              <span style={s.hint}>Arraste imagens e fatos dos pools abaixo · Edite o texto clicando nele</span>
            </div>
            <div style={s.sequenceWrap}>
              <div style={s.sequence}>
                {slots.map((slot, i) => (
                  <div key={i} style={sq.card}>
                    <div style={sq.cardNum}>Card {i + 1}</div>

                    {/* Image slot */}
                    <div
                      style={{
                        ...sq.imgSlot,
                        ...(dropTarget === `img-${i}` ? sq.slotOver : {}),
                      }}
                      onDragOver={e => onDragOver(e, `img-${i}`)}
                      onDragLeave={onDragLeave}
                      onDrop={e => onDrop(e, `img-${i}`)}
                    >
                      {slot.image ? (
                        <>
                          <img
                            src={slot.image} alt=""
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

                    {/* Fact slot — editable textarea */}
                    <div
                      style={{
                        ...sq.txtSlot,
                        ...(dropTarget === `txt-${i}` ? sq.slotOver : {}),
                      }}
                      onDragOver={e => !slot.fact ? onDragOver(e, `txt-${i}`) : e.preventDefault()}
                      onDragLeave={onDragLeave}
                      onDrop={e => onDrop(e, `txt-${i}`)}
                    >
                      {slot.fact !== null ? (
                        <>
                          <textarea
                            style={sq.textarea}
                            value={slot.fact}
                            onChange={e => updateSlotFact(i, e.target.value)}
                            rows={4}
                            placeholder="Texto do fato..."
                            draggable
                            onDragStart={e => {
                              e.stopPropagation();
                              onDragStart({ kind: 'slot-fact', fromSlot: i });
                            }}
                          />
                          <div style={sq.charCount}>{slot.fact.length} chars</div>
                          <button style={sq.removeBtn} onClick={() => removeFact(i)}>×</button>
                        </>
                      ) : (
                        <span style={sq.slotEmpty}>✎ fato</span>
                      )}
                    </div>
                  </div>
                ))}

                {/* Add card button */}
                <button style={sq.addCard} onClick={addCard} title="Adicionar card">
                  <span style={{ fontSize: 22, lineHeight: 1 }}>+</span>
                  <span style={{ fontSize: 11 }}>Card</span>
                </button>
              </div>
            </div>
          </section>

          {/* ── Pool de imagens ── */}
          <section style={s.section}>
            <div style={s.sectionLabel}>
              Imagens disponíveis
              <span style={s.hint}>{imagePool.length} disponíveis · passe o mouse para ampliar</span>
            </div>

            {/* Custom image URL */}
            <div style={s.customUrlRow}>
              <input
                style={s.customUrlInput}
                value={customUrl}
                onChange={e => setCustomUrl(e.target.value)}
                placeholder="Cole uma URL de imagem para adicionar ao pool..."
                onKeyDown={e => e.key === 'Enter' && addCustomImage()}
              />
              <button
                style={{ ...s.btnAddUrl, ...(!customUrl.trim() ? s.btnDisabled : {}) }}
                onClick={addCustomImage} disabled={!customUrl.trim()}
              >
                + Adicionar
              </button>
            </div>

            {imagePool.length === 0 ? (
              <div style={s.poolEmpty}>Todas as imagens foram atribuídas.</div>
            ) : (
              <div style={pl.imgGrid}>
                {imagePool.map((url, i) => (
                  <ZoomableImage
                    key={url + i}
                    url={url}
                    onDragStart={() => onDragStart({ kind: 'pool-image', url })}
                  />
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
                    <span style={pl.dragHandle}>⠿</span>
                    <span style={pl.factText}>{text}</span>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Render button */}
          {!activeJob && (
            <button
              style={{ ...s.btnRender, ...(!allFilled || running ? s.btnDisabled : {}) }}
              onClick={handleRender} disabled={!allFilled || running}
            >
              ▶  Renderizar vídeo ({slots.length} cards)
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
              <div key={i} style={{ display: 'flex', gap: 6 }}>
                <span style={{ color: '#374151', flexShrink: 0 }}>›</span>
                <span style={lineColor(line)}>{line}</span>
              </div>
            ))}
            {running && <span style={{ color: '#6366f1' }}>▌</span>}
          </div>
          {activeJob.status === 'done' && (
            <div style={s.doneBox}>Vídeo gerado — veja em <strong>Shorts</strong>.</div>
          )}
        </div>
      )}
    </div>
  );
}

// ── ZoomableImage ─────────────────────────────────────────────────────────────
function ZoomableImage({ url, onDragStart }: { url: string; onDragStart: () => void }) {
  const [hovered, setHovered] = useState(false);
  return (
    <div
      style={{
        ...pl.imgWrap,
        transform:  hovered ? 'scale(2.4)' : 'scale(1)',
        zIndex:     hovered ? 50 : 1,
        boxShadow:  hovered ? '0 8px 32px rgba(0,0,0,0.9)' : 'none',
        transition: 'transform 0.18s ease, box-shadow 0.18s ease',
      }}
      draggable
      onDragStart={onDragStart}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <img
        src={url} alt=""
        style={pl.img}
        onError={e => { (e.target as HTMLImageElement).style.opacity = '0.2'; }}
      />
      {!hovered && <div style={pl.dragHint}>drag</div>}
    </div>
  );
}

// ── Sub-components ─────────────────────────────────────────────────────────────
function StatusBadge({ status }: { status: string }) {
  const map: Record<string, [string, string]> = {
    running: ['#fbbf24', 'Executando'], done: ['#22c55e', 'Concluído'], error: ['#ef4444', 'Erro'],
  };
  const [color, text] = map[status] ?? ['#6b7280', status];
  return (
    <span style={{
      fontSize: 11, padding: '3px 9px', borderRadius: 20, fontWeight: 500,
      background: color + '22', color, border: `1px solid ${color}44`,
    }}>{text}</span>
  );
}

function lineColor(line: string): React.CSSProperties {
  if (line.includes('ERROR') || line.includes('error')) return { color: '#f87171' };
  if (line.includes('WARNING'))                          return { color: '#fbbf24' };
  if (line.includes('✓') || line.toLowerCase().includes('done') || line.includes('gerado'))
    return { color: '#4ade80' };
  return { color: '#d1d5db' };
}

// ── Styles ─────────────────────────────────────────────────────────────────────
const s: Record<string, React.CSSProperties> = {
  page:       { padding: '22px 28px', boxSizing: 'border-box', minHeight: '100%' },
  header:     { display: 'flex', alignItems: 'center', gap: 14, marginBottom: 16 },
  backBtn:    {
    background: 'transparent', border: '1px solid #374151', borderRadius: 7,
    color: '#9ca3af', fontSize: 13, padding: '6px 14px', cursor: 'pointer',
  },
  title:      { fontSize: 18, fontWeight: 600, color: '#f3f4f6', flex: 1, margin: 0 },
  topicRow:   { display: 'flex', gap: 10, marginBottom: 18 },
  topicInput: {
    flex: 1, background: '#0f1117', border: '1px solid #374151', borderRadius: 7,
    padding: '9px 12px', color: '#e5e7eb', fontSize: 14, outline: 'none',
  },
  btnGenerate: {
    padding: '9px 18px', background: '#6366f1', border: 'none', borderRadius: 7,
    color: 'white', fontSize: 13, fontWeight: 600, cursor: 'pointer', whiteSpace: 'nowrap',
  },
  btnDisabled:  { background: '#374151', cursor: 'not-allowed' },
  errorBox:     {
    marginBottom: 14, padding: '10px 14px', background: '#7f1d1d22',
    border: '1px solid #7f1d1d', borderRadius: 7, color: '#f87171', fontSize: 13,
  },
  section:      { marginBottom: 22 },
  sectionLabel: {
    fontSize: 11, fontWeight: 600, color: '#6b7280', textTransform: 'uppercase',
    letterSpacing: 1, marginBottom: 10, display: 'flex', alignItems: 'center', gap: 10,
  },
  hint:         { fontWeight: 400, color: '#4b5563', fontSize: 11, textTransform: 'none', letterSpacing: 0 },
  sequenceWrap: { overflowX: 'auto', paddingBottom: 8 },
  sequence:     { display: 'flex', gap: 10, width: 'max-content' },
  poolEmpty:    { color: '#4b5563', fontStyle: 'italic', fontSize: 12 },
  customUrlRow: { display: 'flex', gap: 8, marginBottom: 12 },
  customUrlInput: {
    flex: 1, background: '#0f1117', border: '1px solid #374151', borderRadius: 6,
    padding: '7px 10px', color: '#e5e7eb', fontSize: 12, outline: 'none',
  },
  btnAddUrl: {
    padding: '7px 14px', background: '#374151', border: 'none', borderRadius: 6,
    color: '#e5e7eb', fontSize: 12, fontWeight: 600, cursor: 'pointer', whiteSpace: 'nowrap',
  },
  numCardsWrap: {
    display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0,
  },
  numCardsLabel: { fontSize: 12, color: '#9ca3af', whiteSpace: 'nowrap' as const },
  numCardsInput: {
    width: 52, background: '#0f1117', border: '1px solid #374151', borderRadius: 6,
    padding: '9px 8px', color: '#e5e7eb', fontSize: 14, outline: 'none', textAlign: 'center' as const,
  },
  musicRow: {
    display: 'flex', alignItems: 'center', gap: 10, marginBottom: 18,
  },
  musicLabel: { fontSize: 13, color: '#9ca3af', flexShrink: 0 },
  musicSelect: {
    flex: 1, background: '#0f1117', border: '1px solid #374151', borderRadius: 7,
    padding: '8px 12px', color: '#e5e7eb', fontSize: 13, outline: 'none',
  },
  btnRender: {
    width: '100%', padding: '12px', background: '#059669', border: 'none',
    borderRadius: 8, color: 'white', fontSize: 14, fontWeight: 600, cursor: 'pointer', marginBottom: 20,
  },
  logCard: {
    background: '#161b27', border: '1px solid #1f2937', borderRadius: 12, padding: '16px 18px',
  },
  logHeader:  { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 },
  logTitle:   { fontSize: 11, fontWeight: 600, color: '#9ca3af', textTransform: 'uppercase', letterSpacing: 1 },
  logBox: {
    background: '#0a0d14', border: '1px solid #1f2937', borderRadius: 8,
    padding: '10px 12px', height: 220, overflowY: 'auto',
    fontFamily: 'monospace', fontSize: 12, lineHeight: 1.6,
  },
  doneBox: {
    marginTop: 10, padding: '10px 14px', background: '#0522183a',
    border: '1px solid #166534', borderRadius: 7, color: '#4ade80', fontSize: 13,
  },
};

// sequence card
const sq: Record<string, React.CSSProperties> = {
  card: {
    flexShrink: 0, width: 210,
    background: '#161b27', border: '1px solid #1f2937',
    borderRadius: 10, padding: 10,
    display: 'flex', flexDirection: 'column', gap: 8,
  },
  cardNum: {
    fontSize: 10, fontWeight: 600, color: '#6366f1',
    textTransform: 'uppercase', letterSpacing: 1,
  },
  imgSlot: {
    position: 'relative', width: '100%', aspectRatio: '9/14',
    border: '2px dashed #374151', borderRadius: 7,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    background: '#0f1117', overflow: 'hidden',
  },
  slotOver:  { borderColor: '#6366f1', background: '#1e1b4b' },
  slotImg:   { width: '100%', height: '100%', objectFit: 'cover', cursor: 'grab' },
  slotEmpty: { color: '#4b5563', fontSize: 11, pointerEvents: 'none' },
  txtSlot: {
    position: 'relative', minHeight: 80,
    border: '2px dashed #374151', borderRadius: 7,
    display: 'flex', flexDirection: 'column',
    background: '#0f1117', overflow: 'hidden',
  },
  textarea: {
    width: '100%', background: 'transparent', border: 'none', outline: 'none',
    color: '#e5e7eb', fontSize: 11, lineHeight: 1.5,
    resize: 'none', padding: '8px 24px 4px 8px',
    fontFamily: 'inherit', boxSizing: 'border-box',
    cursor: 'text',
  },
  charCount: { fontSize: 10, color: '#4b5563', textAlign: 'right', padding: '0 8px 6px' },
  removeBtn: {
    position: 'absolute', top: 4, right: 4,
    background: '#374151', border: 'none', borderRadius: '50%',
    width: 18, height: 18, color: '#9ca3af',
    fontSize: 11, cursor: 'pointer',
    display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 0,
  },
  addCard: {
    flexShrink: 0, width: 60, alignSelf: 'stretch',
    background: 'transparent', border: '2px dashed #374151', borderRadius: 10,
    color: '#6b7280', cursor: 'pointer',
    display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
    gap: 4, transition: 'border-color 0.15s, color 0.15s',
  },
};

// pools
const pl: Record<string, React.CSSProperties> = {
  imgGrid: { display: 'flex', flexWrap: 'wrap', gap: 10, overflow: 'visible' },
  imgWrap: {
    position: 'relative', width: 90, aspectRatio: '2/3',
    border: '2px solid #1f2937', borderRadius: 7, overflow: 'hidden',
    cursor: 'grab', flexShrink: 0,
  },
  img:      { width: '100%', height: '100%', objectFit: 'cover', display: 'block' },
  dragHint: {
    position: 'absolute', bottom: 3, right: 5,
    fontSize: 9, color: 'rgba(255,255,255,0.35)', pointerEvents: 'none',
  },
  factGrid: { display: 'flex', flexDirection: 'column', gap: 6 },
  factCard: {
    display: 'flex', alignItems: 'flex-start', gap: 10,
    background: '#161b27', border: '1px solid #1f2937',
    borderRadius: 8, padding: '10px 14px', cursor: 'grab',
  },
  dragHandle: { color: '#4b5563', fontSize: 16, flexShrink: 0, marginTop: 1 },
  factText:   { fontSize: 13, color: '#d1d5db', lineHeight: 1.45 },
};
