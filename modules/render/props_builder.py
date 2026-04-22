"""
render/props_builder.py — Monta o JSON de props para o Remotion e mede frames.
"""
import json
import logging
import subprocess
from pathlib import Path

from modules.models import GeneratedContent, PreparedAssets

logger = logging.getLogger(__name__)

PUBLIC_DIR = Path("video-renderer") / "public"


def build_props(assets: PreparedAssets, content: GeneratedContent, template: str) -> dict:
    base = {
        "hook": content.curiosity_text.title(),
        "comentario": content.comment_text,
        "nome": assets.account_name,
        "avatar": assets.avatar_path.name,
        "bgVideo": "bg_looped.mp4",
    }

    if template == "ComentarioVideo":
        base["video"] = assets.clip_path.name
        base["clipDurationFrames"] = get_frame_count(PUBLIC_DIR / assets.clip_path.name) - 1
        base["story"] = content.story_text
        base["highlights"] = content.highlights
        if assets.music_path:
            base["music"] = assets.music_path.name

    elif template == "ComentarioImagem":
        if not assets.image_path:
            raise ValueError("ComentarioImagem requer image_path nos assets.")
        base["imagem"] = assets.image_path.name
        base["story"] = content.story_text
        base["highlights"] = content.highlights
        if assets.music_path:
            base["music"] = assets.music_path.name

    return base


def get_frame_count(video_path: Path) -> int:
    """Retorna o número exato de frames do arquivo via ffprobe (-count_packets)."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-select_streams", "v:0",
        "-count_packets",
        "-show_entries", "stream=nb_read_packets",
        str(video_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe falhou em {video_path}")

    data = json.loads(result.stdout)
    streams = data.get("streams", [])
    if not streams or not streams[0].get("nb_read_packets"):
        raise RuntimeError(f"Não foi possível obter frame count de {video_path}")

    return int(streams[0]["nb_read_packets"])


def get_duration(video_path: Path) -> float:
    """
    Duração real do clipe contando packets. Subtrai 2 frames para evitar
    off-by-one quando o Remotion faz seek no último frame.
    """
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-select_streams", "v:0",
        "-count_packets",
        "-show_entries", "stream=nb_read_packets,r_frame_rate,duration",
        str(video_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        logger.warning("[Props] ffprobe falhou, usando duração padrão de 30s")
        return 30.0

    data = json.loads(result.stdout)
    streams = data.get("streams", [])
    if not streams:
        return 30.0

    stream = streams[0]
    nb_packets = stream.get("nb_read_packets")
    r_frame_rate = stream.get("r_frame_rate", "30/1")

    if nb_packets:
        try:
            num, den = map(int, r_frame_rate.split("/"))
            fps = num / den if den else 30.0
            duration = max(0.1, int(nb_packets) / fps - (2 / fps))
            logger.info(f"[Props] Duração real: {int(nb_packets)} frames / {fps:.2f}fps = {duration:.2f}s")
            return duration
        except (ValueError, ZeroDivisionError):
            pass

    duration = float(stream.get("duration", 30.0))
    logger.info(f"[Props] Duração via metadata: {duration:.2f}s")
    return duration