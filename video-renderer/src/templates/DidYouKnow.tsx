/**
 * templates/DidYouKnow.tsx
 *
 * Template "Did You Know?" — sequência de cards fullscreen.
 * Cada card: imagem de fundo + gradiente + texto do fato.
 * Transição: fade entre cards.
 */

import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Img,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

export interface DYKFact {
  text: string;
  image: string; // filename in public/
}

export interface DidYouKnowProps {
  facts?: DYKFact[];
  cardFrames?: number; // frames per card, default 270 (9s @ 30fps)
  music?: string;
  nome?: string;
  avatar?: string;
}

const FADE = 15; // frames for fade in/out

export const DidYouKnow: React.FC<DidYouKnowProps> = ({
  facts: factsProp,
  cardFrames = 270,
  music,
  nome,
  avatar,
}) => {
  const facts = factsProp ?? [];
  const frame = useCurrentFrame();
  useVideoConfig();

  const safeCardFrames = Math.max(cardFrames, FADE * 3);
  const cardIndex = Math.min(
    Math.floor(frame / safeCardFrames),
    facts.length - 1
  );
  const cardFrame = frame - cardIndex * safeCardFrames;

  const fact = facts[cardIndex];
  if (!fact) return null;

  const fadeIn  = interpolate(cardFrame, [0, FADE], [0, 1], { extrapolateRight: 'clamp' });
  const fadeOut = cardIndex < facts.length - 1
    ? interpolate(cardFrame, [safeCardFrames - FADE, safeCardFrames], [1, 0], { extrapolateLeft: 'clamp' })
    : 1;
  const opacity = Math.min(fadeIn, fadeOut);

  // Slide text up slightly as it fades in
  const textY = interpolate(cardFrame, [0, FADE], [30, 0], { extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ background: '#000', fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      {music && <Audio src={staticFile(music)} volume={0.25} />}

      <AbsoluteFill style={{ opacity }}>
        {/* Background image */}
        <Img
          src={staticFile(fact.image)}
          style={{ width: '100%', height: '100%', objectFit: 'cover' }}
        />

        {/* Gradient overlays */}
        <AbsoluteFill style={{
          background: 'linear-gradient(to bottom, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0) 35%, rgba(0,0,0,0) 45%, rgba(0,0,0,0.75) 70%, rgba(0,0,0,0.95) 100%)',
        }} />

        {/* Top — "Você sabia?" label */}
        <div style={{
          position: 'absolute',
          top: 90,
          left: 0,
          right: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 8,
        }}>
          <span style={{
            color: '#818cf8',
            fontSize: 28,
            fontWeight: 700,
            letterSpacing: 4,
            textTransform: 'uppercase',
          }}>
            Você sabia?
          </span>
          <div style={{ width: 48, height: 3, background: '#6366f1', borderRadius: 2 }} />
        </div>

        {/* Card dots (progress) */}
        <div style={{
          position: 'absolute',
          top: 90,
          right: 60,
          display: 'flex',
          flexDirection: 'column',
          gap: 7,
          alignItems: 'center',
        }}>
          {facts.map((_, i) => (
            <div
              key={i}
              style={{
                width: i === cardIndex ? 10 : 7,
                height: i === cardIndex ? 10 : 7,
                borderRadius: '50%',
                background: i === cardIndex ? '#6366f1' : 'rgba(255,255,255,0.35)',
                transition: 'all 0.3s',
              }}
            />
          ))}
        </div>

        {/* Fact text — bottom area */}
        <div style={{
          position: 'absolute',
          bottom: 120,
          left: 60,
          right: 60,
          transform: `translateY(${textY}px)`,
        }}>
          {/* Fact number */}
          <div style={{
            fontSize: 14,
            fontWeight: 600,
            color: '#6366f1',
            letterSpacing: 2,
            textTransform: 'uppercase',
            marginBottom: 16,
          }}>
            Fato {cardIndex + 1} de {facts.length}
          </div>

          {/* The fact text */}
          <p style={{
            color: '#ffffff',
            fontSize: 52,
            fontWeight: 700,
            lineHeight: 1.25,
            margin: 0,
            textShadow: '0 2px 20px rgba(0,0,0,0.8)',
          }}>
            {fact.text}
          </p>
        </div>

        {/* Account name (bottom) */}
        {nome && (
          <div style={{
            position: 'absolute',
            bottom: 50,
            left: 60,
            right: 60,
            display: 'flex',
            alignItems: 'center',
            gap: 12,
          }}>
            {avatar && (
              <Img
                src={staticFile(avatar)}
                style={{ width: 36, height: 36, borderRadius: '50%', objectFit: 'cover' }}
              />
            )}
            <span style={{ color: 'rgba(255,255,255,0.7)', fontSize: 22, fontWeight: 500 }}>
              @{nome}
            </span>
          </div>
        )}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
