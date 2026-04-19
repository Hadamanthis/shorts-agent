import {
  AbsoluteFill,
  OffthreadVideo,
  staticFile,
  Img,
} from 'remotion';

export type ComentarioImagemProps = {
  hook: string;
  comentario: string;
  nome: string;
  imagem: string;
  avatar?: string;
  bgVideo?: string;
};

const AutoText = ({
  text,
  maxSize,
  style = {},
}: {
  text: string;
  maxSize: number;
  style?: React.CSSProperties;
}) => (
  <div
    style={{
      fontSize: maxSize,
      color: 'white',
      textAlign: 'center',
      width: '100%',
      height: '100%',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '0 20px',
      lineHeight: 1.25,
      fontFamily: 'sans-serif',
      ...style,
    }}
  >
    <span>{text}</span>
  </div>
);

export const ComentarioImagem: React.FC<ComentarioImagemProps> = ({
  hook,
  comentario,
  nome,
  imagem,
  avatar = 'avatar.png',
  bgVideo = 'bg_looped.mp4',
}) => {
  return (
    <AbsoluteFill style={{ backgroundColor: '#000' }}>

      {/* FUNDO — bg_looped.mp4 já tem a duração exata do short */}
      <OffthreadVideo
        src={staticFile(bgVideo)}
        style={{ width: '100%', height: '100%', objectFit: 'cover' }}
      />

      {/* CARD CENTRAL */}
      <div
        style={{
          position: 'absolute',
          top: '5%',
          left: '5%',
          right: '5%',
          height: '70%',
          backgroundColor: 'rgba(0,0,0,0.88)',
          borderRadius: 24,
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* ZONA 1 — Hook */}
        <div style={{ flex: '0 0 20%', borderBottom: '1px solid #333' }}>
          <AutoText text={hook} maxSize={52} />
        </div>

        {/* ZONA 2 — Imagem estática */}
        <div style={{ flex: '0 0 45%', backgroundColor: '#111', overflow: 'hidden' }}>
          <Img
            src={staticFile(imagem)}
            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
          />
        </div>

        {/* ZONA 3 — Comentário */}
        <div
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            padding: '16px 20px 20px',
            gap: 8,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <Img
              src={staticFile(avatar)}
              style={{
                width: 64,
                height: 64,
                borderRadius: '50%',
                objectFit: 'cover',
                flexShrink: 0,
              }}
            />
            <span style={{ color: '#fff', fontSize: 36, fontFamily: 'sans-serif', fontWeight: 700 }}>
              {nome}
            </span>
          </div>
          <div style={{ flex: 1 }}>
            <AutoText
              text={comentario}
              maxSize={44}
              style={{ textAlign: 'left', justifyContent: 'flex-start', padding: 0 }}
            />
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};