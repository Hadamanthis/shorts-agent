import { AbsoluteFill, OffthreadVideo, staticFile, Img } from 'remotion';
import { Html5Audio } from 'remotion';

export type ComentarioImagemProps = {
  hook: string;
  story: string;
  comentario: string;
  nome: string;
  imagem: string;
  avatar?: string;
  bgVideo?: string;
  music?: string;
};

export const ComentarioImagem: React.FC<ComentarioImagemProps> = ({
  hook, story, comentario, nome,
  imagem, avatar = 'avatar.png',
  bgVideo = 'bg_looped.mp4',
  music,
}) => {
  return (
    <AbsoluteFill style={{ backgroundColor: '#000' }}>

      {/* FUNDO com overlay escuro para dar profundidade */}
      <OffthreadVideo
        src={staticFile(bgVideo)}
        style={{ width: '100%', height: '100%', objectFit: 'cover', opacity: 0.70 }}
      />

      {/* Overlay gradiente — fundo mais escuro embaixo, mais leve em cima */}
      <div style={{
        position: 'absolute', inset: 0,
        background: 'linear-gradient(180deg, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0.80) 100%)',
      }} />

      {music && (
        <Html5Audio src={staticFile(music)} volume={0.18} loop={true} />
      )}

      {/* CARD — máx 92% da altura, fixado no topo */}
      <div style={{
        position: 'absolute',
        top: '4%',
        left: '4%',
        right: '4%',
        maxHeight: '92%',
        borderRadius: 24,
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
        // sombra de profundidade no card inteiro
        boxShadow: '0 8px 40px rgba(0,0,0,0.7)',
      }}>

        {/* ── ZONA 1: HOOK ─────────────────────────────────────────── */}
        {/* fundo levemente diferente do restante do card */}
        <div style={{
          backgroundColor: 'rgba(15,15,15,0.97)',
          padding: '22px 28px 20px',
          borderBottom: '1px solid rgba(255,255,255,0.08)',
        }}>
          <p style={{
            color: '#FFFFFF',
            fontFamily: 'sans-serif',
            fontWeight: 800,
            fontSize: 46,
            lineHeight: 1.2,
            textAlign: 'center',
            margin: 0,
            // máx 2 linhas — se o prompt for curto sempre cabe
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
            // leve sombra no texto para destacar do fundo
            textShadow: '0 2px 8px rgba(0,0,0,0.8)',
          }}>
            {hook}
          </p>
        </div>

        {/* ── ZONA 2: IMAGEM ───────────────────────────────────────── */}
        <div style={{
          backgroundColor: '#0d0d0d',
          borderBottom: '1px solid rgba(255,255,255,0.06)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: 340,    // mínimo — imagens pequenas não ficam minúsculas
          maxHeight: 560,    // máximo — imagens altas não dominam o card
          flexShrink: 0,
        }}>
          <Img
            src={staticFile(imagem)}
            style={{
              width: '100%',
              minHeight: 340,
              maxHeight: 560,
              objectFit: 'contain',
              display: 'block',
            }}
          />
        </div>

        {/* ── ZONA 2.5: STORY ──────────────────────────────────────── */}
        {/* fundo ligeiramente mais claro que o hook — cria separação visual */}
        <div style={{
          backgroundColor: 'rgba(22,22,22,0.98)',
          borderBottom: '1px solid rgba(255,255,255,0.08)',
          padding: '18px 28px',
          flexShrink: 0,
        }}>
          <p style={{
            color: 'rgba(255,255,255,0.88)',
            fontFamily: 'sans-serif',
            fontSize: 30,          // mínimo 30 — legível em celular
            lineHeight: 1.55,
            margin: 0,
            fontWeight: 400,
          }}>
            &nbsp;&nbsp;&nbsp;&nbsp;{story}
          </p>
        </div>

        {/* ── ZONA 3: COMENTÁRIO ───────────────────────────────────── */}
        {/* fundo mais escuro — contraste máximo, leitura fácil */}
        <div style={{
          backgroundColor: 'rgba(10,10,10,0.99)',
          padding: '14px 24px 20px',
          flexShrink: 0,
          display: 'flex',
          flexDirection: 'column',
          gap: 10,
        }}>
          {/* linha separadora com accent sutil */}
          <div style={{
            height: 2,
            width: 48,
            backgroundColor: 'rgba(255,255,255,0.15)',
            borderRadius: 2,
            marginBottom: 2,
          }} />

          {/* avatar + nome */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <Img
              src={staticFile(avatar)}
              style={{
                width: 48, height: 48,
                borderRadius: '50%',
                objectFit: 'cover',
                flexShrink: 0,
                // borda sutil no avatar
                outline: '2px solid rgba(255,255,255,0.15)',
                outlineOffset: 1,
              }}
            />
            <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <span style={{
                color: '#FFFFFF',
                fontSize: 26,
                fontFamily: 'sans-serif',
                fontWeight: 700,
                lineHeight: 1,
              }}>
                {nome}
              </span>
            </div>
          </div>

          {/* texto do comentário — mínimo 32px */}
          <p style={{
            color: 'rgba(255,255,255,0.92)',
            fontSize: 32,          // mínimo 32 — nunca menor
            fontFamily: 'sans-serif',
            lineHeight: 1.45,
            margin: 0,
            fontWeight: 400,
          }}>
            &nbsp;&nbsp;&nbsp;&nbsp;{comentario}
          </p>
        </div>

      </div>
    </AbsoluteFill>
  );
};