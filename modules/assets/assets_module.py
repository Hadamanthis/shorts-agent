"""
assets/assets_module.py — Prepara e valida todos os assets antes do render.

Funciona para os dois pipelines:
  - Vídeo (ComentarioVideo): clip_path preenchido, image_path=None
  - Imagem (ComentarioImagem): image_path preenchido, clip_path é um dummy vazio

Futuramente: remoção de marca d'água seria feita aqui no clip.
"""
import logging
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw

from modules.models import ImageSource, PipelineContext, PreparedAssets, VideoSource

logger = logging.getLogger(__name__)

# Duração padrão usada quando o pipeline é de imagem (sem clip de vídeo real)
IMAGE_PIPELINE_DURATION = 15  # segundos


class AssetsModule:

    def run_video(self, ctx: PipelineContext, source: VideoSource) -> PreparedAssets:
        """Pipeline de vídeo: valida clip, bg e avatar."""
        profile = ctx.config["profiles"][ctx.profile_name]
        return self._build(
            ctx=ctx,
            clip_path=source.clip_path,
            image_path=None,
            bg_path=Path(profile["background_video"]),
            avatar_path=Path(profile["avatar_path"]),
            account_name=profile["account_name"],
        )

    def run_image(self, ctx: PipelineContext, source: ImageSource) -> PreparedAssets:
        """Pipeline de imagem: sem clip, usa a imagem baixada."""
        profile = ctx.config["profiles"][ctx.profile_name]

        # Cria um clip vazio (arquivo de texto) só para que PreparedAssets
        # tenha um clip_path válido — o render de imagem não o usa.
        dummy_clip = Path("output") / "images" / "_dummy_clip.txt"
        dummy_clip.parent.mkdir(parents=True, exist_ok=True)
        dummy_clip.touch()

        return self._build(
            ctx=ctx,
            clip_path=None,
            image_path=source.image_path,
            bg_path=Path(profile["background_video"]),
            avatar_path=Path(profile["avatar_path"]),
            account_name=profile["account_name"],
            music_path=Path(profile.get("music_path", "")) or None
        )

    # ── Internos ─────────────────────────────────────────────────────────────

    def _build(
        self,
        ctx: PipelineContext,
        clip_path: Path,
        image_path: Optional[Path],
        bg_path: Path,
        avatar_path: Path,
        account_name: str,
        music_path: Optional[Path] = None,    # ← novo parâmetro
    ) -> PreparedAssets:
        self._validate_background(bg_path)
        avatar_path = self._ensure_avatar(avatar_path)

        if ctx.config["pipeline"].get("watermark_removal", False):
            logger.info("[Assets] Remoção de marca d'água: não implementado ainda.")

        if clip_path:
            logger.info(f"[Assets] Clip:   {clip_path}")
        if image_path:
            logger.info(f"[Assets] Imagem: {image_path}")

        logger.info(f"[Assets] Fundo:  {bg_path}")
        logger.info(f"[Assets] Avatar: {avatar_path}")
        if music_path:
            logger.info(f"[Assets] Música: {music_path}")

        return PreparedAssets(
            clip_path=clip_path,
            image_path=Path(image_path) if image_path else None,
            background_video_path=bg_path,
            avatar_path=avatar_path,
            account_name=account_name,
            music_path=music_path,
        )

    def _validate_background(self, path: Path) -> None:
        if not path.exists():
            raise FileNotFoundError(
                f"Vídeo de fundo não encontrado: {path}\n"
                f"Coloque seu vídeo de fundo em: {path}"
            )

    def _ensure_avatar(self, path: Path) -> Path:
        if path.exists():
            return path
        logger.warning(f"[Assets] Avatar não encontrado em {path}. Gerando placeholder.")
        path.parent.mkdir(parents=True, exist_ok=True)
        size = 128
        img = Image.new("RGBA", (size, size), (80, 80, 200, 255))
        draw = ImageDraw.Draw(img)
        draw.ellipse([0, 0, size, size], fill=(80, 80, 200, 255))
        img.save(path)
        return path