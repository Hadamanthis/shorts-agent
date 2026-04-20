import {
  AbsoluteFill,
  OffthreadVideo,
  staticFile,
  Img,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
} from 'remotion';
import { Html5Audio } from 'remotion';

export type ComentarioImagemProps = {
  hook: string;
  story: string;
  comentario: string;
  nome: string;
  imagem: string;
  highlights?: string[];
  avatar?: string;
  bgVideo?: string;
  music?: string;
};

// ── Cores ─────────────────────────────────────────────────────────────────────
const GOLD = '#FFD700';

// Renderiza texto com palavras destacadas em dourado
const HighlightedText: React.FC<{
  text: string; fontSize: number; color?: string; highlights?: string[];
}> = ({ text, fontSize, color = 'rgba(255,255,255,0.88)', highlights = [] }) => {
  if (highlights.length === 0) {
    return <span style={{ fontSize, color, fontFamily: 'sans-serif',
                          lineHeight: 1.55, fontWeight: 400 }}>{text}</span>;
  }
  // Escapa e monta regex de match exato de palavra/expressão
  const escaped = highlights.map(h => h.trim().replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  const re = new RegExp(`(${escaped.join('|')})`, 'gi');
  const parts = text.split(re);
  return (
    <span style={{ fontSize, color, fontFamily: 'sans-serif',
                   lineHeight: 1.55, fontWeight: 400 }}>
      {parts.map((part, i) =>
        highlights.some(h => h.trim().toLowerCase() === part.toLowerCase())
          ? <span key={i} style={{ color: GOLD, fontWeight: 700 }}>{part}</span>
          : part
      )}
    </span>
  );
};

// ── Typewriter palavra por palavra — com highlight ────────────────────────────
const TypewriterStory: React.FC<{ text: string; startFrame: number; highlights?: string[] }> = ({ text, startFrame, highlights = [] }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const words = text.split(/(\s+)/);
  const FRAMES_PER_WORD = Math.round(fps / 12);
  const wordsVisible = Math.max(0, Math.floor((frame - startFrame) / FRAMES_PER_WORD));

  // Monta set de tokens individuais que fazem parte de highlights exatos
  // Ex: highlight "neve derretendo" → adiciona "neve derretendo" como chave
  // e marca cada token só se o vizinho também bater (match de frase completa)
  const hlLower = highlights.map(h => h.toLowerCase().trim());

  // Para cada posição, verifica se a partir dali começa um highlight
  const tokensFull = words; // inclui espaços
  const highlighted = new Set<number>();
  for (const hl of hlLower) {
    const hlTokens = hl.split(/\s+/);
    // percorre os tokens de palavras e tenta casar a sequência
    let wordIdx = 0;
    for (let i = 0; i < tokensFull.length; i++) {
      const tok = tokensFull[i];
      if (tok.trim().length === 0) continue; // pula espaços
      if (tok.trim().toLowerCase() === hlTokens[wordIdx]) {
        if (wordIdx === 0) {
          // possível início — tenta casar o restante
          let match = true;
          let wi = wordIdx;
          let ii = i;
          while (wi < hlTokens.length) {
            while (ii < tokensFull.length && tokensFull[ii].trim().length === 0) ii++;
            if (ii >= tokensFull.length || tokensFull[ii].trim().toLowerCase() !== hlTokens[wi]) {
              match = false; break;
            }
            ii++; wi++;
          }
          if (match) {
            // marca todos os índices da sequência
            let wi2 = 0, ii2 = i;
            while (wi2 < hlTokens.length) {
              while (ii2 < tokensFull.length && tokensFull[ii2].trim().length === 0) ii2++;
              highlighted.add(ii2);
              ii2++; wi2++;
            }
          }
        }
      }
      wordIdx = 0;
    }
  }

  let count = 0;
  const visible = words.map((token, i) => {
    const isWord = token.trim().length > 0;
    if (isWord) count++;
    const show = count <= wordsVisible;
    const isHl = highlighted.has(i);
    return (
      <span key={i} style={{
        opacity: show ? 1 : 0,
        color: isHl ? GOLD : undefined,
        fontWeight: isHl ? 700 : undefined,
      }}>
        {token}
      </span>
    );
  });

  return (
    <p style={{ margin: 0, fontSize: 30, fontFamily: 'sans-serif',
                lineHeight: 1.55, color: 'rgba(255,255,255,0.88)', fontWeight: 400 }}>
      {visible}
    </p>
  );
};

// ── Comentário — sem highlight, sem indent ────────────────────────────────────
const CommentBlock: React.FC<{ text: string }> = ({ text }) => {
  const sentences = text.match(/[^.!?]+[.!?]+/g) ?? [text];
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {sentences.map((s, i) => (
        <span key={i} style={{
          fontSize: 32, color: 'rgba(255,255,255,0.92)',
          fontFamily: 'sans-serif', lineHeight: 1.55, fontWeight: 400,
        }}>
          &nbsp;&nbsp;&nbsp;&nbsp;{s.trim()}
        </span>
      ))}
    </div>
  );
};

