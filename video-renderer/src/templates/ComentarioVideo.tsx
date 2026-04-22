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
import { Video } from '@remotion/media';

export type ComentarioVideoProps = {
  hook: string;
  story: string;
  comentario: string;
  nome: string;
  video: string;
  highlights?: string[];
  avatar?: string;
  bgVideo?: string;
  clipDurationFrames?: number;
  music?: string;
};

const GOLD = '#FFD700';

const stripPunctuation = (tok: string): string =>
  tok.replace(/^[\s.,!?;:()"'«»\-–—]+|[\s.,!?;:()"'«»\-–—]+$/g, '').toLowerCase();

const buildHighlightedIndices = (tokens: string[], highlights: string[]): Set<number> => {
  const indices = new Set<number>();
  if (highlights.length === 0) return indices;

  // Apenas match de frases completas — nunca palavras soltas
  const hlPhrases = highlights.map(hl =>
    hl.trim().split(/\s+/).map(t => stripPunctuation(t))
  );

  const wordEntries = tokens
    .map((tok, i) => ({ tok, i }))
    .filter(({ tok }) => tok.trim().length > 0);

  for (const hlTokens of hlPhrases) {
    for (let wi = 0; wi <= wordEntries.length - hlTokens.length; wi++) {
      let match = true;
      for (let k = 0; k < hlTokens.length; k++) {
        if (stripPunctuation(wordEntries[wi + k].tok) !== hlTokens[k]) {
          match = false;
          break;
        }
      }
      if (match) {
        const startIdx = wordEntries[wi].i;
        const endIdx = wordEntries[wi + hlTokens.length - 1].i;
        for (let ti = startIdx; ti <= endIdx; ti++) indices.add(ti);
      }
    }
  }

  return indices;
};


const HighlightedText: React.FC<{
  text: string; fontSize: number; color?: string; highlights?: string[];
}> = ({ text, fontSize, color = 'rgba(255,255,255,0.88)', highlights = [] }) => {
  const tokens = text.split(/(\s+)/);
  const highlightedIndices = buildHighlightedIndices(tokens, highlights);
  return (
    <span style={{ fontSize, color, fontFamily: 'sans-serif', lineHeight: 1.55, fontWeight: 400 }}>
      {tokens.map((token, i) =>
        highlightedIndices.has(i)
          ? <span key={i} style={{ color: GOLD, fontWeight: 700 }}>{token}</span>
          : <span key={i}>{token}</span>
      )}
    </span>
  );
};

const TypewriterStory: React.FC<{
  text: string; startFrame: number; highlights?: string[];
}> = ({ text, startFrame, highlights = [] }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const tokens = text.split(/(\s+)/);
  const FRAMES_PER_WORD = Math.round(fps / 12);
  const wordsVisible = Math.max(0, Math.floor((frame - startFrame) / FRAMES_PER_WORD));
  const highlightedIndices = buildHighlightedIndices(tokens, highlights);
  let wordCount = 0;
  const rendered = tokens.map((token, i) => {
    const isWord = token.trim().length > 0;
    if (isWord) wordCount++;
    const show = wordCount <= wordsVisible;
    const isHl = highlightedIndices.has(i);
    return (
      <span key={i} style={{ opacity: show ? 1 : 0, color: isHl ? GOLD : undefined, fontWeight: isHl ? 700 : undefined }}>
        {token}
      </span>
    );
  });
  return (
    <p style={{ margin: 0, fontSize: 30, fontFamily: 'sans-serif', lineHeight: 1.55, color: 'rgba(255,255,255,0.88)', fontWeight: 400 }}>
      {rendered}
    </p>
  );
};

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

const ProgressBar: React.FC = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  return (
    <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 6, backgroundColor: 'rgba(255,255,255,0.15)', zIndex: 100 }}>
      <div style={{ height: '100%', width: `${(frame / durationInFrames) * 100}%`, backgroundColor: GOLD, borderRadius: 0 }} />
    </div>
  );
};

