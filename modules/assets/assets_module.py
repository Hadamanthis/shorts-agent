"""
assets/assets_module.py — Prepara e valida todos os assets antes do render.
"""
import logging
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw

from modules.models import ImageSource, PipelineContext, PreparedAssets, VideoSource

logger = logging.getLogger(__name__)


class AssetsModule:

    def run_video(self, ctx: PipelineContext, source: VideoSource) -> PreparedAssets:
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
        profile = ctx.config["profiles"][ctx.profile_name]
        dummy_clip = Path("output") / "images" / "_dummy_clip.txt"
        dummy_clip.parent.mkdir(parents=True, exist_ok=True)
        dummy_clip.touch()
        return self._build(
            ctx=ctx,
            clip_path=dummy_clip,
            image_path=source.image_path,
            bg_path=Path(profile["background_video"]),
            avatar_path=Path(profile["avatar_path"]),
            account_name=profile["account_name"],
        )

    def _build(
        self,
        ctx: PipelineContext,
        clip_path: Path,
        image_path: Optional[Path],
        bg_path: Path,
        avatar_path: Path,
        account_name: str,
    ) -> PreparedAssets:
        self._validate_background(bg_path)
        avatar_path = self._ensure_avatar(avatar_path)

        # Música de fundo — opcional, configurada no perfil
        profile = ctx.config["profiles"][ctx.profile_name]
        music_path: Optional[Path] = None
        music_cfg = profile.get("music_path")
        if music_cfg:
            p = Path(music_cfg)
            if p.exists():
                music_path = p
            else:
                logger.warning(f"[Assets] Música configurada não encontrada: {p}")

        if ctx.config["pipeline"].get("watermark_removal", False):
            logger.info("[Assets] Remoção de marca d'água: não implementado ainda.")

        logger.info(f"[Assets] Clip:   {clip_path}")
        logger.info(f"[Assets] Imagem: {image_path}")
        logger.info(f"[Assets] Fundo:  {bg_path}")
        logger.info(f"[Assets] Avatar: {avatar_path}")
        logger.info(f"[Assets] Música: {music_path}")

        return PreparedAssets(
            clip_path=clip_path,
            image_path=image_path,
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
        ImageDraw.Draw(img).ellipse([0, 0, size, size], fill=(80, 80, 200, 255))
        img.save(path)
        return path