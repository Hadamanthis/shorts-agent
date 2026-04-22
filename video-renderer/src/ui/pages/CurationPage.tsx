/**
 * video-renderer/src/ui/pages/CurationPage.tsx
 *
 * Curadoria Did You Know com drag-and-drop, edição inline e cards customizáveis.
 */

import React, { useEffect, useRef, useState } from 'react';
import { apiFetch } from '../AppRouter';

const API_BASE = 'http://localhost:8000';

// ── Types ─────────────────────────────────────────────────────────────────────
interface RawFact  { text: string; image_query: string; candidates: string[] }
interface CardSlot {
  image: string | null;
  fact: string | null;
  duration?: number; // segundos por card; undefined = padrão do perfil
}
interface DYKMetadata { title: string; description: string; hashtags: string[] }
interface Job {
  status: 'running' | 'done' | 'error';
  log?: string[];
  metadata?: DYKMetadata;
}

type DragPayload =
  | { kind: 'pool-image'; url: string; poolIdx: number }
  | { kind: 'pool-video'; name: string }
  | { kind: 'pool-fact';  text: string; poolIdx: number }
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
  const [videoList,     setVideoList]     = useState<{name: string}[]>([]);
  const [cleaning,      setCleaning]      = useState(false);
  const [uploadingVideo, setUploadingVideo] = useState(false);

  const [defaultDuration, setDefaultDuration] = useState(6);
  const [imgsPerSource,   setImgsPerSource]   = useState(3);

  // Adicionar fato manual
  const [newFactText, setNewFactText] = useState('');
  const [showAddFact, setShowAddFact] = useState(false);

  // Buscar mais imagens
  const [addImageTopic, setAddImageTopic] = useState('');
  const [addImageNum,   setAddImageNum]   = useState(3);
  const [addingImages,  setAddingImages]  = useState(false);

  // Metadata após render
  const [metadata, setMetadata] = useState<DYKMetadata | null>(null);
  const [showMeta, setShowMeta] = useState(false);

  const dragRef    = useRef<DragPayload | null>(null);
  const [dropTarget, setDropTarget] = useState<string | null>(null);

  const [activeJob, setActiveJob] = useState<Job | null>(null);
  const [running,   setRunning]   = useState(false);
  const logRef       = useRef<HTMLDivElement>(null);
  const pollRef      = useRef<ReturnType<typeof setInterval> | null>(null);
  const videoFileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    apiFetch('/music').then((list: {name: string}[]) => setMusicList(list)).catch(() => {});
    apiFetch('/videos').then((list: {name: string}[]) => setVideoList(list)).catch(() => {});
    apiFetch('/config').then((cfg: Record<string, unknown>) => {
      const dyk = cfg['did-you-know'] as Record<string, number> | undefined;
      if (dyk?.card_duration_seconds) setDefaultDuration(dyk.card_duration_seconds);
      if (dyk?.imgs_per_source) {
        setImgsPerSource(dyk.imgs_per_source);
        setAddImageNum(dyk.imgs_per_source);
      }
    }).catch(() => {});
    if (initialTopic) handleGenerate();
  }, []); // eslint-disable-line

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [activeJob?.log?.length]);

  // ── Geração ────────────────────────────────────────────────────────────────
  async function handleGenerate() {
    if (!topic.trim()) return;
    const hasContent = slots.some(s => s.image !== null || s.fact !== null);
    if (hasContent) {
      if (!window.confirm('Os cards atuais têm conteúdo. Gerar novos fatos irá limpar tudo. Continuar?')) return;
    }
    setLoading(true);
    setError('');
    setSlots([]);
    setImagePool([]);
    setFactPool([]);
    setActiveJob(null);
    setMetadata(null);
    try {
      const data = await apiFetch('/dyk/generate', {
        method: 'POST',
        body: JSON.stringify({ topic: topic.trim(), profile, num_facts: numCards }),
      });
      const facts: RawFact[] = data.facts;
      setSlots(Array.from({ length: numCards }, () => ({ image: null, fact: null })));
      setFactPool(facts.map(f => f.text));
      setImagePool(Array.from(new Set(facts.flatMap(f => f.candidates))));
      setAddImageTopic(topic.trim());
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

  function handleDeleteCard(i: number) {
    setSlots(prev => {
      const slot = prev[i];
      if (slot.image && !slot.image.startsWith('video:')) setImagePool(p => [...p, slot.image!]);
      if (slot.fact) setFactPool(p => [...p, slot.fact!]);
      return prev.filter((_, idx) => idx !== i);
    });
  }

  function moveCard(i: number, dir: -1 | 1) {
    const j = i + dir;
    if (j < 0 || j >= slots.length) return;
    setSlots(prev => {
      const next = [...prev];
      [next[i], next[j]] = [next[j], next[i]];
      return next;
    });
  }

  function updateSlotFact(idx: number, text: string) {
    setSlots(prev => prev.map((s, i) => i === idx ? { ...s, fact: text } : s));
  }

  function updateSlotDuration(idx: number, val: string) {
    const num = val === '' ? undefined : Math.max(1, parseInt(val) || 1);
    setSlots(prev => prev.map((s, i) => i === idx ? { ...s, duration: num } : s));
  }

  function removeImage(idx: number) {
    setSlots(prev => {
      const url = prev[idx].image;
      if (url && !url.startsWith('video:')) setImagePool(p => [...p, url]);
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

  // ── Assign "→ próximo vazio" ───────────────────────────────────────────────
  function handleAssignFactToNext(text: string, poolIdx: number) {
    const nextEmpty = slots.findIndex(s => s.fact === null);
    if (nextEmpty === -1) { alert('Todos os cards já têm fato.'); return; }
    setSlots(prev => prev.map((s, i) => i === nextEmpty ? { ...s, fact: text } : s));
    setFactPool(prev => prev.filter((_, i) => i !== poolIdx));
  }

  function handleAssignImageToNext(url: string, poolIdx: number) {
    const nextEmpty = slots.findIndex(s => s.image === null);
    if (nextEmpty === -1) { alert('Todos os cards já têm imagem.'); return; }
    setSlots(prev => prev.map((s, i) => i === nextEmpty ? { ...s, image: url } : s));
    setImagePool(prev => prev.filter((_, i) => i !== poolIdx));
  }

  function handleAssignVideoToNext(name: string) {
    const nextEmpty = slots.findIndex(s => s.image === null);
    if (nextEmpty === -1) { alert('Todos os cards já têm imagem/vídeo.'); return; }
    setSlots(prev => prev.map((s, i) => i === nextEmpty ? { ...s, image: `video:${name}` } : s));
  }

  // ── Adicionar fato manual ──────────────────────────────────────────────────
  function handleAddFact() {
    const text = newFactText.trim();
    if (!text) return;
    setFactPool(prev => [...prev, text]);
    setNewFactText('');
    setShowAddFact(false);
  }

  // ── Buscar mais imagens ────────────────────────────────────────────────────
  async function handleSearchMoreImages() {
    if (!addImageTopic.trim()) return;
    setAddingImages(true);
    try {
      const data = await apiFetch('/dyk/search-images', {
        method: 'POST',
        body: JSON.stringify({ query: addImageTopic.trim(), per_source: addImageNum }),
      });
      const newImgs: string[] = data.images ?? [];
      setImagePool(prev => {
        const existing = new Set(prev);
        return [...prev, ...newImgs.filter(u => !existing.has(u))];
      });
    } catch (e) {
      alert(e instanceof Error ? e.message : String(e));
    } finally {
      setAddingImages(false);
    }
  }

  // ── Upload de vídeo local ──────────────────────────────────────────────────
  async function handleVideoUpload(file: File) {
    setUploadingVideo(true);
    try {
      const form = new FormData();
      form.append('file', file);
      const resp = await fetch(`${API_BASE}/dyk/upload-video`, { method: 'POST', body: form });
      if (!resp.ok) throw new Error(await resp.text());
      const data = await resp.json();
      setVideoList(prev => {
        if (prev.some(v => v.name === data.name)) return prev;
        return [...prev, { name: data.name }];
      });
    } catch (e) {
      alert(e instanceof Error ? e.message : String(e));
    } finally {
      setUploadingVideo(false);
    }
  }

  // ── Imagem custom por URL ──────────────────────────────────────────────────
  function addCustomImage() {
    const url = customUrl.trim();
    if (!url) return;
    setImagePool(p => [...p, url]);
    setCustomUrl('');
  }

  async function handleCleanup() {
    setCleaning(true);
    try { await apiFetch('/cleanup', { method: 'POST' }); } catch { /* ignore */ }
    finally { setCleaning(false); }
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
            const filtered = p.filter((_u, i) => i !== payload.poolIdx);
            return displaced && !displaced.startsWith('video:') ? [...filtered, displaced] : filtered;
          });
        } else if (payload.kind === 'pool-video') {
          next[slotIdx].image = `video:${payload.name}`;
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
            const filtered = p.filter((_t, i) => i !== payload.poolIdx);
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
  function factFontSize(slot: CardSlot): number {
    const d = slot.duration ?? defaultDuration;
    if (d <= 4) return 11;
    if (d >= 8) return 15;
    return 13;
  }

  function startPolling(jobId: string) {
    pollRef.current = setInterval(async () => {
      try {
        const job: Job = await apiFetch(`/run/${jobId}`);
        setActiveJob(job);
        if (job.status !== 'running') {
          clearInterval(pollRef.current!);
          setRunning(false);
          if (job.status === 'done' && job.metadata) {
            setMetadata(job.metadata);
            setShowMeta(true);
          }
        }
      } catch { clearInterval(pollRef.current!); setRunning(false); }
    }, 800);
  }

  async function handleRender() {
    const incomplete = slots.findIndex(s => !s.image || !s.fact);
    if (incomplete !== -1) { alert(`Card ${incomplete + 1} está incompleto.`); return; }
    setRunning(true); setActiveJob({ status: 'running', log: [] }); setMetadata(null);
    try {
      const { job_id } = await apiFetch('/dyk/render', {
        method: 'POST',
        body: JSON.stringify({
          profile,
          topic: topic.trim() || undefined,
          facts: slots.map(s => ({
            text: s.fact,
            image_url: s.image,
            duration_seconds: s.duration || undefined,
          })),
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
          <select style={s.musicSelect} value={selectedMusic} onChange={e => setSelectedMusic(e.target.value)}>
            <option value="">Padrão do perfil</option>
            {musicList.map(m => <option key={m.name} value={m.name}>{m.name}</option>)}
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
              <span style={s.hint}>← → para reordenar · × para excluir · duração em segundos por card</span>
            </div>
            <div style={s.sequenceWrap}>
              <div style={s.sequence}>
                {slots.map((slot, i) => (
                  <div key={i} style={sq.card}>
                    {/* Card header */}
                    <div style={sq.cardHeader}>
                      <span style={sq.cardNum}>Card {i + 1}</span>
                      <div style={sq.cardActions}>
                        <button style={sq.arrowBtn} onClick={() => moveCard(i, -1)} disabled={i === 0} title="Mover esquerda">←</button>
                        <button style={sq.arrowBtn} onClick={() => moveCard(i, 1)} disabled={i === slots.length - 1} title="Mover direita">→</button>
                        <button style={sq.deleteCardBtn} onClick={() => handleDeleteCard(i)} title="Excluir card">×</button>
                      </div>
                    </div>

                    {/* Image slot */}
                    <div
                      style={{ ...sq.imgSlot, ...(dropTarget === `img-${i}` ? sq.slotOver : {}) }}
                      onDragOver={e => onDragOver(e, `img-${i}`)}
                      onDragLeave={onDragLeave}
                      onDrop={e => onDrop(e, `img-${i}`)}
                    >
                      {slot.image ? (
                        <>
                          {slot.image.startsWith('video:') ? (
                            <div style={sq.videoSlotContent}>
                              <span style={{ fontSize: 24 }}>🎬</span>
                              <span style={{ fontSize: 10, color: '#a5b4fc', marginTop: 4, maxWidth: '90%', textAlign: 'center', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                {slot.image.slice(6)}
                              </span>
                            </div>
                          ) : (
                            <img
                              src={slot.image} alt=""
                              style={sq.slotImg}
                              draggable
                              onDragStart={() => onDragStart({ kind: 'slot-image', fromSlot: i })}
                            />
                          )}
                          <button style={sq.removeBtn} onClick={() => removeImage(i)}>×</button>
                        </>
                      ) : (
                        <span style={sq.slotEmpty}>🖼 imagem</span>
                      )}
                    </div>

                    {/* Fact slot */}
                    <div
                      style={{ ...sq.txtSlot, ...(dropTarget === `txt-${i}` ? sq.slotOver : {}) }}
                      onDragOver={e => !slot.fact ? onDragOver(e, `txt-${i}`) : e.preventDefault()}
                      onDragLeave={onDragLeave}
                      onDrop={e => onDrop(e, `txt-${i}`)}
                    >
                      {slot.fact !== null ? (
                        <>
                          <textarea
                            style={{ ...sq.textarea, fontSize: factFontSize(slot) }}
                            value={slot.fact}
                            onChange={e => updateSlotFact(i, e.target.value)}
                            rows={slot.duration && slot.duration >= 8 ? 5 : 4}
                            placeholder="Texto do fato..."
                            draggable
                            onDragStart={e => { e.stopPropagation(); onDragStart({ kind: 'slot-fact', fromSlot: i }); }}
                          />
                          <div style={sq.charCount}>{slot.fact.length} chars</div>
                          <button style={sq.removeBtn} onClick={() => removeFact(i)}>×</button>
                        </>
                      ) : (
                        <span style={sq.slotEmpty}>✎ fato</span>
                      )}
                    </div>

                    {/* Duration field */}
                    <div style={sq.durationRow}>
                      <span style={sq.durationLabel}>⏱</span>
                      <input
                        type="number"
                        min={1}
                        max={60}
                        style={sq.durationInput}
                        value={slot.duration ?? ''}
                        onChange={e => updateSlotDuration(i, e.target.value)}
                        placeholder={`${defaultDuration}s`}
                        title="Duração em segundos (vazio = padrão do perfil)"
                      />
                      <span style={sq.durationSuffix}>s</span>
                    </div>
                  </div>
                ))}

                {/* Add card */}
                <button style={sq.addCard} onClick={addCard} title="Adicionar card">
                  <span style={{ fontSize: 22, lineHeight: 1 }}>+</span>
                  <span style={{ fontSize: 11 }}>Card</span>
                </button>
              </div>
            </div>
          </section>

          {/* ── Buscar mais imagens ── */}
          <section style={s.section}>
            <div style={s.sectionLabel}>Buscar mais imagens</div>
            <div style={s.searchImgRow}>
              <input
                style={s.topicInput}
                value={addImageTopic}
                onChange={e => setAddImageTopic(e.target.value)}
                placeholder="Tópico ou palavra-chave..."
                onKeyDown={e => e.key === 'Enter' && !addingImages && handleSearchMoreImages()}
              />
              <div style={s.numCardsWrap}>
                <label style={s.numCardsLabel}>Por fonte</label>
                <input
                  type="number" min={1} max={10} style={s.numCardsInput}
                  value={addImageNum}
                  onChange={e => setAddImageNum(Math.max(1, Math.min(10, parseInt(e.target.value) || imgsPerSource)))}
                />
              </div>
              <button
                style={{ ...s.btnAddUrl, ...(addingImages || !addImageTopic.trim() ? s.btnDisabled : { background: '#4f46e5', color: 'white' }) }}
                onClick={handleSearchMoreImages}
                disabled={addingImages || !addImageTopic.trim()}
              >
                {addingImages ? '⟳ Buscando...' : '🔍 Buscar'}
              </button>
            </div>
          </section>

          {/* ── Pool de imagens ── */}
          <section style={s.section}>
            <div style={s.sectionLabel}>
              Imagens disponíveis
              <span style={s.hint}>{imagePool.length} disponíveis · arraste ou clique → para o próximo vazio</span>
            </div>

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
                    onDragStart={() => onDragStart({ kind: 'pool-image', url, poolIdx: i })}
                    onAssign={() => handleAssignImageToNext(url, i)}
                  />
                ))}
              </div>
            )}
          </section>

          {/* ── Pool de vídeos locais ── */}
          <section style={s.section}>
            <div style={s.sectionLabel}>
              Vídeos locais
              <span style={s.hint}>assets/videos/ · arraste ou → para o próximo vazio</span>
            </div>
            <div style={pl.imgGrid}>
              {videoList.map(v => (
                <div key={v.name} style={pl.videoChipWrap}>
                  <div
                    style={pl.videoChip}
                    draggable
                    onDragStart={() => onDragStart({ kind: 'pool-video', name: v.name })}
                    title={v.name}
                  >
                    <span style={{ fontSize: 16 }}>🎬</span>
                    <span style={{ fontSize: 10, color: '#d1d5db', maxWidth: 72, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {v.name}
                    </span>
                  </div>
                  <button style={pl.assignBtn} onClick={() => handleAssignVideoToNext(v.name)} title="Adicionar ao próximo card vazio">→</button>
                </div>
              ))}

              {/* Upload de vídeo local */}
              <div style={pl.uploadWrap}>
                <input
                  ref={videoFileRef}
                  type="file"
                  accept=".mp4,.mov,.webm,.mkv"
                  style={{ display: 'none' }}
                  onChange={e => e.target.files?.[0] && handleVideoUpload(e.target.files[0])}
                />
                <button
                  style={{ ...pl.videoChip, ...pl.uploadBtn, ...(uploadingVideo ? s.btnDisabled : {}) }}
                  onClick={() => videoFileRef.current?.click()}
                  disabled={uploadingVideo}
                  title="Subir vídeo local"
                >
                  <span style={{ fontSize: 16 }}>{uploadingVideo ? '⟳' : '⬆'}</span>
                  <span style={{ fontSize: 10, color: '#9ca3af' }}>Upload</span>
                </button>
              </div>
            </div>
          </section>

          {/* ── Pool de fatos ── */}
          <section style={s.section}>
            <div style={s.sectionLabel}>
              Fatos disponíveis
              <span style={s.hint}>{factPool.length} restantes · arraste ou → para o próximo vazio</span>
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
                    onDragStart={() => onDragStart({ kind: 'pool-fact', text, poolIdx: i })}
                  >
                    <span style={pl.dragHandle}>⠿</span>
                    <span style={pl.factText}>{text}</span>
                    <button
                      style={pl.assignBtn}
                      onClick={() => handleAssignFactToNext(text, i)}
                      title="Adicionar ao próximo card vazio"
                    >→</button>
                  </div>
                ))}
              </div>
            )}

            {/* Adicionar fato manual */}
            {showAddFact ? (
              <div style={s.addFactRow}>
                <textarea
                  style={s.addFactInput}
                  value={newFactText}
                  onChange={e => setNewFactText(e.target.value)}
                  placeholder="Digite o texto do fato..."
                  rows={3}
                  autoFocus
                  onKeyDown={e => { if (e.key === 'Enter' && e.ctrlKey) handleAddFact(); }}
                />
                <div style={{ display: 'flex', gap: 8, marginTop: 6 }}>
                  <button
                    style={{ ...s.btnAddUrl, ...(!newFactText.trim() ? s.btnDisabled : { background: '#059669', color: 'white' }) }}
                    onClick={handleAddFact} disabled={!newFactText.trim()}
                  >✓ Adicionar</button>
                  <button style={{ ...s.btnAddUrl }} onClick={() => { setShowAddFact(false); setNewFactText(''); }}>Cancelar</button>
                </div>
              </div>
            ) : (
              <button style={s.btnAddFact} onClick={() => setShowAddFact(true)}>＋ Adicionar fato</button>
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
            <div style={s.doneRow}>
              <div style={s.doneBox}>Vídeo gerado — veja em <strong>Shorts</strong>.</div>
              <button
                style={{ ...s.btnCleanup, ...(cleaning ? s.btnDisabled : {}) }}
                onClick={handleCleanup}
                disabled={cleaning}
                title="Remove imagens temporárias dyk_img_* de public/"
              >
                {cleaning ? '⟳ Limpando...' : '🗑 Limpar cache'}
              </button>
            </div>
          )}
        </div>
      )}

      {/* Metadata SEO */}
      {metadata && (
        <div style={s.metaCard}>
          <div style={s.metaHeader}>
            <span style={s.metaTitle}>📋 Metadata SEO</span>
            <button style={s.metaToggle} onClick={() => setShowMeta(v => !v)}>
              {showMeta ? '▲ Ocultar' : '▼ Mostrar'}
            </button>
          </div>
          {showMeta && (
            <div style={s.metaBody}>
              <MetaSection label="Título" content={metadata.title} />
              <MetaSection label="Descrição" content={metadata.description} pre />
              <MetaSection label="Hashtags" content={metadata.hashtags.join(' ')} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── ZoomableImage ─────────────────────────────────────────────────────────────
function ZoomableImage({ url, onDragStart, onAssign }: {
  url: string;
  onDragStart: () => void;
  onAssign: () => void;
}) {
  const [hovered, setHovered] = useState(false);
  return (
    <div style={pl.imgWrapOuter}>
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
      <button style={pl.imgAssignBtn} onClick={onAssign} title="Adicionar ao próximo card vazio">→</button>
    </div>
  );
}

// ── MetaSection ───────────────────────────────────────────────────────────────
function MetaSection({ label, content, pre }: { label: string; content: string; pre?: boolean }) {
  return (
    <div style={ms.section}>
      <div style={ms.label}>{label}</div>
      {pre
        ? <pre style={ms.content}>{content}</pre>
        : <div style={ms.content}>{content}</div>
      }
      <button style={ms.copyBtn} onClick={() => navigator.clipboard.writeText(content)}>
        📋 Copiar
      </button>
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
  page:         { padding: '22px 28px', boxSizing: 'border-box', minHeight: '100%' },
  header:       { display: 'flex', alignItems: 'center', gap: 14, marginBottom: 16 },
  backBtn:      {
    background: 'transparent', border: '1px solid #374151', borderRadius: 7,
    color: '#9ca3af', fontSize: 13, padding: '6px 14px', cursor: 'pointer',
  },
  title:        { fontSize: 18, fontWeight: 600, color: '#f3f4f6', flex: 1, margin: 0 },
  topicRow:     { display: 'flex', gap: 10, marginBottom: 18 },
  topicInput:   {
    flex: 1, background: '#0f1117', border: '1px solid #374151', borderRadius: 7,
    padding: '9px 12px', color: '#e5e7eb', fontSize: 14, outline: 'none',
  },
  btnGenerate:  {
    padding: '9px 18px', background: '#6366f1', border: 'none', borderRadius: 7,
    color: 'white', fontSize: 13, fontWeight: 600, cursor: 'pointer', whiteSpace: 'nowrap',
  },
  btnDisabled:  { background: '#374151', cursor: 'not-allowed', color: '#6b7280' },
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
  btnAddUrl:    {
    padding: '7px 14px', background: '#374151', border: 'none', borderRadius: 6,
    color: '#e5e7eb', fontSize: 12, fontWeight: 600, cursor: 'pointer', whiteSpace: 'nowrap',
  },
  numCardsWrap: { display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 },
  numCardsLabel: { fontSize: 12, color: '#9ca3af', whiteSpace: 'nowrap' as const },
  numCardsInput: {
    width: 52, background: '#0f1117', border: '1px solid #374151', borderRadius: 6,
    padding: '9px 8px', color: '#e5e7eb', fontSize: 14, outline: 'none', textAlign: 'center' as const,
  },
  musicRow:     { display: 'flex', alignItems: 'center', gap: 10, marginBottom: 18 },
  musicLabel:   { fontSize: 13, color: '#9ca3af', flexShrink: 0 },
  musicSelect:  {
    flex: 1, background: '#0f1117', border: '1px solid #374151', borderRadius: 7,
    padding: '8px 12px', color: '#e5e7eb', fontSize: 13, outline: 'none',
  },
  btnRender:    {
    width: '100%', padding: '12px', background: '#059669', border: 'none',
    borderRadius: 8, color: 'white', fontSize: 14, fontWeight: 600, cursor: 'pointer', marginBottom: 20,
  },
  searchImgRow: { display: 'flex', gap: 10, marginBottom: 4 },
  addFactRow:   { marginTop: 10 },
  addFactInput: {
    width: '100%', background: '#0f1117', border: '1px solid #374151', borderRadius: 6,
    padding: '8px 10px', color: '#e5e7eb', fontSize: 13, outline: 'none',
    fontFamily: 'inherit', resize: 'vertical' as const, boxSizing: 'border-box' as const,
  },
  btnAddFact:   {
    marginTop: 10, padding: '7px 16px', background: 'transparent', border: '1px dashed #4b5563',
    borderRadius: 6, color: '#6b7280', fontSize: 12, cursor: 'pointer', width: '100%',
  },
  logCard:      {
    background: '#161b27', border: '1px solid #1f2937', borderRadius: 12, padding: '16px 18px', marginBottom: 16,
  },
  logHeader:    { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 },
  logTitle:     { fontSize: 11, fontWeight: 600, color: '#9ca3af', textTransform: 'uppercase', letterSpacing: 1 },
  logBox:       {
    background: '#0a0d14', border: '1px solid #1f2937', borderRadius: 8,
    padding: '10px 12px', height: 220, overflowY: 'auto',
    fontFamily: 'monospace', fontSize: 12, lineHeight: 1.6,
  },
  doneRow:      { marginTop: 10, display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' },
  doneBox:      {
    flex: 1, padding: '10px 14px', background: '#0522183a',
    border: '1px solid #166534', borderRadius: 7, color: '#4ade80', fontSize: 13,
  },
  btnCleanup:   {
    padding: '8px 14px', background: '#374151', border: '1px solid #4b5563',
    borderRadius: 7, color: '#d1d5db', fontSize: 12, cursor: 'pointer', whiteSpace: 'nowrap',
  },
  // Metadata
  metaCard:     {
    background: '#161b27', border: '1px solid #1f2937', borderRadius: 12,
    padding: '16px 18px', marginBottom: 16,
  },
  metaHeader:   { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 },
  metaTitle:    { fontSize: 13, fontWeight: 600, color: '#a5b4fc' },
  metaToggle:   {
    background: 'transparent', border: '1px solid #374151', borderRadius: 5,
    color: '#9ca3af', fontSize: 11, padding: '4px 10px', cursor: 'pointer',
  },
  metaBody:     { display: 'flex', flexDirection: 'column', gap: 12, marginTop: 12 },
};

// sequence card
const sq: Record<string, React.CSSProperties> = {
  card: {
    flexShrink: 0, width: 210,
    background: '#161b27', border: '1px solid #1f2937',
    borderRadius: 10, padding: 10,
    display: 'flex', flexDirection: 'column', gap: 8,
  },
  cardHeader:  { display: 'flex', alignItems: 'center', justifyContent: 'space-between' },
  cardNum:     { fontSize: 10, fontWeight: 600, color: '#6366f1', textTransform: 'uppercase', letterSpacing: 1 },
  cardActions: { display: 'flex', gap: 3, alignItems: 'center' },
  arrowBtn:    {
    background: 'transparent', border: 'none', color: '#4b5563', fontSize: 13,
    cursor: 'pointer', padding: '1px 5px', borderRadius: 4, lineHeight: 1,
  },
  deleteCardBtn: {
    background: '#7f1d1d33', border: 'none', color: '#f87171', fontSize: 13,
    cursor: 'pointer', padding: '1px 5px', borderRadius: 4, lineHeight: 1,
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
    color: '#e5e7eb', lineHeight: 1.5,
    resize: 'none', padding: '8px 24px 4px 8px',
    fontFamily: 'inherit', boxSizing: 'border-box',
    cursor: 'text',
  },
  charCount:    { fontSize: 10, color: '#4b5563', textAlign: 'right', padding: '0 8px 6px' },
  removeBtn: {
    position: 'absolute', top: 4, right: 4,
    background: '#374151', border: 'none', borderRadius: '50%',
    width: 18, height: 18, color: '#9ca3af',
    fontSize: 11, cursor: 'pointer',
    display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 0,
  },
  videoSlotContent: {
    display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
    width: '100%', height: '100%', padding: '8px 4px', boxSizing: 'border-box',
  },
  durationRow: { display: 'flex', alignItems: 'center', gap: 4, marginTop: 2 },
  durationLabel: { fontSize: 11, color: '#4b5563', flexShrink: 0 },
  durationInput: {
    flex: 1, background: '#0f1117', border: '1px solid #2d3748', borderRadius: 5,
    padding: '4px 6px', color: '#9ca3af', fontSize: 11, outline: 'none',
    textAlign: 'center' as const,
  },
  durationSuffix: { fontSize: 11, color: '#4b5563', flexShrink: 0 },
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
  imgGrid:    { display: 'flex', flexWrap: 'wrap', gap: 10, overflow: 'visible' },
  imgWrapOuter: {
    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4, flexShrink: 0,
  },
  imgWrap: {
    position: 'relative', width: 90, aspectRatio: '2/3',
    border: '2px solid #1f2937', borderRadius: 7, overflow: 'hidden',
    cursor: 'grab',
  },
  img:       { width: '100%', height: '100%', objectFit: 'cover', display: 'block' },
  dragHint:  {
    position: 'absolute', bottom: 3, right: 5,
    fontSize: 9, color: 'rgba(255,255,255,0.35)', pointerEvents: 'none',
  },
  imgAssignBtn: {
    background: '#1e1b4b', border: '1px solid #4f46e5', borderRadius: 5,
    color: '#a5b4fc', fontSize: 12, padding: '2px 10px', cursor: 'pointer', width: '100%',
  },
  factGrid:  { display: 'flex', flexDirection: 'column', gap: 6 },
  factCard:  {
    display: 'flex', alignItems: 'flex-start', gap: 8,
    background: '#161b27', border: '1px solid #1f2937',
    borderRadius: 8, padding: '10px 10px 10px 14px', cursor: 'grab',
  },
  dragHandle: { color: '#4b5563', fontSize: 16, flexShrink: 0, marginTop: 1 },
  factText:   { fontSize: 13, color: '#d1d5db', lineHeight: 1.45, flex: 1 },
  assignBtn:  {
    background: '#1e1b4b', border: '1px solid #4f46e5', borderRadius: 5,
    color: '#a5b4fc', fontSize: 13, padding: '2px 8px', cursor: 'pointer',
    flexShrink: 0, alignSelf: 'center',
  },
  videoChipWrap: {
    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4, flexShrink: 0,
  },
  videoChip: {
    display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
    gap: 4, width: 90, height: 60, border: '2px solid #374151', borderRadius: 7,
    background: '#1f2937', cursor: 'grab', padding: 6,
  },
  uploadWrap: { display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4, flexShrink: 0 },
  uploadBtn:  { cursor: 'pointer', border: '2px dashed #374151', background: 'transparent' },
};

// metadata sections
const ms: Record<string, React.CSSProperties> = {
  section: {
    background: '#0f1117', border: '1px solid #1f2937', borderRadius: 8, padding: '12px 14px',
  },
  label:   { fontSize: 10, fontWeight: 600, color: '#6b7280', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 6 },
  content: {
    fontSize: 13, color: '#e5e7eb', lineHeight: 1.5, margin: 0,
    fontFamily: 'inherit', whiteSpace: 'pre-wrap' as const, wordBreak: 'break-word' as const,
  },
  copyBtn: {
    marginTop: 8, padding: '5px 12px', background: '#374151', border: 'none',
    borderRadius: 5, color: '#9ca3af', fontSize: 11, cursor: 'pointer',
  },
};
