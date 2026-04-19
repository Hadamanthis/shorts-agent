import { Composition } from 'remotion';
import { ComentarioVideo, ComentarioVideoProps } from './templates/ComentarioVideo';
import { ComentarioImagem, ComentarioImagemProps } from './templates/ComentarioImagem';

// durationInFrames é sobrescrito pelo Python via --props no momento do render.
// Os valores aqui são apenas para o Remotion Studio (preview).
const DEFAULT_DURATION = 30 * 30; // 30 segundos a 30fps
const FPS = 30;

export const RemotionRoot = () => {
  return (
    <>
      {/* Template com vídeo no meio */}
      <Composition<ComentarioVideoProps>
        id="ComentarioVideo"
        component={ComentarioVideo}
        durationInFrames={DEFAULT_DURATION}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={{
          hook: 'Você não vai acreditar no que aconteceu aqui...',
          comentario: 'Isso me surpreendeu demais quando vi pela primeira vez!',
          nome: 'carlos.silva',
          video: 'video.mp4',
          avatar: 'avatar.png',
          bgVideo: 'bg.mp4',
        }}
      />

      {/* Template com imagem estática no meio */}
      <Composition<ComentarioImagemProps>
        id="ComentarioImagem"
        component={ComentarioImagem}
        durationInFrames={DEFAULT_DURATION}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={{
          hook: 'Você não vai acreditar no que aconteceu aqui...',
          comentario: 'Isso me surpreendeu demais quando vi pela primeira vez!',
          nome: 'carlos.silva',
          imagem: 'thumbnail.jpg',
          avatar: 'avatar.png',
          bgVideo: 'bg.mp4',
        }}
      />
    </>
  );
};