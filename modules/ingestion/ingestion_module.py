"""
ingestion/ingestion_module.py — Baixa o vídeo e coleta comentários.

Responsabilidades:
  - Extrair metadados do vídeo (título, descrição, canal)
  - Baixar o trecho de vídeo conforme config (max_clip_duration, clip_start_offset)
  - Coletar os top comentários do YouTube
  - Persistir o VideoSource em disco (source_<video_id>.json) para que
    etapas subsequentes possam ser executadas em sessões separadas
  - Devolver um VideoSource preenchido

Não sabe nada sobre LLM, layout ou render.
"""
import json
import logging
import subprocess
from pathlib import Path

from modules.models import PipelineContext, VideoSource

logger = logging.getLogger(__name__)

SOURCE_CACHE_DIR = Path("output") / "cache"


def save_source(source: VideoSource) -> Path:
    """Serializa o VideoSource para JSON em disco."""
    SOURCE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = SOURCE_CACHE_DIR / f"source_{source.video_id}.json"
    data = {
        "url": source.url,
        "video_id": source.video_id,
        "title": source.title,
        "description": source.description,
        "channel_name": source.channel_name,
        "duration_seconds": source.duration_seconds,
        "clip_path": str(source.clip_path),
        "comments": source.comments,
        "thumbnail_url": source.thumbnail_url,
    }
    cache_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"[Ingestion] VideoSource salvo em: {cache_path}")
    return cache_path


def load_source(url: str) -> VideoSource | None:
    """
    Tenta carregar um VideoSource já salvo a partir da URL.
    Extrai o video_id da URL para encontrar o arquivo de cache.
    Retorna None se não existir.
    """
    # Extrai video_id de URLs do tipo ?v=XXXX ou /shorts/XXXX
    video_id = None
    if "v=" in url:
        video_id = url.split("v=")[-1].split("&")[0]
    elif "/shorts/" in url:
        video_id = url.split("/shorts/")[-1].split("?")[0]

    if not video_id:
        return None

    cache_path = SOURCE_CACHE_DIR / f"source_{video_id}.json"
    if not cache_path.exists():
        return None

    data = json.loads(cache_path.read_text(encoding="utf-8"))

    source = VideoSource(
        url=data["url"],
        video_id=data["video_id"],
        title=data["title"],
        description=data["description"],
        channel_name=data["channel_name"],
        duration_seconds=data["duration_seconds"],
        clip_path=Path(data["clip_path"]),
        comments=data["comments"],
        thumbnail_url=data["thumbnail_url"],
    )
    logger.info(f"[Ingestion] VideoSource carregado do cache: {cache_path}")
    return source


class IngestionModule:

    def run(self, ctx: PipelineContext, url: str) -> VideoSource:
        logger.info(f"[Ingestion] Iniciando para URL: {url}")

        video_cfg = ctx.config["video"]
        output_dir = Path("output") / "clips"
        output_dir.mkdir(parents=True, exist_ok=True)

        # 1. Metadados
        meta = self._fetch_metadata(url)
        video_id = meta["id"]
        logger.info(f"[Ingestion] Vídeo: {meta['title']} ({video_id})")

        # 2. Download do trecho
        clip_path = self._download_clip(
            url=url,
            video_id=video_id,
            output_dir=output_dir,
            start=video_cfg["clip_start_offset"],
            duration=video_cfg["max_clip_duration"],
        )

        # 3. Comentários
        comments = self._fetch_comments(
            url=url,
            limit=video_cfg["max_comments_to_fetch"],
            top_n=video_cfg["top_comments_for_context"],
        )

        source = VideoSource(
            url=url,
            video_id=video_id,
            title=meta.get("title", ""),
            description=meta.get("description", "")[:1000],  # limita tamanho
            channel_name=meta.get("channel", ""),
            duration_seconds=int(meta.get("duration", 0)),
            clip_path=clip_path,
            comments=comments,
            thumbnail_url=meta.get("thumbnail", ""),
        )

        save_source(source)
        logger.info(f"[Ingestion] Clip salvo em: {clip_path}")
        logger.info(f"[Ingestion] Comentários coletados: {len(comments)}")
        return source

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _fetch_metadata(self, url: str) -> dict:
        """Extrai metadados via yt-dlp sem baixar o vídeo."""
        cmd = [
            "yt-dlp",
            "--dump-json",
            "--no-playlist",
            "--quiet",
            url,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            raise RuntimeError(
                f"yt-dlp falhou ao buscar metadados:\n{result.stderr}"
            )
        return json.loads(result.stdout)

    def _download_clip(
        self,
        url: str,
        video_id: str,
        output_dir: Path,
        start: int,
        duration: int,
    ) -> Path:
        """
        Baixa apenas o trecho definido por start + duration usando yt-dlp + FFmpeg.
        Formato: mp4 com codec compatível para composição posterior.
        """
        clip_path = output_dir / f"{video_id}_clip.mp4"

        if clip_path.exists():
            logger.info(f"[Ingestion] Clip já existe, pulando download: {clip_path}")
            return clip_path

        # Baixa o vídeo completo em qualidade reduzida para agilizar
        raw_path = output_dir / f"{video_id}_raw.mp4"

        dl_cmd = [
            "yt-dlp",
            "--format", "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best",
            "--merge-output-format", "mp4",
            "--output", str(raw_path),
            "--no-playlist",
            "--quiet",
            url,
        ]
        logger.info("[Ingestion] Baixando vídeo...")
        result = subprocess.run(dl_cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise RuntimeError(f"yt-dlp download falhou:\n{result.stderr}")

        # Recorta com FFmpeg
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-ss", str(start),
            "-i", str(raw_path),
            "-t", str(duration),
            "-c:v", "libx264",
            "-c:a", "aac",
            "-movflags", "+faststart",
            str(clip_path),
        ]
        logger.info(f"[Ingestion] Recortando trecho: {start}s → {start + duration}s")
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg falhou ao recortar:\n{result.stderr}")

        # Remove o raw para economizar espaço
        raw_path.unlink(missing_ok=True)

        return clip_path

    def _fetch_comments(self, url: str, limit: int, top_n: int) -> list[str]:
        """
        Coleta comentários via yt-dlp --write-comments.
        Retorna os top_n mais curtidos como lista de strings.
        """
        cmd = [
            "yt-dlp",
            "--write-comments",
            "--skip-download",
            "--extractor-args", f"youtube:max_comments={limit}",
            "--dump-json",
            "--quiet",
            url,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            logger.warning(f"[Ingestion] Falha ao coletar comentários: {result.stderr}")
            return []

        try:
            data = json.loads(result.stdout)
            raw_comments = data.get("comments", [])
        except (json.JSONDecodeError, KeyError):
            return []

        # Ordena por likes e pega os top_n
        sorted_comments = sorted(
            raw_comments,
            key=lambda c: c.get("like_count", 0),
            reverse=True,
        )
        return [c.get("text", "") for c in sorted_comments[:top_n] if c.get("text")]