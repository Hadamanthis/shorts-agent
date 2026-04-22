"""
main.py — Orquestrador do Shorts Agent.

Pipelines disponíveis (selecionados pelo --template):

  comentario-reddit — busca posts (imagem ou vídeo) de um subreddit.
    O tipo do post escolhido determina o template de render automaticamente.

    python main.py --template comentario-reddit --subreddit interestingasfuck --profile Synthvator
    python main.py --template comentario-reddit --subreddit nextfuckinglevel --profile Synthvator
    python main.py --template comentario-reddit --subreddit interestingasfuck --profile Synthvator --image-url "https://..."
    python main.py --template comentario-reddit --subreddit interestingasfuck --profile Synthvator --video-url "https://v.redd.it/..."

  comentario-youtube — vídeo do YouTube
    python main.py --template comentario-youtube --url "https://youtube.com/watch?v=abc123" --profile Synthvator
"""
import argparse
import logging
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

from modules.models import PipelineContext, ImageSource, VideoSource

# No Windows o stdout pode ser CP1252 — força UTF-8 para não travar em caracteres especiais
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

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


# ── Config ────────────────────────────────────────────────────────────────────

def load_config(path: str = "config.yaml") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def apply_cli_overrides(config: dict, args: argparse.Namespace) -> dict:
    """Sobrescreve valores do config.yaml com flags da CLI quando fornecidos."""
    reddit_cfg = config.setdefault("comentario-reddit", {})
    mapping = [
        ("comment_tone",        ["content",          "comment_tone"]),
        ("curiosity_max_chars", ["content",          "curiosity_max_chars"]),
        ("comment_max_chars",   ["content",          "comment_max_chars"]),
        ("subreddit",           ["comentario-reddit","subreddit"]),
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

    p.add_argument("--template", default="comentario-reddit",
                   choices=["comentario-reddit", "comentario-youtube"],
                   help="Pipeline a usar (default: comentario-reddit)")
    p.add_argument("--profile", default="Synthvator",
                   help="Perfil do canal em config.yaml")
    p.add_argument("--config", default="config.yaml",
                   help="Caminho para o config.yaml")

    # ── Fontes de conteúdo ────────────────────────────────────────────────────
    src = p.add_argument_group("fontes de conteúdo")
    src.add_argument("--subreddit", default=None, metavar="SUB",
                     help="Subreddit a listar (comentario-reddit)")
    src.add_argument("--image-url", default=None, metavar="URL",
                     help="URL de imagem direta, pula a listagem (comentario-reddit)")
    src.add_argument("--video-url", default=None, metavar="URL",
                     help="URL de vídeo direto, pula a listagem (comentario-reddit)")
    src.add_argument("--url", default=None, metavar="URL",
                     help="URL do YouTube (comentario-youtube)")
    src.add_argument("--post-index", default=None, type=int, metavar="N",
                     help="Índice do post Reddit já selecionado (bypassa TUI, usado pela GUI)")

    # ── Overrides de conteúdo ─────────────────────────────────────────────────
    ov = p.add_argument_group("overrides de config")
    ov.add_argument("--comment-tone",
                    choices=["surpreso", "humoristico", "reflexivo", "emocional", "assustado"])
    ov.add_argument("--curiosity-max-chars", type=int, metavar="N")
    ov.add_argument("--comment-max-chars",   type=int, metavar="N")

    return p


# ── Pipelines ─────────────────────────────────────────────────────────────────

def _run_reddit_pipeline(args, ctx) -> None:
    """
    Busca posts (imagem ou vídeo) de um subreddit, exibe TUI paginada,
    e despacha para o render correto conforme o tipo do post escolhido.
    """
    from modules.ingestion.ingestion_reddit import RedditIngestionModule
    from modules.intelligence.intelligence_reddit import RedditIntelligenceModule
    from modules.assets.assets_module import AssetsModule
    from modules.render.render_module import RenderModule
    from modules.output.output_module import OutputModule

    pipeline_cfg = ctx.config["pipeline"]
    module       = RedditIngestionModule()

    # ── Ingestion ─────────────────────────────────────────────────────────────
    if args.image_url:
        ctx.source = module.run_manual(ctx, args.image_url, mode="image")
    elif args.video_url:
        ctx.source = module.run_manual(ctx, args.video_url, mode="video")
    elif getattr(args, "post_index", None) is not None:
        # Vem da GUI — índice já escolhido, sem TUI
        ctx.source = module.run_from_index(ctx, [], args.post_index)
    else:
        ctx.source = module.run_interactive(ctx)

    # Detecta o tipo do post escolhido
    render_template = "ComentarioImagem" if isinstance(ctx.source, ImageSource) else "ComentarioVideo"
    mode            = "image"            if isinstance(ctx.source, ImageSource) else "video"
    logger.info(f"[Pipeline] Tipo detectado: {mode} -> template: {render_template}")

    # ── Intelligence ──────────────────────────────────────────────────────────
    if pipeline_cfg["run_intelligence"]:
        ctx.content = RedditIntelligenceModule().run(ctx, ctx.source, mode)

    # ── Assets ────────────────────────────────────────────────────────────────
    if pipeline_cfg["run_asset_prep"]:
        if mode == "image":
            ctx.assets = AssetsModule().run_image(ctx, ctx.source)
        else:
            ctx.assets = AssetsModule().run_video(ctx, ctx.source)

    # ── Render ────────────────────────────────────────────────────────────────
    if pipeline_cfg["run_render"]:
        ctx.rendered = RenderModule().run(ctx, ctx.assets, ctx.content,
                                          template=render_template)

    # ── Output ────────────────────────────────────────────────────────────────
    if pipeline_cfg["run_output"] and ctx.rendered:
        OutputModule().run(ctx, ctx.source, ctx.content, ctx.rendered)


def _run_youtube_pipeline(args, ctx) -> None:
    """Pipeline YouTube — baixa vídeo, gera conteúdo e renderiza."""
    from modules.ingestion.ingestion_module import IngestionModule
    from modules.intelligence.intelligence_module import IntelligenceModule
    from modules.assets.assets_module import AssetsModule
    from modules.render.render_module import RenderModule
    from modules.output.output_module import OutputModule

    if not args.url:
        logger.error("--url é obrigatório para comentario-youtube.")
        sys.exit(1)

    pipeline_cfg = ctx.config["pipeline"]

    # ── Ingestion ─────────────────────────────────────────────────────────────
    ctx.source = IngestionModule().run(ctx, args.url)

    # ── Intelligence ──────────────────────────────────────────────────────────
    if pipeline_cfg["run_intelligence"]:
        ctx.content = IntelligenceModule().run(ctx, ctx.source)

    # ── Assets ────────────────────────────────────────────────────────────────
    if pipeline_cfg["run_asset_prep"]:
        ctx.assets = AssetsModule().run_video(ctx, ctx.source)

    # ── Render ────────────────────────────────────────────────────────────────
    if pipeline_cfg["run_render"]:
        ctx.rendered = RenderModule().run(ctx, ctx.assets, ctx.content,
                                          template="ComentarioVideo")

    # ── Output ────────────────────────────────────────────────────────────────
    if pipeline_cfg["run_output"] and ctx.rendered:
        OutputModule().run(ctx, ctx.source, ctx.content, ctx.rendered)


# ── Orquestrador principal ────────────────────────────────────────────────────

def run_pipeline(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    config = apply_cli_overrides(config, args)

    if args.profile not in config["profiles"]:
        logger.error(f"Perfil '{args.profile}' não encontrado. "
                     f"Disponíveis: {list(config['profiles'].keys())}")
        sys.exit(1)

    ctx = PipelineContext(profile_name=args.profile, config=config)
    logger.info(f"Perfil: {args.profile} | Template: {args.template}")

    if args.template == "comentario-reddit":
        if not args.image_url and not args.video_url and not args.subreddit and getattr(args, "post_index", None) is None:
            logger.error("--subreddit é obrigatório para comentario-reddit "
                         "(a menos que passe --image-url ou --video-url).")
            sys.exit(1)
        _run_reddit_pipeline(args, ctx)
    else:
        _run_youtube_pipeline(args, ctx)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    Path("logs").mkdir(exist_ok=True)
    parser = build_parser()
    args   = parser.parse_args()
    run_pipeline(args)