const ClipVideo: React.FC<{ src: string; durationInFrames: number }> = ({ src, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { durationInFrames: totalFrames } = useVideoConfig();
  const scale = interpolate(frame, [0, totalFrames], [1.08, 1.0], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  return (
    <div style={{ width: '100%', minHeight: 340, maxHeight: 560, overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: '#0d0d0d' }}>
      <OffthreadVideo
        src={staticFile(src)}
        endAt={durationInFrames - 1}   // <-- nunca busca além do último frame
        style={{ width: '100%', minHeight: 340, maxHeight: 560, objectFit: 'contain', display: 'block', transform: `scale(${scale})`, transformOrigin: 'top center' }}
      />
    </div>
  );
};

export const ComentarioVideo: React.FC<ComentarioVideoProps> = ({
  hook, story, comentario, nome,
  video, highlights = [],
  avatar = 'avatar.png',
  bgVideo = 'bg_looped.mp4',
  clipDurationFrames,
  music,
}) => {
  const { fps, durationInFrames } = useVideoConfig();
  const storyStartFrame = Math.round(fps * 0.5);

  return (
    <AbsoluteFill style={{ backgroundColor: '#000' }}>

      {/* FUNDO — Loop garante que o bg reinicia antes do fim, evitando "No frame found" */}
      <Video
        src={staticFile(bgVideo)}
        loop
        muted
        style={{ width: '100%', height: '100%', objectFit: 'cover', opacity: 0.70 }}
      />
      <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(180deg, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0.80) 100%)' }} />

      {music && <Html5Audio src={staticFile(music)} volume={0.18} loop />}

      <ProgressBar />

      {/* CARD */}
      <div style={{
        position: 'absolute', top: '4%', left: '4%', right: '4%',
        maxHeight: '92%', borderRadius: 24, overflow: 'hidden',
        display: 'flex', flexDirection: 'column',
        boxShadow: '0 8px 40px rgba(0,0,0,0.7)',
      }}>

        {/* ZONA 1 — HOOK */}
        <div style={{
          backgroundColor: 'rgba(15,15,15,0.97)', padding: '22px 28px 20px',
          borderBottom: '1px solid rgba(255,255,255,0.08)',
          display: '-webkit-box', WebkitLineClamp: 2,
          WebkitBoxOrient: 'vertical', overflow: 'hidden',
          textShadow: '0 2px 8px rgba(0,0,0,0.8)', textAlign: 'center',
          fontSize: 46, lineHeight: 1.2,
        }}>
          <HighlightedText text={hook} fontSize={46} color="#FFFFFF" highlights={highlights} />
        </div>

        {/* ZONA 2 — VÍDEO com zoom, mesmas proporções da imagem */}
        <div style={{ borderBottom: '1px solid rgba(255,255,255,0.06)', flexShrink: 0 }}>
          <ClipVideo src={video} durationInFrames={clipDurationFrames ?? durationInFrames} />
        </div>

        {/* ZONA 2.5 — STORY typewriter com highlight */}
        <div style={{ backgroundColor: 'rgba(22,22,22,0.98)', borderBottom: '1px solid rgba(255,255,255,0.08)', padding: '18px 28px', flexShrink: 0 }}>
          <TypewriterStory text={story} startFrame={storyStartFrame} highlights={highlights} />
        </div>

        {/* ZONA 3 — COMENTÁRIO */}
        <div style={{ backgroundColor: 'rgba(10,10,10,0.99)', padding: '14px 24px 20px', flexShrink: 0, display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ height: 2, width: 48, backgroundColor: 'rgba(255,255,255,0.15)', borderRadius: 2, marginBottom: 2 }} />
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <Img src={staticFile(avatar)} style={{ width: 48, height: 48, borderRadius: '50%', objectFit: 'cover', flexShrink: 0, outline: '2px solid rgba(255,255,255,0.15)', outlineOffset: 1 }} />
            <span style={{ color: '#FFFFFF', fontSize: 26, fontFamily: 'sans-serif', fontWeight: 700, lineHeight: 1 }}>@{nome}</span>
          </div>
          <CommentBlock text={comentario} />
        </div>

      </div>
    </AbsoluteFill>
  );
};