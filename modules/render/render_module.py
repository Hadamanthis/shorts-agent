"""
render/render_module.py — Renderiza o short delegando ao Remotion CLI.

Responsabilidades:
  - Copiar os arquivos de mídia necessários para video-renderer/public/
  - Montar o JSON de props que o Remotion vai consumir
  - Descobrir a duração real do clipe (via ffprobe)
  - Chamar `npx remotion render` com os parâmetros certos
  - Devolver um RenderedShort com o caminho do mp4 gerado

Templates disponíveis (definidos em video-renderer/src/Root.tsx):
  - ComentarioVideo  → hook + vídeo + comentário
  - ComentarioImagem → hook + imagem + comentário
"""
import json
import logging
import platform
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from modules.models import GeneratedContent, PipelineContext, PreparedAssets, RenderedShort

logger = logging.getLogger(__name__)

REMOTION_DIR = Path("video-renderer")
PUBLIC_DIR = REMOTION_DIR / "public"

# No Windows, npx é um script .cmd — subprocess precisa do nome completo
NPX = "npx.cmd" if platform.system() == "Windows" else "npx"


class RenderModule:

    def run(
        self,
        ctx: PipelineContext,
        assets: PreparedAssets,
        content: GeneratedContent,
        template: str = "ComentarioVideo",
    ) -> RenderedShort:
        output_dir = Path("output") / "shorts"
        output_dir.mkdir(parents=True, exist_ok=True)
        PUBLIC_DIR.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"short_{ctx.profile_name}_{timestamp}.mp4"

        # 1. Duração: para vídeo usa ffprobe no clip; para imagem usa config
        fps = ctx.config["layout"].get("fps", 30)
        if template == "ComentarioVideo":
            duration_seconds = self._get_duration(assets.clip_path)
        else:
            duration_seconds = float(ctx.config["image_ingestion"].get("short_duration", 15))
        duration_frames = int(duration_seconds * fps)

        # 2. Prepara public/ com bg_looped.mp4 na duração certa e FPS correto
        self._sync_public(assets, template, duration_seconds, fps)

        logger.info(f"[Render] Template: {template}")
        logger.info(f"[Render] Duração: {duration_seconds:.1f}s → {duration_frames} frames @ {fps}fps")

        # 3. Props para o Remotion (só nomes de arquivo — public/ já está sincronizado)
        props = self._build_props(assets, content, template, fps)
        logger.info(f"[Render] Props: {json.dumps(props, ensure_ascii=False)}")

        # 4. Chama o Remotion CLI
        self._run_remotion(
            template=template,
            props=props,
            output_path=output_path,
            duration_frames=duration_frames,
            fps=fps,
        )

        logger.info(f"[Render] Short gerado: {output_path}")
        return RenderedShort(
            video_path=output_path,
            width=ctx.config["layout"]["width"],
            height=ctx.config["layout"]["height"],
            duration_seconds=duration_seconds,
        )

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _sync_public(self, assets: PreparedAssets, template: str, duration_seconds: float, fps: int) -> None:
        """
        Prepara video-renderer/public/ com todos os assets que o Remotion precisa.

        bg_looped.mp4 — gerado via FFmpeg com loop exato da duração do clip.
          O OffthreadVideo do Remotion não suporta loop nativo, então entregamos
          um arquivo já com a duração certa, sem precisar de <Loop> no TSX.

        avatar — copiado uma vez (identidade fixa do canal).
        clip/imagem — sempre sobrescreve (muda a cada vídeo).
        """
        # bg_looped.mp4 — sempre regera para bater com a duração atual do clip
        bg_src = assets.background_video_path
        bg_looped = PUBLIC_DIR / "bg_looped.mp4"
        logger.info(f"[Render] Gerando bg_looped.mp4 com {duration_seconds:.1f}s via FFmpeg...")
        ffmpeg_loop_cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1",
            "-i", str(bg_src.resolve()),
            "-t", str(duration_seconds),
            "-r", str(fps),              # força FPS igual ao da composição Remotion
            "-c:v", "libx264",
            "-an",
            "-preset", "fast",
            str(bg_looped),
        ]
        result = subprocess.run(ffmpeg_loop_cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg falhou ao gerar bg_looped.mp4:\n{result.stderr}")

        # avatar — só copia se não existir ainda
        avatar_src = assets.avatar_path
        avatar_dst = PUBLIC_DIR / avatar_src.name
        if not avatar_dst.exists():
            logger.info(f"[Render] Copiando avatar para public/: {avatar_src.name}")
            shutil.copy2(avatar_src, avatar_dst)

        # clip / imagem — sempre copia (muda a cada vídeo)
        if template == "ComentarioVideo":
            clip_dst = PUBLIC_DIR / assets.clip_path.name
            logger.info(f"[Render] Copiando clip para public/: {assets.clip_path.name}")
            shutil.copy2(assets.clip_path, clip_dst)

        elif template == "ComentarioImagem":
            if assets.image_path and assets.image_path.exists():
                img_dst = PUBLIC_DIR / assets.image_path.name
                shutil.copy2(assets.image_path, img_dst)
                logger.info(f"[Render] Copiando imagem para public/: {assets.image_path.name}")
            else:
                raise FileNotFoundError(
                    "ComentarioImagem requer image_path nos assets, mas não foi encontrado."
                )

    def _build_props(
        self,
        assets: PreparedAssets,
        content: GeneratedContent,
        template: str,
        fps: int,
    ) -> dict:
        base = {
            "hook": content.curiosity_text,
            "comentario": content.comment_text,
            "nome": assets.account_name,
            "avatar": assets.avatar_path.name,
            "bgVideo": "bg_looped.mp4",   # gerado pelo Python com duração exata
        }

        if template == "ComentarioVideo":
            base["video"] = assets.clip_path.name
        elif template == "ComentarioImagem":
            if not assets.image_path:
                raise ValueError("ComentarioImagem requer image_path nos assets.")
            base["imagem"] = assets.image_path.name

        return base

    def _get_duration(self, video_path: Path) -> float:
        """Usa ffprobe para obter a duração real do clipe em segundos."""
        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            str(video_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            logger.warning("[Render] ffprobe falhou, usando duração padrão de 30s")
            return 30.0

        data = json.loads(result.stdout)
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video":
                return float(stream.get("duration", 30.0))

        return 30.0

    def _run_remotion(
        self,
        template: str,
        props: dict,
        output_path: Path,
        duration_frames: int,
        fps: int,
    ) -> None:
        if not REMOTION_DIR.exists():
            raise FileNotFoundError(
                f"Projeto Remotion não encontrado em: {REMOTION_DIR.resolve()}\n"
                f"Certifique-se que a pasta video-renderer/ existe e rodou 'npm install'."
            )

        props_json = json.dumps(props, ensure_ascii=False)

        cmd = [
            NPX, "remotion", "render",
            "src/index.ts",
            template,
            str(output_path.resolve()),
            "--props", props_json,
            "--duration", str(duration_frames),
            "--fps", str(fps),
        ]

        logger.info(f"[Render] Executando Remotion render para '{template}'...")
        result = subprocess.run(
            cmd,
            cwd=str(REMOTION_DIR.resolve()),
            capture_output=False,
            timeout=600,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"Remotion render falhou com código {result.returncode}."
            )