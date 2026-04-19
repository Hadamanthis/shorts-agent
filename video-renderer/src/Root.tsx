import { Composition } from 'remotion';
import { ComentarioVideo, ComentarioVideoProps } from './templates/ComentarioVideo';
import { ComentarioImagem, ComentarioImagemProps } from './templates/ComentarioImagem';

// Valores usados APENAS no Remotion Studio (preview).
// Em produção, --duration e --fps passados pelo Python sobrescrevem tudo isso.
const PREVIEW_DURATION_SEC = 30;
const FPS = 30;
const PREVIEW_FRAMES = PREVIEW_DURATION_SEC * FPS;

export const RemotionRoot = () => {
  return (
    <>
      <Composition<ComentarioVideoProps>
        id="ComentarioVideo"
        component={ComentarioVideo}
        durationInFrames={PREVIEW_FRAMES}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={{
          hook: 'Você não vai acreditar no que aconteceu aqui...',
          story: 'Contexto da imagem aparece aqui. Três a cinco frases contando o que aconteceu e por que viralizou.',
          comentario: 'Isso me surpreendeu demais quando vi pela primeira vez!',
          nome: 'carlos.silva',
          video: 'video.mp4',
          avatar: 'avatar.png',
          bgVideo: 'bg_looped.mp4',
        }}
      />

      <Composition<ComentarioImagemProps>
        id="ComentarioImagem"
        component={ComentarioImagem}
        durationInFrames={PREVIEW_FRAMES}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={{
          hook: 'Você não vai acreditar no que aconteceu aqui...',
          story: 'Contexto da imagem aparece aqui. Três a cinco frases contando o que aconteceu e por que viralizou.',
          comentario: 'Isso me surpreendeu demais quando vi pela primeira vez!',
          nome: 'carlos.silva',
          imagem: 'thumbnail.jpg',
          avatar: 'avatar.png',
          bgVideo: 'bg_looped.mp4',
        }}
      />
    </>
  );
};