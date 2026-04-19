import { AbsoluteFill, OffthreadVideo, staticFile, Img } from 'remotion';

export type ComentarioImagemProps = {
  hook: string;
  story: string;        // ← PROP NOVA
  comentario: string;
  nome: string;
  imagem: string;
  avatar?: string;
  bgVideo?: string;
};

const AutoText = ({
  text, maxSize, style = {},
}: {
  text: string; maxSize: number; style?: React.CSSProperties;
}) => (
  <div style={{
    fontSize: maxSize, color: 'white', textAlign: 'center',
    width: '100%', height: '100%', display: 'flex',
    alignItems: 'center', justifyContent: 'center',
    padding: '0 20px', lineHeight: 1.3,
    fontFamily: 'sans-serif', ...style,
  }}>
    <span>{text}</span>
  </div>
);

export const ComentarioImagem: React.FC<ComentarioImagemProps> = ({
  hook, story, comentario, nome,
  imagem, avatar = 'avatar.png', bgVideo = 'bg_looped.mp4',
}) => {
  return (
    <AbsoluteFill style={{ backgroundColor: '#000' }}>

      {/* FUNDO */}
      <OffthreadVideo
        src={staticFile(bgVideo)}
        style={{ width: '100%', height: '100%', objectFit: 'cover' }}
      />

      {/* CARD CENTRAL — altura maior para acomodar o story */}
      <div style={{
        position: 'absolute',
        top: '3%', left: '4%', right: '4%',
        height: '88%',                         // ← era 70%, cresceu
        backgroundColor: 'rgba(0,0,0,0.90)',
        borderRadius: 24,
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
      }}>

        {/* ZONA 1 — Hook (15% do card) */}
        <div style={{ flex: '0 0 15%', borderBottom: '1px solid #333' }}>
          <AutoText text={hook} maxSize={46} />
        </div>

        {/* ZONA 2 — Imagem (30% do card, era 45%) */}
        <div style={{ flex: '0 0 30%', backgroundColor: '#111', overflow: 'hidden' }}>
          <Img
            src={staticFile(imagem)}
            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
          />
        </div>

        {/* ZONA 2.5 — Story: narrativa da imagem ← ZONA NOVA */}
        <div style={{
          flex: '0 0 22%',
          borderTop: '1px solid #222',
          borderBottom: '1px solid #333',
          padding: '10px 20px',
          display: 'flex',
          alignItems: 'center',
        }}>
          <p style={{
            color: '#d0d0d0',
            fontSize: 34,
            fontFamily: 'sans-serif',
            lineHeight: 1.35,
            margin: 0,
          }}>
            {story}
          </p>
        </div>

        {/* ZONA 3 — Comentário (flex: 1, ocupa o restante) */}
        <div style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          padding: '12px 20px 16px',
          gap: 8,
        }}>
          {/* Cabeçalho: avatar + nome */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <Img
              src={staticFile(avatar)}
              style={{ width: 56, height: 56, borderRadius: '50%',
                       objectFit: 'cover', flexShrink: 0 }}
            />
            <span style={{ color: '#fff', fontSize: 32,
                           fontFamily: 'sans-serif', fontWeight: 700 }}>
              {nome}
            </span>
          </div>
          {/* Texto do comentário */}
          <div style={{ flex: 1 }}>
            <AutoText
              text={comentario}
              maxSize={38}
              style={{ textAlign: 'left', justifyContent: 'flex-start', padding: 0 }}
            />
          </div>
        </div>

      </div>
    </AbsoluteFill>
  );
};