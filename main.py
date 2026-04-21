"""
main.py — Orquestrador do Shorts Agent.

Pipelines disponíveis (selecionados pelo --template):

  ComentarioImagem  — imagem do Reddit ou URL manual
    python main.py --template ComentarioImagem
    python main.py --template ComentarioImagem --image-url "https://..."
    python main.py --template ComentarioImagem --subreddit brasil

  ComentarioVideo   — vídeo do Reddit ou YouTube
    python main.py --template ComentarioVideo --subreddit-video nextfuckinglevel
    python main.py --template ComentarioVideo --subreddit-video nextfuckinglevel --interactive
    python main.py --template ComentarioVideo --video-url "https://v.redd.it/..."
    python main.py --url "https://youtube.com/watch?v=abc123"

Etapas isoladas (útil para desenvolvimento):
    python main.py --template ComentarioImagem --only ingestion
    python main.py --template ComentarioImagem --only intelligence
    python main.py --template ComentarioImagem --only render
"""
import argparse
import logging
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

from modules.models import PipelineContext

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/agent.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


# ── Config ───────────────────────────────────────────────────────────────────

def load_config(path: str = "config.yaml") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def apply_cli_overrides(config: dict, args: argparse.Namespace) -> dict:
    """Sobrescreve valores do config.yaml com flags da CLI quando fornecidos."""
    mapping = [
        ("max_duration",       ["video", "max_clip_duration"]),
        ("clip_start",         ["video", "clip_start_offset"]),
        ("num_facts",          ["content", "num_facts"]),
        ("comment_tone",       ["content", "comment_tone"]),
        ("curiosity_max_chars",["content", "curiosity_max_chars"]),
        ("comment_max_chars",  ["content", "comment_max_chars"]),
        ("subreddit",          ["image_ingestion", "subreddit"]),
        ("subreddit_video",    ["video_ingestion", "subreddit"]),
    ]
    for attr, keys in mapping:
        val = getattr(args, attr, None)
        if val is not None:
            config[keys[0]][keys[1]] = val
    return config


# ── CLI ───────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Shorts Agent — Gerador automático de YouTube Shorts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Template — determina qual pipeline rodar
    p.add_argument("--template", default="ComentarioVideo",
                   choices=["ComentarioVideo", "ComentarioImagem"],
                   help="Template a usar (default: ComentarioVideo)")
    p.add_argument("--profile", default="CuriosidadesBR",
                   help="Perfil do canal em config.yaml")
    p.add_argument("--only",
                   choices=["ingestion", "intelligence", "assets", "render", "all"],
                   default="all",
                   help="Rodar só uma etapa do pipeline (default: all)")
    p.add_argument("--config", default="config.yaml",
                   help="Caminho para o config.yaml")

    # ── Fontes de conteúdo ────────────────────────────────────────────────────
    src = p.add_argument_group("fontes de conteúdo")
    src.add_argument("--url", default="dummy",
                     help="URL do YouTube (pipeline YouTube)")
    src.add_argument("--image-url", default=None, metavar="URL",
                     help="URL de imagem (ComentarioImagem manual)")
    src.add_argument("--subreddit", default=None, metavar="SUB",
                     help="Subreddit de imagens (ComentarioImagem Reddit)")
    src.add_argument("--video-url", default=None, metavar="URL",
                     help="URL de vídeo direto (ComentarioVideo manual)")
    src.add_argument("--subreddit-video", default=None, metavar="SUB",
                     help="Subreddit de vídeos (ComentarioVideo Reddit)")
    src.add_argument("--interactive", action="store_true",
                     help="Modo interativo: escolha o post via TUI")

    # ── Overrides de conteúdo ─────────────────────────────────────────────────
    ov = p.add_argument_group("overrides de config")
    ov.add_argument("--max-duration", type=int, metavar="S")
    ov.add_argument("--clip-start", type=int, metavar="S")
    ov.add_argument("--num-facts", type=int, metavar="N")
    ov.add_argument("--comment-tone",
                    choices=["surpreso", "humoristico", "reflexivo", "emocional"])
    ov.add_argument("--curiosity-max-chars", type=int, metavar="N")
    ov.add_argument("--comment-max-chars", type=int, metavar="N")

    return p


# ── Detecção de modo ──────────────────────────────────────────────────────────

