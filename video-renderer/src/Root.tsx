import { Composition } from 'remotion';
import { ComentarioVideo } from './templates/ComentarioVideo';
import type { ComentarioVideoProps } from './templates/ComentarioVideo';
import { ComentarioImagem } from './templates/ComentarioImagem';
import type { ComentarioImagemProps } from './templates/ComentarioImagem';
import { DidYouKnow } from './templates/DidYouKnow';
import type { DidYouKnowProps } from './templates/DidYouKnow';
import AppRouter from './ui/AppRouter';

const FPS = 30;
const PREVIEW_FRAMES = 30 * FPS; // 30s — só para o Studio

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="ComentarioVideo"
        component={ComentarioVideo as React.FC<ComentarioVideoProps>}
        durationInFrames={PREVIEW_FRAMES}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={{
          hook: 'No Japão, bêbados dormem na rua sem ser perturbados',
          story: 'O story gerado pelo LLM aparece aqui. Denso, informativo, sem perguntas no final.',
          comentario: 'Isso muda tudo que eu aprendi sobre segurança pública.',
          nome: 'carlos.silva',
          video: 'video.mp4',
          avatar: 'avatar.png',
          bgVideo: 'bg_looped.mp4',
        } satisfies ComentarioVideoProps}
      />

      <Composition
        id="ComentarioImagem"
        component={ComentarioImagem as React.FC<ComentarioImagemProps>}
        durationInFrames={PREVIEW_FRAMES}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={{
          hook: 'Em 1888, abolir escravidão era destruir a economia',
          story: 'O story gerado pelo LLM aparece aqui. Denso, informativo, sem perguntas no final.',
          comentario: 'A história que não te contaram na escola.',
          nome: 'carlos.silva',
          imagem: 'thumbnail.jpg',
          avatar: 'avatar.png',
          bgVideo: 'bg_looped.mp4',
        } satisfies ComentarioImagemProps}
      />

      <Composition
        id="DidYouKnow"
        component={DidYouKnow as React.FC<DidYouKnowProps>}
        durationInFrames={5 * 270}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={{
          facts: [
            { text: 'O mel nunca estraga — arqueólogos encontraram mel de 3.000 anos comestível no Egito.', image: 'dyk_img_00.jpg' },
            { text: 'Uma colher de sopa de solo saudável contém mais micro-organismos do que pessoas na Terra.', image: 'dyk_img_01.jpg' },
            { text: 'O coração de um camarão fica na sua cabeça.', image: 'dyk_img_02.jpg' },
            { text: 'A Groenlândia é tecnicamente a maior ilha do mundo — mas 80% dela é coberta de gelo.', image: 'dyk_img_03.jpg' },
            { text: 'Polvos têm três corações e sangue azul.', image: 'dyk_img_04.jpg' },
          ],
          cardFrames: 9 * FPS,
        } satisfies DidYouKnowProps}
      />

      {/*
        Interface de gestão — não gera vídeo, só UI de controle.
        Acesse em: http://localhost:3000 → clique em "UI" no painel esquerdo.
      */}
      <Composition
        id="UI"
        component={AppRouter}
        durationInFrames={1}
        fps={30}
        width={1280}
        height={800}
      />
    </>
  );
};