"""
render/render_module.py — Orquestra a renderização delegando ao Remotion CLI.

Responsabilidades:
  - Calcular duração e frames
  - Delegar sync de assets  -> assets_sync.py
  - Delegar montagem de props -> props_builder.py
  - Chamar `npx remotion render`
  - Devolver RenderedShort
"""
import json
import logging
import platform
import subprocess
from datetime import datetime
from pathlib import Path

from modules.models import GeneratedContent, PipelineContext, PreparedAssets, RenderedShort
from modules.render.assets_sync import sync_public
from modules.render.props_builder import build_props, get_duration

logger = logging.getLogger(__name__)

REMOTION_DIR = Path("video-renderer")
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

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"short_{ctx.profile_name}_{timestamp}.mp4"

        fps = ctx.config["layout"].get("fps", 30)

        # 1. Duração
        if template == "ComentarioVideo":
            duration_seconds = get_duration(assets.clip_path)
        else:
            duration_seconds = float(ctx.config["comentario-reddit"].get("short_duration", 30))
        duration_frames = int(duration_seconds * fps)

        logger.info(f"[Render] Template: {template}")
        logger.info(f"[Render] Duração: {duration_seconds:.1f}s -> {duration_frames} frames @ {fps}fps")

        # 2. Sincroniza assets para public/
        sync_public(assets, template, fps)

        # 3. Monta props
        props = build_props(assets, content, template)
        logger.info(f"[Render] Props: {json.dumps(props, ensure_ascii=False)}")

        # 4. Renderiza
        self._run_remotion(template, props, output_path, duration_frames, fps)

        logger.info(f"[Render] Short gerado: {output_path}")
        return RenderedShort(
            video_path=output_path,
            width=ctx.config["layout"]["width"],
            height=ctx.config["layout"]["height"],
            duration_seconds=duration_seconds,
        )

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
                "Certifique-se que a pasta video-renderer/ existe e rodou 'npm install'."
            )

        cmd = [
            NPX, "remotion", "render",
            "src/index.ts",
            template,
            str(output_path.resolve()),
            "--props", json.dumps(props, ensure_ascii=False),
            "--duration", str(duration_frames),
            "--fps", str(fps),
            "--offthread-video-cache-size-in-bytes", "512000000",
        ]

        logger.info(f"[Render] Executando Remotion render para '{template}'...")
        result = subprocess.run(
            cmd,
            cwd=str(REMOTION_DIR.resolve()),
            capture_output=False,
            timeout=600,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Remotion render falhou com código {result.returncode}.")