// ── Barra de progresso ────────────────────────────────────────────────────────
const ProgressBar: React.FC = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  return (
    <div style={{
      position: 'absolute', top: 0, left: 0, right: 0,
      height: 3, backgroundColor: 'rgba(255,255,255,0.12)', zIndex: 10,
    }}>
      <div style={{
        height: '100%',
        width: `${(frame / durationInFrames) * 100}%`,
        backgroundColor: GOLD,
        borderRadius: 2,
      }} />
    </div>
  );
};

// ── Zoom suave na imagem (topo → normal) ──────────────────────────────────────
const ZoomedImage: React.FC<{ src: string }> = ({ src }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const scale = interpolate(frame, [0, durationInFrames], [1.08, 1.0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  return (
    <div style={{
      width: '100%', minHeight: 340, maxHeight: 560, overflow: 'hidden',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      backgroundColor: '#0d0d0d',
    }}>
      <Img
        src={staticFile(src)}
        style={{
          width: '100%', minHeight: 340, maxHeight: 560,
          objectFit: 'contain', display: 'block',
          transform: `scale(${scale})`,
          transformOrigin: 'top center',
        }}
      />
    </div>
  );
};

// ── Componente principal ──────────────────────────────────────────────────────
export const ComentarioImagem: React.FC<ComentarioImagemProps> = ({
  hook, story, comentario, nome,
  imagem, highlights = [],
  avatar = 'avatar.png',
  bgVideo = 'bg_looped.mp4',
  music,
}) => {
  const { fps } = useVideoConfig();
  // Story começa após 0.5s para o espectador ler o hook primeiro
  const storyStartFrame = Math.round(fps * 0.5);

  return (
    <AbsoluteFill style={{ backgroundColor: '#000' }}>

      {/* FUNDO */}
      <OffthreadVideo
        src={staticFile(bgVideo)}
        style={{ width: '100%', height: '100%', objectFit: 'cover', opacity: 0.70 }}
        playbackRate={1}
        muted
      />
      <div style={{
        position: 'absolute', inset: 0,
        background: 'linear-gradient(180deg, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0.80) 100%)',
      }} />

      {music && <Html5Audio src={staticFile(music)} volume={0.18} loop />}

      <ProgressBar />

      {/* CARD */}
      <div style={{
        position: 'absolute',
        top: '4%', left: '4%', right: '4%',
        maxHeight: '92%',
        borderRadius: 24,
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 8px 40px rgba(0,0,0,0.7)',
      }}>

        {/* ZONA 1 — HOOK */}
        <div style={{
          backgroundColor: 'rgba(15,15,15,0.97)',
          padding: '22px 28px 20px',
          borderBottom: '1px solid rgba(255,255,255,0.08)',
          display: '-webkit-box', WebkitLineClamp: 2,
          WebkitBoxOrient: 'vertical', overflow: 'hidden',
          textShadow: '0 2px 8px rgba(0,0,0,0.8)',
          textAlign: 'center',       // ← centraliza
          fontSize: 46,
          lineHeight: 1.2,
        }}>
          <HighlightedText
            text={hook} fontSize={46} color="#FFFFFF"
            highlights={highlights}
          />
        </div>

        {/* ZONA 2 — IMAGEM com zoom */}
        <div style={{ borderBottom: '1px solid rgba(255,255,255,0.06)', flexShrink: 0 }}>
          <ZoomedImage src={imagem} />
        </div>

        {/* ZONA 2.5 — STORY typewriter com highlight */}
        <div style={{
          backgroundColor: 'rgba(22,22,22,0.98)',
          borderBottom: '1px solid rgba(255,255,255,0.08)',
          padding: '18px 28px',
          flexShrink: 0,
        }}>
          <TypewriterStory text={story} startFrame={storyStartFrame} highlights={highlights} />
        </div>

        {/* ZONA 3 — COMENTÁRIO */}
        <div style={{
          backgroundColor: 'rgba(10,10,10,0.99)',
          padding: '14px 24px 20px',
          flexShrink: 0,
          display: 'flex',
          flexDirection: 'column',
          gap: 10,
        }}>
          <div style={{
            height: 2, width: 48,
            backgroundColor: 'rgba(255,255,255,0.15)',
            borderRadius: 2, marginBottom: 2,
          }} />
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <Img
              src={staticFile(avatar)}
              style={{
                width: 48, height: 48, borderRadius: '50%',
                objectFit: 'cover', flexShrink: 0,
                outline: '2px solid rgba(255,255,255,0.15)', outlineOffset: 1,
              }}
            />
            <span style={{
              color: '#FFFFFF', fontSize: 26,
              fontFamily: 'sans-serif', fontWeight: 700, lineHeight: 1,
            }}>
              @{nome}
            </span>
          </div>
          <CommentBlock text={comentario} />
        </div>

      </div>
    </AbsoluteFill>
  );
};