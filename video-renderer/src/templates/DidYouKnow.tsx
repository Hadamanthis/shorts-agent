/**
 * templates/DidYouKnow.tsx — redesenhado
 *
 * Animações:
 *  - Ken Burns: 4 padrões de zoom/pan ciclados por card
 *  - "VOCÊ SABIA?": spring scale-in + underline animado
 *  - Fato: word-by-word reveal com slide-up
 *  - Progress bar: depleção L→R mostrando tempo restante
 *  - Flash roxo sutil na transição entre cards
 *  - Fade de entrada/saída por card
 *
 * Layout safe zones (1080×1920):
 *  - Top 0-160: conta + dots
 *  - 160-420: "VOCÊ SABIA?" + barra de progresso
 *  - 420-1600: texto do fato (zona central)
 *  - 1600-1920: LIVRE (botões do Instagram/TikTok)
 */

import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Img,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

export interface DYKFact {
  text: string;
  image: string;
}

export interface DidYouKnowProps {
  facts?: DYKFact[];
  cardFrames?: number;
  cardFramesList?: number[];  // duração por card em frames; sobrepõe cardFrames
  music?: string;
  nome?: string;
  avatar?: string;
}

const FADE       = 15;  // frames para fade in/out
const TEXT_START = 22;  // frame em que o texto começa a aparecer
const WORD_GAP   = 4;   // frames entre cada palavra

