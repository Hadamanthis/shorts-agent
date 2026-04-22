/**
 * video-renderer/src/ui/pages/DashboardPage.tsx
 *
 * Página 1 — Pipeline com seleção visual de posts do Reddit.
 *
 * Fluxo Reddit:
 *   1. Usuário configura subreddit/perfil/tom e clica "Buscar posts"
 *   2. API retorna lista de posts → exibida em grade visual
 *   3. Usuário clica num post → confirma → pipeline roda com --post-index
 *
 * Fluxo YouTube / URL direta:
 *   → mesmo de antes, dispara direto
 */

import React, { useEffect, useRef, useState } from 'react';
import { apiFetch } from '../AppRouter';

// ── Types ─────────────────────────────────────────────────────────────────────
interface Profile { language: string; niche: string; account_name: string }
interface Job {
  job_id: string;
  status: 'running' | 'done' | 'error';
  started_at: string;
  finished_at?: string;
  log?: string[];
}
interface SubredditSuggestion { name: string; category: string }
interface RedditPost {
  index: number;
  title: string;
  score: number;
  num_comments: number;
  post_type: 'image' | 'video';
  duration: number;
  thumbnail_url: string;
  url: string;
  permalink: string;
  subreddit: string;
  title_original?: string;  // título original em inglês (quando tradução está ativa)
}

type Step = 'form' | 'picking' | 'running';

