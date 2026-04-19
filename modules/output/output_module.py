"""
output/output_module.py — Salva o resultado final e metadados.

Responsabilidades:
  - Organizar o arquivo .mp4 gerado
  - Salvar metadata.json com todo o contexto da geração
  - Log de sucesso com caminho final

Futuramente: upload para YouTube, notificação Telegram, etc.
"""
import json
import logging
from datetime import datetime
from pathlib import Path

from modules.models import (
    GeneratedContent,
    PipelineContext,
    RenderedShort,
    VideoSource,
)

logger = logging.getLogger(__name__)


class OutputModule:

    def run(
        self,
        ctx: PipelineContext,
        source: VideoSource,
        content: GeneratedContent,
        rendered: RenderedShort,
    ) -> Path:
        metadata = {
            "generated_at": datetime.now().isoformat(),
            "profile": ctx.profile_name,
            "source": source.to_dict(),
            "content": {
                "curiosity_text": content.curiosity_text,
                "comment_text": content.comment_text,
                "hashtags": content.hashtags,
                "language": content.language,
            },
            "output": {
                "video_path": str(rendered.video_path),
                "resolution": f"{rendered.width}x{rendered.height}",
                "duration_seconds": rendered.duration_seconds,
            },
        }

        meta_path = rendered.video_path.with_suffix(".json")
        meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

        logger.info("=" * 60)
        logger.info("[Output] Short gerado com sucesso!")
        logger.info(f"[Output] Vídeo:     {rendered.video_path}")
        logger.info(f"[Output] Metadados: {meta_path}")
        logger.info(f"[Output] Duração:   {rendered.duration_seconds:.1f}s")
        logger.info("=" * 60)

        return rendered.video_path