def _detect_mode(args: argparse.Namespace) -> str:
    """
    Retorna o modo de operação com base nos flags fornecidos.
      "image_reddit"  — ComentarioImagem via Reddit
      "image_manual"  — ComentarioImagem via URL
      "video_reddit"  — ComentarioVideo via Reddit
      "video_manual"  — ComentarioVideo via URL direta
      "video_youtube" — ComentarioVideo via YouTube
    """
    if args.template == "ComentarioImagem":
        return "image_manual" if args.image_url else "image_reddit"

    # ComentarioVideo
    if args.video_url:
        return "video_manual"
    if args.subreddit_video:
        return "video_reddit"
    return "video_youtube"


# ── Sub-pipelines ─────────────────────────────────────────────────────────────

def _run_image_pipeline(args, ctx, pipeline_cfg) -> None:
    """Pipeline ComentarioImagem — Reddit automático, Reddit interativo ou URL manual."""
    from modules.ingestion.image_ingestion_module import (
        ImageIngestionModule, load_image_source,
    )
    from modules.intelligence.image_intelligence_module import ImageIntelligenceModule
    from modules.assets.assets_module import AssetsModule

    mode = _detect_mode(args)

    # ── Ingestion ─────────────────────────────────────────────────────────────
    if args.only in ("ingestion", "all") and pipeline_cfg["run_ingestion"]:
        module = ImageIngestionModule()
        if mode == "image_manual":
            ctx.source = module.run_manual(ctx, args.image_url)
        elif args.interactive:
            ctx.source = module.run_reddit_interactive(ctx)
        else:
            ctx.source = module.run_reddit(ctx)

        if args.only == "ingestion":
            logger.info(f"[Pipeline] Imagem: {ctx.source.image_path}")
            return

    # Cache para etapas isoladas
    if ctx.source is None and args.only != "all":
        ref = args.image_url or ctx.config["image_ingestion"].get("subreddit", "")
        if ref:
            ctx.source = load_image_source(ref)
            if ctx.source:
                logger.info("[Pipeline] ImageSource recuperado do cache.")

    # ── Intelligence ──────────────────────────────────────────────────────────
    if args.only in ("intelligence", "all") and pipeline_cfg["run_intelligence"]:
        _require_source(ctx, "intelligence")
        ctx.content = ImageIntelligenceModule().run(ctx, ctx.source)
        if args.only == "intelligence":
            _print_content(ctx.content)
            return

    # ── Assets ────────────────────────────────────────────────────────────────
    if args.only in ("assets", "all") and pipeline_cfg["run_asset_prep"]:
        _require_source(ctx, "assets")
        ctx.assets = AssetsModule().run_image(ctx, ctx.source)
        if args.only == "assets":
            return


def _run_video_reddit_pipeline(args, ctx, pipeline_cfg) -> None:
    """Pipeline ComentarioVideo — Reddit automático, interativo ou URL de vídeo."""
    from modules.ingestion.video_ingestion_module import (
        VideoIngestionModule, load_video_source,
    )
    from modules.intelligence.video_intelligence_module import VideoIntelligenceModule
    from modules.assets.assets_module import AssetsModule

    mode = _detect_mode(args)

    # ── Ingestion ─────────────────────────────────────────────────────────────
    if args.only in ("ingestion", "all") and pipeline_cfg["run_ingestion"]:
        module = VideoIngestionModule()
        if mode == "video_manual":
            ctx.source = module.run_manual(ctx, args.video_url)
        elif args.interactive:
            ctx.source = module.run_reddit_interactive(ctx)
        else:
            ctx.source = module.run_reddit(ctx)

        if args.only == "ingestion":
            logger.info(f"[Pipeline] Clip: {ctx.source.clip_path}")
            return

    # Cache para etapas isoladas
    if ctx.source is None and args.only != "all":
        ref = args.video_url or ""
        if ref:
            ctx.source = load_video_source(ref)
            if ctx.source:
                logger.info("[Pipeline] VideoSource Reddit recuperado do cache.")

    # ── Intelligence ──────────────────────────────────────────────────────────
    if args.only in ("intelligence", "all") and pipeline_cfg["run_intelligence"]:
        _require_source(ctx, "intelligence")
        ctx.content = VideoIntelligenceModule().run(ctx, ctx.source)
        if args.only == "intelligence":
            _print_content(ctx.content)
            return

    # ── Assets ────────────────────────────────────────────────────────────────
    if args.only in ("assets", "all") and pipeline_cfg["run_asset_prep"]:
        _require_source(ctx, "assets")
        ctx.assets = AssetsModule().run_video(ctx, ctx.source)
        if args.only == "assets":
            return


