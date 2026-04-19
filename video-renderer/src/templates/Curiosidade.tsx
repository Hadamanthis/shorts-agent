import {
  AbsoluteFill,
  OffthreadVideo,
  staticFile,
  useCurrentFrame,
  interpolate
} from 'remotion';

type Props = {
  hook: string;
  comentario: string;
  video: string;
  avatar?: string;
  nome?: string;
};

export const Comentario: React.FC<Props> = ({
  hook,
  comentario,
  video,
  avatar = 'avatar.png',
  nome = 'Usuário'
}) => {

  const frame = useCurrentFrame();

  // animação do card
  const opacity = interpolate(frame, [0, 20], [0, 1]);
  const scale = interpolate(frame, [0, 20], [0.9, 1]);

  return (
    <AbsoluteFill style={{ backgroundColor: 'black' }}>

      {/* 🎥 FUNDO */}
      {video && (
        <OffthreadVideo
          src={staticFile(video)}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover'
          }}
        />
      )}

      {/* 🌑 overlay */}
      <AbsoluteFill style={{ backgroundColor: 'rgba(0,0,0,0.5)' }} />

      {/* 🧩 CARD CENTRAL */}
      <div
        style={{
          position: 'absolute',
          top: '10%',
          left: '5%',
          right: '5%',
          bottom: '10%',
          backgroundColor: '#111',
          borderRadius: 30,
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          opacity,
          transform: `scale(${scale})`
        }}
      >

        {/* 🔥 HOOK */}
        <div
          style={{
            padding: 20,
            backgroundColor: '#000',
            color: '#fff',
            fontSize: 42,
            fontWeight: 'bold',
            textAlign: 'center'
          }}
        >
          {hook}
        </div>

        {/* 🎥 VÍDEO DENTRO DO CARD */}
        <div style={{ flex: 1 }}>
          {video && (
            <OffthreadVideo
              src={staticFile(video)}
              style={{
                width: '100%',
                height: '100%',
                objectFit: 'cover'
              }}
            />
          )}
        </div>

        {/* 💬 BLOCO DE COMENTÁRIO */}
        <div
          style={{
            padding: 20,
            backgroundColor: '#1a1a1a'
          }}
        >

          {/* 👤 PERFIL */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              marginBottom: 10
            }}
          >
            <img
              src={staticFile(avatar)}
              style={{
                width: 45,
                height: 45,
                borderRadius: '50%',
                marginRight: 10
              }}
            />

            <span
              style={{
                color: '#fff',
                fontSize: 22,
                fontWeight: 'bold'
              }}
            >
              {nome}
            </span>
          </div>

          {/* 📝 TEXTO */}
          <div
            style={{
              color: '#ddd',
              fontSize: 26,
              lineHeight: 1.4
            }}
          >
            {comentario}
          </div>

        </div>

      </div>

    </AbsoluteFill>
  );
};