export const DidYouKnow: React.FC<DidYouKnowProps> = ({
  facts: factsProp,
  cardFrames = 270,
  cardFramesList,
  music,
  nome,
  avatar,
}) => {
  const facts = factsProp ?? [];
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const defaultFrames = Math.max(cardFrames, FADE * 3 + 30);
  // Resolve lista de frames por card — garante mínimo por card
  const framesList = (cardFramesList && cardFramesList.length === facts.length)
    ? cardFramesList.map(f => Math.max(f, FADE * 3 + 30))
    : facts.map(() => defaultFrames);

  // Mapeamento frame global → cardIndex + cardFrame (frame dentro do card)
  let cardIndex = facts.length - 1;
  let cardFrame = 0;
  let remaining = frame;
  for (let i = 0; i < framesList.length; i++) {
    if (remaining < framesList[i]) {
      cardIndex = i;
      cardFrame = remaining;
      break;
    }
    remaining -= framesList[i];
  }
  cardIndex = Math.min(cardIndex, facts.length - 1);

  const safeCardFrames = framesList[cardIndex] ?? defaultFrames;
  const fact = facts[cardIndex];
  if (!fact) return null;

  // ── Card fade ────────────────────────────────────────────────────────────
  const fadeIn    = interpolate(cardFrame, [0, FADE], [0, 1], { extrapolateRight: 'clamp' });
  const fadeOut   = cardIndex < facts.length - 1
    ? interpolate(cardFrame, [safeCardFrames - FADE, safeCardFrames], [1, 0], { extrapolateLeft: 'clamp' })
    : 1;
  const cardOpacity = Math.min(fadeIn, fadeOut);

  // ── Ken Burns — 4 padrões ────────────────────────────────────────────────
  const pattern     = cardIndex % 4;
  const kenScale    = interpolate(cardFrame, [0, safeCardFrames], pattern < 2 ? [1.0, 1.10] : [1.10, 1.0]);
  const kenX        = interpolate(cardFrame, [0, safeCardFrames],
    pattern === 0 ? [-25, 25] : pattern === 1 ? [25, -25] : [0, 0]);
  const kenY        = interpolate(cardFrame, [0, safeCardFrames],
    pattern === 2 ? [-18, 18] : pattern === 3 ? [18, -18] : [0, 0]);

  // ── Header animations ────────────────────────────────────────────────────
  const headerSpring  = spring({ frame: cardFrame, fps, config: { damping: 14, stiffness: 160 } });
  const headerScale   = interpolate(headerSpring, [0, 1], [0.75, 1]);
  const headerOpacity = interpolate(cardFrame, [0, 14], [0, 1], { extrapolateRight: 'clamp' });
  const underlineW    = interpolate(headerSpring, [0, 1], [0, 100]);

  // ── Progress bar ─────────────────────────────────────────────────────────
  const progressW = interpolate(cardFrame, [0, safeCardFrames], [100, 0], { extrapolateRight: 'clamp' });

  // ── Transition flash ─────────────────────────────────────────────────────
  const flashOpacity = interpolate(cardFrame, [0, 12], [0.20, 0], { extrapolateRight: 'clamp' });

  // ── Word reveal ──────────────────────────────────────────────────────────
  const words = fact.text.split(' ');

  return (
    <AbsoluteFill style={{ background: '#000', fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      {music && <Audio src={staticFile(music)} volume={0.22} />}

      <AbsoluteFill style={{ opacity: cardOpacity }}>

        {/* Ken Burns image */}
        <AbsoluteFill style={{ overflow: 'hidden' }}>
          <Img
            src={staticFile(fact.image)}
            style={{
              width: '100%', height: '100%', objectFit: 'cover',
              transform: `scale(${kenScale}) translate(${kenX}px, ${kenY}px)`,
              transformOrigin: 'center center',
            }}
          />
        </AbsoluteFill>

        {/* Gradient — heavy top & bottom, transparent middle */}
        <AbsoluteFill style={{
          background: [
            'linear-gradient(to bottom,',
            'rgba(0,0,0,0.82) 0%,',
            'rgba(0,0,0,0.45) 20%,',
            'rgba(0,0,0,0.10) 42%,',
            'rgba(0,0,0,0.10) 58%,',
            'rgba(0,0,0,0.55) 75%,',
            'rgba(0,0,0,0.88) 100%)',
          ].join(' '),
        }} />

        {/* Transition flash */}
        <AbsoluteFill style={{ background: '#4f46e5', opacity: flashOpacity, pointerEvents: 'none' }} />

        {/* ── Account — top left ────────────────────────────────────────── */}
        <div style={{
          position: 'absolute', top: 72, left: 60,
          display: 'flex', alignItems: 'center', gap: 18,
          opacity: headerOpacity,
        }}>
          {avatar && (
            <Img
              src={staticFile(avatar)}
              style={{
                width: 64, height: 64, borderRadius: '50%', objectFit: 'cover',
                border: '2.5px solid rgba(255,255,255,0.45)',
              }}
            />
          )}
          {nome && (
            <span style={{
              color: 'rgba(255,255,255,0.90)', fontSize: 30,
              fontWeight: 600, letterSpacing: -0.5,
            }}>
              @{nome}
            </span>
          )}
        </div>

        {/* ── Card indicator dots — top right ───────────────────────────── */}
        <div style={{
          position: 'absolute', top: 88, right: 60,
          display: 'flex', gap: 8, alignItems: 'center',
          opacity: headerOpacity,
        }}>
          {facts.map((_, i) => (
            <div key={i} style={{
              width: i === cardIndex ? 28 : 8, height: 8, borderRadius: 4,
              background: i === cardIndex ? '#6366f1' : 'rgba(255,255,255,0.28)',
            }} />
          ))}
        </div>

        {/* ── "VOCÊ SABIA?" ─────────────────────────────────────────────── */}
        <div style={{
          position: 'absolute', top: 200, left: 0, right: 0,
          display: 'flex', flexDirection: 'column', alignItems: 'center',
          transform: `scale(${headerScale})`,
          opacity: headerOpacity,
        }}>
          <span style={{
            color: '#ffffff',
            fontSize: 78,
            fontWeight: 900,
            letterSpacing: 8,
            textTransform: 'uppercase',
            textShadow: '0 0 50px rgba(99,102,241,0.75), 0 4px 24px rgba(0,0,0,1)',
            lineHeight: 1,
          }}>
            VOCÊ SABIA?
          </span>

          {/* Underline animado */}
          <div style={{
            width: '72%', height: 5, background: 'rgba(255,255,255,0.12)',
            borderRadius: 3, marginTop: 18, overflow: 'hidden',
          }}>
            <div style={{
              width: `${underlineW}%`, height: '100%',
              background: 'linear-gradient(to right, #6366f1, #a78bfa)',
              borderRadius: 3,
            }} />
          </div>
        </div>

        {/* ── Progress bar (tempo restante) ─────────────────────────────── */}
        <div style={{
          position: 'absolute', top: 378, left: 60, right: 60,
          height: 4, background: 'rgba(255,255,255,0.10)', borderRadius: 2, overflow: 'hidden',
          opacity: headerOpacity,
        }}>
          <div style={{
            width: `${progressW}%`, height: '100%',
            background: 'linear-gradient(to right, #6366f1, #818cf8)',
            borderRadius: 2,
          }} />
        </div>

        {/* ── Contador de card ──────────────────────────────────────────── */}
        <div style={{
          position: 'absolute', top: 406, left: 60,
          display: 'flex', alignItems: 'center', gap: 10,
          opacity: headerOpacity,
        }}>
          <div style={{
            background: 'rgba(99,102,241,0.22)',
            border: '1px solid rgba(99,102,241,0.50)',
            borderRadius: 6, padding: '5px 14px',
          }}>
            <span style={{
              color: '#a5b4fc', fontSize: 22, fontWeight: 700,
              letterSpacing: 2, textTransform: 'uppercase',
            }}>
              Fato {cardIndex + 1} de {facts.length}
            </span>
          </div>
        </div>

        {/* ── Texto do fato — word-by-word ──────────────────────────────── */}
        <div style={{
          position: 'absolute',
          top: 520,
          left: 72, right: 72,
        }}>
          <p style={{
            margin: 0,
            fontSize: 58,
            fontWeight: 700,
            lineHeight: 1.28,
            color: '#ffffff',
            textShadow: '0 4px 28px rgba(0,0,0,0.95)',
            wordBreak: 'break-word' as const,
          }}>
            {words.map((word, i) => {
              const start    = TEXT_START + i * WORD_GAP;
              const wOpacity = interpolate(cardFrame, [start, start + 8], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
              const wY       = interpolate(cardFrame, [start, start + 8], [22, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
              return (
                <span
                  key={i}
                  style={{
                    opacity: wOpacity,
                    display: 'inline-block',
                    transform: `translateY(${wY}px)`,
                    marginRight: '0.24em',
                  }}
                >
                  {word}
                </span>
              );
            })}
          </p>
        </div>

      </AbsoluteFill>
    </AbsoluteFill>
  );
};