def _run_video_youtube_pipeline(args, ctx, pipeline_cfg) -> None:
    """Pipeline ComentarioVideo — YouTube."""
    from modules.ingestion.ingestion_module import IngestionModule, load_source
    from modules.intelligence.intelligence_module import VideoIntelligenceModule
    from modules.assets.assets_module import AssetsModule

    # ── Ingestion ─────────────────────────────────────────────────────────────
    if args.only in ("ingestion", "all") and pipeline_cfg["run_ingestion"]:
        ctx.source = IngestionModule().run(ctx, args.url)
        if args.only == "ingestion":
            logger.info("[Pipeline] Ingestion YouTube concluído.")
            return

    # Cache para etapas isoladas
    if ctx.source is None and args.only != "all" and args.url != "dummy":
        ctx.source = load_source(args.url)
        if ctx.source:
            logger.info("[Pipeline] VideoSource YouTube recuperado do cache.")

    # ── Intelligence ──────────────────────────────────────────────────────────
    if args.only in ("intelligence", "all") and pipeline_cfg["run_intelligence"]:
        _require_source(ctx, "intelligence")
        ctx.content = VideoIntelligenceModule().run(ctx, ctx.source)
        if args.only == "intelligence":
            _print_content(ctx.content)
            return

    # ── Assets ────────────────────────────────────────────────────────────────
    if args.only in ("assets", "all") and pipeline_cfg["run_asset_prep"]:
        _require_source(ctx, "assets")
        ctx.assets = AssetsModule().run_video(ctx, ctx.source)
        if args.only == "assets":
            return


# ── Orquestrador principal ────────────────────────────────────────────────────

def run_pipeline(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    config = apply_cli_overrides(config, args)

    if args.profile not in config["profiles"]:
        logger.error(f"Perfil '{args.profile}' não encontrado. "
                     f"Disponíveis: {list(config['profiles'].keys())}")
        sys.exit(1)

    ctx = PipelineContext(profile_name=args.profile, config=config)
    pipeline_cfg = config["pipeline"]
    mode = _detect_mode(args)

    logger.info(f"Perfil: {args.profile} | Template: {args.template} | Modo: {mode}")

    # ── Etapas 1-3: variam por pipeline ──────────────────────────────────────
    if mode in ("image_reddit", "image_manual"):
        _run_image_pipeline(args, ctx, pipeline_cfg)
    elif mode in ("video_reddit", "video_manual"):
        _run_video_reddit_pipeline(args, ctx, pipeline_cfg)
    else:
        _run_video_youtube_pipeline(args, ctx, pipeline_cfg)

    # ── Etapa 4: Render (igual para todos) ───────────────────────────────────
    if args.only in ("render", "all") and pipeline_cfg["run_render"]:
        if any(x is None for x in [ctx.source, ctx.content, ctx.assets]):
            logger.error("Render requer Ingestion + Intelligence + Assets completos.")
            sys.exit(1)
        from modules.render.render_module import RenderModule
        ctx.rendered = RenderModule().run(ctx, ctx.assets, ctx.content,
                                          template=args.template)

    # ── Etapa 5: Output (igual para todos) ───────────────────────────────────
    if pipeline_cfg["run_output"] and ctx.rendered:
        from modules.output.output_module import OutputModule
        OutputModule().run(ctx, ctx.source, ctx.content, ctx.rendered)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _require_source(ctx: PipelineContext, stage: str) -> None:
    if ctx.source is None:
        logger.error(f"Etapa '{stage}' requer ingestion concluído primeiro "
                     f"(rode --only ingestion antes).")
        sys.exit(1)


def _print_content(content) -> None:
    print("\n" + "=" * 50)
    print(f"HOOK:\n{content.curiosity_text}")
    print(f"\nSTORY:\n{content.story_text[:200]}...")
    print(f"\nCOMENTÁRIO:\n{content.comment_text}")
    print(f"\nHASHTAGS: {' '.join(content.hashtags)}")
    print("=" * 50)


if __name__ == "__main__":
    Path("logs").mkdir(exist_ok=True)
    parser = build_parser()
    args = parser.parse_args()
    run_pipeline(args)