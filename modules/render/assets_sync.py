"""
render/assets_sync.py — Sincroniza assets para video-renderer/public/.

Responsabilidades:
  - Re-encodar o background com keyframes densos (uma vez por perfil)
  - Copiar avatar, música, clip e imagem para public/
"""
import logging
import shutil
import subprocess
from pathlib import Path

from modules.models import PreparedAssets

logger = logging.getLogger(__name__)

PUBLIC_DIR = Path("video-renderer") / "public"


def sync_public(assets: PreparedAssets, template: str, fps: int) -> None:
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)

    _sync_background(assets.background_video_path, fps)
    _sync_avatar(assets.avatar_path)
    _sync_music(assets.music_path)

    if template == "ComentarioVideo":
        _sync_clip(assets.clip_path)
    elif template == "ComentarioImagem":
        _sync_image(assets.image_path)


# ── Internos ──────────────────────────────────────────────────────────────────

def _sync_background(bg_src: Path, fps: int) -> None:
    bg_dst = PUBLIC_DIR / "bg_looped.mp4"
    sentinel = PUBLIC_DIR / ".bg_encoded"
    sentinel_src = sentinel.read_text().strip() if sentinel.exists() else ""
    bg_src_str = str(bg_src.resolve())

    if bg_dst.exists() and sentinel_src == bg_src_str:
        logger.info("[Assets Sync] Fundo já re-encodado e compatível, pulando.")
        return

    logger.info(f"[Assets Sync] Re-encodando fundo: {bg_src.name}")
    cmd = [
        "ffmpeg", "-y",
        "-i", str(bg_src),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-g", str(fps),
        "-keyint_min", str(fps),
        "-sc_threshold", "0",
        "-an",
        str(bg_dst),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg falhou ao re-encodar bg:\n{result.stderr[-500:]}")
    sentinel.write_text(bg_src_str)
    logger.info(f"[Assets Sync] Fundo re-encodado: {bg_dst}")


def _sync_avatar(avatar_path: Path) -> None:
    dst = PUBLIC_DIR / avatar_path.name
    if not dst.exists():
        logger.info(f"[Assets Sync] Copiando avatar: {avatar_path.name}")
        shutil.copy2(avatar_path, dst)


def _sync_music(music_path: Path | None) -> None:
    if not music_path or not music_path.exists():
        return
    dst = PUBLIC_DIR / music_path.name
    if not dst.exists():
        logger.info(f"[Assets Sync] Copiando música: {music_path.name}")
        shutil.copy2(music_path, dst)


def _sync_clip(clip_path: Path) -> None:
    dst = PUBLIC_DIR / clip_path.name
    logger.info(f"[Assets Sync] Copiando clip: {clip_path.name}")
    shutil.copy2(clip_path, dst)


def _sync_image(image_path: Path | None) -> None:
    if not image_path or not image_path.exists():
        raise FileNotFoundError("ComentarioImagem requer image_path nos assets.")
    dst = PUBLIC_DIR / image_path.name
    logger.info(f"[Assets Sync] Copiando imagem: {image_path.name}")
    shutil.copy2(image_path, dst)