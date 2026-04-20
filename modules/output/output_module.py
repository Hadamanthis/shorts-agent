"""
output/output_module.py — Salva o resultado final e metadados.

Gera três arquivos ao lado do .mp4:
  - metadata.json  : contexto completo da geração (para debug e histórico)
  - youtube.txt    : título + descrição prontos para copiar e colar no YouTube
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Union

from modules.models import (
    GeneratedContent,
    ImageSource,
    PipelineContext,
    RenderedShort,
    VideoSource,
)

logger = logging.getLogger(__name__)


class OutputModule:

    def run(
        self,
        ctx: PipelineContext,
        source: Union[VideoSource, ImageSource],
        content: GeneratedContent,
        rendered: RenderedShort,
    ) -> Path:
        # ── metadata.json ────────────────────────────────────────────
        metadata = {
            "generated_at": datetime.now().isoformat(),
            "profile": ctx.profile_name,
            "source": source.to_dict() if hasattr(source, "to_dict") else {},
            "content": {
                "curiosity_text": content.curiosity_text,
                "story_text": content.story_text,
                "comment_text": content.comment_text,
                "hashtags": content.hashtags,
                "language": content.language,
            },
            "youtube": {
                "title": content.youtube_title,
                "description": content.youtube_description,
            },
            "output": {
                "video_path": str(rendered.video_path),
                "resolution": f"{rendered.width}x{rendered.height}",
                "duration_seconds": rendered.duration_seconds,
            },
        }
        meta_path = rendered.video_path.with_suffix(".json")
        meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

        # ── youtube.txt ───────────────────────────────────────────────
        yt_path = rendered.video_path.with_suffix(".txt")
        hashtags_line = " ".join(content.hashtags)
        yt_content = f"""TÍTULO
{content.youtube_title or content.curiosity_text}

DESCRIÇÃO
{content.youtube_description or content.story_text}

{hashtags_line}
"""
        yt_path.write_text(yt_content, encoding="utf-8")

        logger.info("=" * 60)
        logger.info("[Output] Short gerado com sucesso!")
        logger.info(f"[Output] Vídeo:    {rendered.video_path}")
        logger.info(f"[Output] YouTube:  {yt_path}")
        logger.info(f"[Output] Duração:  {rendered.duration_seconds:.1f}s")
        logger.info("=" * 60)

        return rendered.video_path