// ── Component ─────────────────────────────────────────────────────────────────
export default function DashboardPage() {
  const [profiles, setProfiles]       = useState<Record<string, Profile>>({});
  const [suggestions, setSuggestions] = useState<SubredditSuggestion[]>([]);
  const [jobs, setJobs]               = useState<Job[]>([]);

  // Formulário
  const [template,  setTemplate]  = useState('comentario-reddit');
  const [profile,   setProfile]   = useState('Synthvator');
  const [subreddit, setSubreddit] = useState('interestingasfuck');
  const [ytUrl,     setYtUrl]     = useState('');
  const [tone,      setTone]      = useState('humoristico');
  const [imageUrl,  setImageUrl]  = useState('');
  const [videoUrl,  setVideoUrl]  = useState('');

  // Posts Reddit
  const [step,         setStep]         = useState<Step>('form');
  const [posts,        setPosts]        = useState<RedditPost[]>([]);
  const [loadingPosts, setLoadingPosts] = useState(false);
  const [selectedPost, setSelectedPost] = useState<RedditPost | null>(null);
  const [postsError,   setPostsError]   = useState('');

  // Job ativo
  const [activeJob, setActiveJob] = useState<Job | null>(null);
  const [running,   setRunning]   = useState(false);
  const logRef  = useRef<HTMLDivElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    apiFetch('/profiles').then(setProfiles).catch(() => {});
    apiFetch('/subreddits/suggestions').then(setSuggestions).catch(() => {});
    apiFetch('/jobs').then(setJobs).catch(() => {});
  }, []);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [activeJob?.log?.length]);

  // Reset post selection when subreddit/profile changes
  useEffect(() => {
    setPosts([]);
    setSelectedPost(null);
    setPostsError('');
    if (step === 'picking') setStep('form');
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [subreddit, profile]);

  function startPolling(jobId: string) {
    pollRef.current = setInterval(async () => {
      try {
        const job: Job = await apiFetch(`/run/${jobId}`);
        setActiveJob(job);
        if (job.status !== 'running') {
          clearInterval(pollRef.current!);
          setRunning(false);
          apiFetch('/jobs').then(setJobs).catch(() => {});
        }
      } catch {
        clearInterval(pollRef.current!);
        setRunning(false);
      }
    }, 800);
  }

  async function handleFetchPosts() {
    setLoadingPosts(true);
    setPostsError('');
    setPosts([]);
    setSelectedPost(null);
    try {
      const data = await apiFetch(
        `/posts?subreddit=${encodeURIComponent(subreddit)}&profile=${encodeURIComponent(profile)}&translate=true`
      );
      setPosts(data.posts ?? []);
      setStep('picking');
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setPostsError(msg || 'Erro ao buscar posts. API está rodando?');
    } finally {
      setLoadingPosts(false);
    }
  }

  async function handleRun(postIndex?: number) {
    if (running) return;
    setRunning(true);
    setStep('running');
    setActiveJob({ job_id: '...', status: 'running', started_at: new Date().toISOString(), log: [] });

    const body: Record<string, unknown> = { template, profile, comment_tone: tone };

    if (template === 'comentario-reddit') {
      if (imageUrl)                     body.image_url  = imageUrl;
      else if (videoUrl)                body.video_url  = videoUrl;
      else if (postIndex !== undefined) { body.post_index = postIndex; body.subreddit = subreddit; }
      else                              body.subreddit  = subreddit;
    } else {
      body.url = ytUrl;
    }

    try {
      const { job_id } = await apiFetch('/run', {
        method: 'POST',
        body: JSON.stringify(body),
      });
      startPolling(job_id);
    } catch {
      alert(
        'Não foi possível conectar na API.\n\n' +
        'Certifique-se que o servidor está rodando:\n' +
        '  cd shorts-creator-agent\n' +
        '  uvicorn api:app --reload --port 8000'
      );
      setRunning(false);
      setActiveJob(null);
      setStep('form');
    }
  }

  const isReddit    = template === 'comentario-reddit';
  const useDirectUrl = isReddit && (!!imageUrl || !!videoUrl);

  return (
    <div style={s.page}>
      <h1 style={s.pageTitle}>Pipeline</h1>

      <div style={s.grid}>
        {/* ── Formulário ── */}
        <section style={s.card}>
          <h2 style={s.cardTitle}>Novo short</h2>

          <Field label="Template">
            <select style={s.select} value={template}
              onChange={e => { setTemplate(e.target.value); setStep('form'); }}>
              <option value="comentario-reddit">Reddit</option>
              <option value="comentario-youtube">YouTube</option>
            </select>
          </Field>

          <Field label="Perfil de canal">
            <select style={s.select} value={profile} onChange={e => setProfile(e.target.value)}>
              {Object.entries(profiles).map(([k, v]) => (
                <option key={k} value={k}>{k} — {v.niche}</option>
              ))}
              {Object.keys(profiles).length === 0 && (
                <option value="Synthvator">Synthvator (API offline)</option>
              )}
            </select>
          </Field>

          <Field label="Tom do comentário">
            <select style={s.select} value={tone} onChange={e => setTone(e.target.value)}>
              {['surpreso', 'humoristico', 'reflexivo', 'emocional', 'assustado'].map(t => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </Field>

          {isReddit ? (
            <>
              <Field label="Subreddit">
                <input
                  style={s.input}
                  value={subreddit}
                  onChange={e => setSubreddit(e.target.value)}
                  placeholder="interestingasfuck"
                />
                {suggestions.length > 0 && (
                  <div style={s.chips}>
                    {suggestions.map(sub => (
                      <button
                        key={sub.name}
                        style={{ ...s.chip, ...(subreddit === sub.name ? s.chipActive : {}) }}
                        onClick={() => setSubreddit(sub.name)}
                        title={sub.category}
                      >
                        r/{sub.name}
                      </button>
                    ))}
                  </div>
                )}
              </Field>

              <Field label="URL direta (opcional — pula seleção)">
                <input
                  style={s.input}
                  value={imageUrl}
                  onChange={e => { setImageUrl(e.target.value); setVideoUrl(''); setStep('form'); }}
                  placeholder="https://i.redd.it/... (imagem)"
                />
                <input
                  style={{ ...s.input, marginTop: 6 }}
                  value={videoUrl}
                  onChange={e => { setVideoUrl(e.target.value); setImageUrl(''); setStep('form'); }}
                  placeholder="https://v.redd.it/... (vídeo)"
                />
              </Field>

              {useDirectUrl ? (
                <button
                  style={{ ...s.btnRun, ...(running ? s.btnDisabled : {}) }}
                  onClick={() => handleRun()}
                  disabled={running}
                >
                  {running ? '⟳  Executando...' : '▶  Gerar short'}
                </button>
              ) : (
                <button
                  style={{ ...s.btnFetch, ...(loadingPosts || running ? s.btnDisabled : {}) }}
                  onClick={handleFetchPosts}
                  disabled={loadingPosts || running}
                >
                  {loadingPosts ? '⟳  Buscando Assets' : '🔍  Buscar posts do Reddit'}
                </button>
              )}

              {postsError && <div style={s.errorBox}>{postsError}</div>}
            </>
          ) : (
            <>
              <Field label="URL do YouTube">
                <input
                  style={s.input}
                  value={ytUrl}
                  onChange={e => setYtUrl(e.target.value)}
                  placeholder="https://youtube.com/watch?v=..."
                />
              </Field>
              <button
                style={{ ...s.btnRun, ...(running ? s.btnDisabled : {}) }}
                onClick={() => handleRun()}
                disabled={running}
              >
                {running ? '⟳  Executando...' : '▶  Gerar short'}
              </button>
            </>
          )}
        </section>

        {/* ── Painel direito: seleção de posts OU log ── */}
        <section style={s.card}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
            <h2 style={s.cardTitle}>
              {step === 'picking' ? `Posts de r/${subreddit}` : 'Log ao vivo'}
            </h2>
            {activeJob && step === 'running' && <StatusBadge status={activeJob.status} />}
          </div>

          {step === 'picking' ? (
            <PostPicker
              posts={posts}
              selectedPost={selectedPost}
              onSelect={setSelectedPost}
              onConfirm={(post) => handleRun(post.index)}
              onBack={() => setStep('form')}
            />
          ) : (
            <div ref={logRef} style={s.logBox}>
              {!activeJob
                ? <span style={s.logEmpty}>Nenhum job iniciado ainda.</span>
                : activeJob.log?.map((line, i) => (
                    <div key={i} style={s.logLine}>
                      <span style={s.logArrow}>›</span>
                      <span style={lineColor(line)}>{line}</span>
                    </div>
                  ))
              }
              {running && <span style={{ color: '#6366f1' }}>▌</span>}
            </div>
          )}
        </section>
      </div>

      {/* ── Histórico ── */}
      {jobs.length > 0 && (
        <section style={{ ...s.card, marginTop: 16 }}>
          <h2 style={s.cardTitle}>Jobs desta sessão</h2>
          <table style={s.table}>
            <thead>
              <tr>{['Job ID', 'Status', 'Início', 'Fim'].map(h => (
                <th key={h} style={s.th}>{h}</th>
              ))}</tr>
            </thead>
            <tbody>
              {jobs.map(j => (
                <tr key={j.job_id} style={s.tr}>
                  <td style={s.td}><code style={s.code}>{j.job_id}</code></td>
                  <td style={s.td}><StatusBadge status={j.status} /></td>
                  <td style={s.td}>{fmtTime(j.started_at)}</td>
                  <td style={s.td}>{j.finished_at ? fmtTime(j.finished_at) : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}

// ── Post Picker ───────────────────────────────────────────────────────────────
const API_BASE = 'http://localhost:8000';

function PostPicker({
  posts,
  selectedPost,
  onSelect,
  onConfirm,
  onBack,
}: {
  posts: RedditPost[];
  selectedPost: RedditPost | null;
  onSelect: (p: RedditPost) => void;
  onConfirm: (p: RedditPost) => void;
  onBack: () => void;
}) {
  const [page, setPage] = useState(0);
  const PAGE = 4;  // 2 colunas × 2 linhas — cards maiores
  const totalPages = Math.max(1, Math.ceil(posts.length / PAGE));
  const pagePosts  = posts.slice(page * PAGE, page * PAGE + PAGE);

  if (posts.length === 0) {
    return <div style={{ color: '#6b7280', fontStyle: 'italic', fontSize: 13 }}>Nenhum post encontrado.</div>;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={ps.grid}>
        {pagePosts.map(post => {
          const isSelected = selectedPost?.index === post.index;
          // Usa proxy para evitar CORS — API serve a imagem do Reddit CDN
          const thumbSrc = post.thumbnail_url
            ? `${API_BASE}/image-proxy?url=${encodeURIComponent(post.thumbnail_url)}`
            : null;
          return (
            <div
              key={post.index}
              style={{ ...ps.card, ...(isSelected ? ps.cardSelected : {}) }}
              onClick={() => onSelect(post)}
            >
              <div style={ps.thumb}>
                {thumbSrc
                  ? <img src={thumbSrc} alt="" style={ps.thumbImg} onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }} />
                  : null
                }
                <div style={{ ...ps.thumbPlaceholder, ...(thumbSrc ? { opacity: 0 } : {}) }}>
                  {post.post_type === 'video' ? '🎬' : '🖼'}
                </div>
                <span style={ps.typeTag}>
                  {post.post_type === 'video' ? `🎬 ${post.duration}s` : '🖼 img'}
                </span>
                {isSelected && <div style={ps.checkmarkOverlay}>✓</div>}
              </div>
              <div style={ps.info}>
                <div style={ps.title} title={post.title_original ? `Original: ${post.title_original}` : undefined}>
                  {post.title}
                </div>
                <div style={ps.meta}>
                  <span>⬆ {fmtNum(post.score)}</span>
                  <span>💬 {fmtNum(post.num_comments)}</span>
                  {post.title_original && <span style={{ color: '#4b5563', fontSize: 10 }}>🌐 traduzido</span>}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div style={ps.pagination}>
        <button
          style={{ ...ps.pageBtn, ...(page === 0 ? ps.pageBtnDisabled : {}) }}
          onClick={() => setPage(p => Math.max(0, p - 1))}
          disabled={page === 0}
        >◀</button>
        <span style={{ color: '#6b7280', fontSize: 12 }}>{page + 1} / {totalPages}</span>
        <button
          style={{ ...ps.pageBtn, ...(page >= totalPages - 1 ? ps.pageBtnDisabled : {}) }}
          onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
          disabled={page >= totalPages - 1}
        >▶</button>
      </div>

      <div style={ps.actions}>
        <button style={ps.btnBack} onClick={onBack}>← Voltar</button>
        <button
          style={{ ...ps.btnConfirm, ...(!selectedPost ? ps.btnConfirmDisabled : {}) }}
          onClick={() => selectedPost && onConfirm(selectedPost)}
          disabled={!selectedPost}
        >
          ▶ Usar este post
        </button>
      </div>
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────
function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <label style={s.label}>{label}</label>
      {children}
    </div>
  );
}

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

// ── Helpers ───────────────────────────────────────────────────────────────────
function lineColor(line: string): React.CSSProperties {
  if (line.includes('ERROR') || line.includes('error')) return { color: '#f87171' };
  if (line.includes('WARNING'))                          return { color: '#fbbf24' };
  if (line.includes('✓') || line.toLowerCase().includes('done') || line.includes('gerado'))
    return { color: '#4ade80' };
  return { color: '#d1d5db' };
}

function fmtTime(iso: string) {
  return new Date(iso).toLocaleTimeString('pt-BR', {
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });
}

function fmtNum(n: number) {
  return n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n);
}

// ── Styles — dashboard ────────────────────────────────────────────────────────
const s: Record<string, React.CSSProperties> = {
  page:      { padding: '28px 32px', boxSizing: 'border-box' },
  pageTitle: { fontSize: 22, fontWeight: 600, marginBottom: 20, color: '#f3f4f6' },
  grid:      { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 },
  card: {
    background: '#161b27', border: '1px solid #1f2937',
    borderRadius: 12, padding: '20px 22px',
  },
  cardTitle: {
    fontSize: 11, fontWeight: 600, color: '#6b7280', marginBottom: 16,
    letterSpacing: 1, textTransform: 'uppercase' as const,
  },
  label: { display: 'block', fontSize: 12, color: '#9ca3af', marginBottom: 6 },
  input: {
    width: '100%', background: '#0f1117', border: '1px solid #374151',
    borderRadius: 7, padding: '8px 10px', color: '#e5e7eb', fontSize: 13,
    boxSizing: 'border-box' as const, outline: 'none',
  },
  select: {
    width: '100%', background: '#0f1117', border: '1px solid #374151',
    borderRadius: 7, padding: '8px 10px', color: '#e5e7eb', fontSize: 13,
  },
  chips: { display: 'flex', flexWrap: 'wrap' as const, gap: 5, marginTop: 8 },
  chip: {
    fontSize: 11, padding: '4px 9px', borderRadius: 20,
    background: '#1f2937', border: '1px solid #374151',
    color: '#9ca3af', cursor: 'pointer',
  },
  chipActive: { background: '#312e81', borderColor: '#6366f1', color: '#a5b4fc' },
  btnRun: {
    width: '100%', padding: '10px 16px', background: '#6366f1',
    border: 'none', borderRadius: 8, color: 'white',
    fontSize: 14, fontWeight: 600, cursor: 'pointer', marginTop: 6,
  },
  btnFetch: {
    width: '100%', padding: '10px 16px', background: '#0f766e',
    border: 'none', borderRadius: 8, color: 'white',
    fontSize: 14, fontWeight: 600, cursor: 'pointer', marginTop: 6,
  },
  btnDisabled: { background: '#374151', cursor: 'not-allowed' },
  logBox: {
    background: '#0a0d14', border: '1px solid #1f2937', borderRadius: 8,
    padding: '12px 14px', height: 340, overflowY: 'auto' as const,
    fontFamily: 'monospace', fontSize: 12, lineHeight: 1.6,
  },
  logEmpty:  { color: '#4b5563', fontStyle: 'italic' as const, fontSize: 13 },
  logLine:   { display: 'flex', gap: 6 },
  logArrow:  { color: '#374151', flexShrink: 0 },
  errorBox: {
    marginTop: 10, padding: '10px 12px', background: '#7f1d1d22',
    border: '1px solid #7f1d1d', borderRadius: 7, color: '#f87171', fontSize: 12,
  },
  table: { width: '100%', borderCollapse: 'collapse' as const },
  th: {
    fontSize: 11, color: '#6b7280', textAlign: 'left' as const,
    padding: '6px 10px', borderBottom: '1px solid #1f2937',
    textTransform: 'uppercase' as const, letterSpacing: 0.5,
  },
  tr: { borderBottom: '1px solid #1f2937' },
  td: { fontSize: 13, color: '#d1d5db', padding: '10px 10px' },
  code: { fontFamily: 'monospace', fontSize: 11, color: '#9ca3af' },
};

// ── Styles — post picker ──────────────────────────────────────────────────────
const ps: Record<string, React.CSSProperties> = {
  grid: {
    display: 'grid', gridTemplateColumns: '1fr 1fr',  // 2 colunas
    gap: 10,
  },
  card: {
    position: 'relative', background: '#0f1117', borderRadius: 8,
    border: '2px solid #1f2937', cursor: 'pointer', overflow: 'hidden',
  },
  cardSelected: {
    borderColor: '#6366f1', background: '#1e1b4b',
  },
  thumb: {
    position: 'relative', width: '100%', paddingTop: '56.25%',
    background: '#1a1f2e', overflow: 'hidden',
  },
  thumbImg: {
    position: 'absolute', inset: 0,
    width: '100%', height: '100%', objectFit: 'cover' as const,
  },
  thumbPlaceholder: {
    position: 'absolute', inset: 0,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    fontSize: 28, color: '#374151',
  },
  typeTag: {
    position: 'absolute', bottom: 6, right: 6,
    fontSize: 11, background: '#000000bb', color: '#e5e7eb',
    padding: '3px 8px', borderRadius: 4, fontWeight: 500,
  },
  checkmarkOverlay: {
    position: 'absolute', top: 8, left: 8, width: 24, height: 24,
    background: '#6366f1', borderRadius: '50%', display: 'flex',
    alignItems: 'center', justifyContent: 'center',
    fontSize: 13, color: 'white', fontWeight: 700,
    boxShadow: '0 0 0 2px #1e1b4b',
  },
  info:  { padding: '10px 10px 10px' },
  title: {
    fontSize: 12, color: '#e5e7eb', lineHeight: 1.45,
    display: '-webkit-box', WebkitLineClamp: 3,
    WebkitBoxOrient: 'vertical' as const, overflow: 'hidden', marginBottom: 6,
  },
  meta: { display: 'flex', gap: 12, fontSize: 11, color: '#9ca3af' },
  pagination: {
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    gap: 12,
  },
  pageBtn: {
    background: '#1f2937', border: '1px solid #374151', color: '#d1d5db',
    borderRadius: 6, padding: '4px 12px', cursor: 'pointer', fontSize: 13,
  },
  pageBtnDisabled: { opacity: 0.4, cursor: 'not-allowed' },
  actions: { display: 'flex', gap: 8 },
  btnBack: {
    flex: 1, padding: '9px 0', background: 'transparent',
    border: '1px solid #374151', borderRadius: 7, color: '#9ca3af',
    fontSize: 13, cursor: 'pointer',
  },
  btnConfirm: {
    flex: 2, padding: '9px 0', background: '#6366f1',
    border: 'none', borderRadius: 7, color: 'white',
    fontSize: 13, fontWeight: 600, cursor: 'pointer',
  },
  btnConfirmDisabled: { background: '#374151', cursor: 'not-allowed' },
};