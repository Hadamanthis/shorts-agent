"""
main.py — Orquestrador do Shorts Agent.

Uso:
  python main.py --url <URL> [opções]

Exemplos:
  # Básico com perfil padrão
  python main.py --url "https://youtube.com/watch?v=abc123"

  # Escolher perfil, assunto e duração máxima na hora
  python main.py --url "https://youtube.com/watch?v=abc123" \\
                 --profile FilmFactsEN \\
                 --max-duration 20 \\
                 --num-facts 2 \\
                 --comment-tone humoristico

  # Testar só o download (sem render)
  python main.py --url "..." --only ingestion

  # Testar só a inteligência (com clip já baixado)
  python main.py --url "..." --only intelligence

  # Testar só o render (conteúdo e clip já existem)
  python main.py --url "..." --only render
"""
import argparse
import logging
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

# Carrega .env antes de qualquer import que precise de variáveis de ambiente
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


def load_config(config_path: str = "config.yaml") -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def apply_cli_overrides(config: dict, args: argparse.Namespace) -> dict:
    """
    Permite sobrescrever parâmetros do config.yaml diretamente pela CLI.
    Só altera o que foi explicitamente passado.
    """
    if args.max_duration is not None:
        config["video"]["max_clip_duration"] = args.max_duration

    if args.clip_start is not None:
        config["video"]["clip_start_offset"] = args.clip_start

    if args.num_facts is not None:
        config["content"]["num_facts"] = args.num_facts

    if args.comment_tone is not None:
        config["content"]["comment_tone"] = args.comment_tone

    if args.curiosity_max_chars is not None:
        config["content"]["curiosity_max_chars"] = args.curiosity_max_chars

    if args.comment_max_chars is not None:
        config["content"]["comment_max_chars"] = args.comment_max_chars

    if args.subreddit is not None:
        config["image_ingestion"]["subreddit"] = args.subreddit

    return config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Shorts Agent — Gerador automático de YouTube Shorts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Obrigatório
    parser.add_argument("--url", required=True, help="URL do vídeo de origem")

    # Perfil
    parser.add_argument(
        "--profile",
        default="CuriosidadesBR",
        help="Nome do perfil em config.yaml (default: CuriosidadesBR)",
    )

    # Template Remotion
    parser.add_argument(
        "--template",
        default="ComentarioVideo",
        choices=["ComentarioVideo", "ComentarioImagem"],
        help="Template Remotion a usar (default: ComentarioVideo)",
    )

    # Overrides do vídeo de entrada
    parser.add_argument("--max-duration", type=int, metavar="SEGUNDOS",
                        help="Duração máxima do trecho recortado")
    parser.add_argument("--clip-start", type=int, metavar="SEGUNDOS",
                        help="Ponto de início do trecho no vídeo original")

    # Overrides do conteúdo gerado
    parser.add_argument("--num-facts", type=int, metavar="N",
                        help="Número de fatos/curiosidades na zona 1")
    parser.add_argument("--comment-tone",
                        choices=["surpreso", "humoristico", "reflexivo", "emocional"],
                        help="Tom do comentário gerado")
    parser.add_argument("--curiosity-max-chars", type=int, metavar="N",
                        help="Máximo de caracteres da curiosidade")
    parser.add_argument("--comment-max-chars", type=int, metavar="N",
                        help="Máximo de caracteres do comentário")

    # Modo de execução parcial (útil para desenvolvimento e testes)
    parser.add_argument(
        "--only",
        choices=["ingestion", "intelligence", "assets", "render", "all"],
        default="all",
        help="Executar apenas uma etapa do pipeline (default: all)",
    )

    # Pipeline de imagem
    parser.add_argument(
        "--image-url",
        default=None,
        metavar="URL",
        help="URL de imagem para o ComentarioImagem (modo manual)",
    )
    parser.add_argument(
        "--subreddit",
        default=None,
        metavar="SUB",
        help="Subreddit para buscar imagem viral (ex: interestingasfuck)",
    )

    # Config alternativo
    parser.add_argument("--config", default="config.yaml",
                        help="Caminho para o arquivo de configuração")

    return parser


def run_pipeline(args: argparse.Namespace) -> None:
    # Carrega e aplica overrides
    config = load_config(args.config)
    config = apply_cli_overrides(config, args)

    # Valida perfil
    if args.profile not in config["profiles"]:
        available = list(config["profiles"].keys())
        logger.error(f"Perfil '{args.profile}' não encontrado. Disponíveis: {available}")
        sys.exit(1)

    ctx = PipelineContext(profile_name=args.profile, config=config)
    pipeline_cfg = config["pipeline"]

    logger.info(f"Perfil: {args.profile} | URL: {args.url} | Template: {args.template}")

    is_image_pipeline = (args.template == "ComentarioImagem")

    # ════════════════════════════════════════════════════════
    # PIPELINE DE VÍDEO (ComentarioVideo) — YouTube
    # ════════════════════════════════════════════════════════
    if not is_image_pipeline:

        # ---- ETAPA 1: INGESTION ----
        if args.only in ("ingestion", "all") and pipeline_cfg["run_ingestion"]:
            from modules.ingestion.ingestion_module import IngestionModule
            ctx.source = IngestionModule().run(ctx, args.url)
            if args.only == "ingestion":
                logger.info("[Pipeline] Etapa 'ingestion' concluída. Encerrando.")
                return

        # Tenta carregar VideoSource do cache se etapa isolada
        if ctx.source is None and args.only != "all" and args.url:
            from modules.ingestion.ingestion_module import load_source
            ctx.source = load_source(args.url)
            if ctx.source is not None:
                logger.info("[Pipeline] VideoSource recuperado do cache.")

        # ---- ETAPA 2: INTELLIGENCE ----
        if args.only in ("intelligence", "all") and pipeline_cfg["run_intelligence"]:
            if ctx.source is None:
                logger.error("Intelligence (vídeo) requer ingestion concluído primeiro.")
                sys.exit(1)
            from modules.intelligence.intelligence_module import IntelligenceModule
            ctx.content = IntelligenceModule().run(ctx, ctx.source)
            if args.only == "intelligence":
                _print_generated_content(ctx.content)
                return

        # ---- ETAPA 3: ASSETS ----
        if args.only in ("assets", "all") and pipeline_cfg["run_asset_prep"]:
            if ctx.source is None:
                logger.error("Assets (vídeo) requer ingestion concluído primeiro.")
                sys.exit(1)
            from modules.assets.assets_module import AssetsModule
            ctx.assets = AssetsModule().run_video(ctx, ctx.source)
            if args.only == "assets":
                return

    # ════════════════════════════════════════════════════════
    # PIPELINE DE IMAGEM (ComentarioImagem) — Reddit / Manual
    # ════════════════════════════════════════════════════════
    else:

        # ---- ETAPA 1: IMAGE INGESTION ----
        if args.only in ("ingestion", "all") and pipeline_cfg["run_ingestion"]:
            from modules.ingestion.image_ingestion_module import (
                ImageIngestionModule, load_image_source
            )
            module = ImageIngestionModule()
            if args.image_url:
                ctx.source = module.run_manual(ctx, args.image_url)
            else:
                # Modo interativo: exibe top-n e deixa o usuário escolher
                ctx.source = module.run_reddit_interactive(ctx)
            if args.only == "ingestion":
                logger.info(f"[Pipeline] Imagem: {ctx.source.image_path}")
                return

        # Tenta carregar ImageSource do cache
        if ctx.source is None and args.only != "all":
            from modules.ingestion.image_ingestion_module import load_image_source
            ref = args.image_url or ctx.config["image_ingestion"].get("subreddit", "")
            if ref:
                ctx.source = load_image_source(ref)
                if ctx.source:
                    logger.info("[Pipeline] ImageSource recuperado do cache.")

        # ---- ETAPA 2: IMAGE INTELLIGENCE ----
        if args.only in ("intelligence", "all") and pipeline_cfg["run_intelligence"]:
            if ctx.source is None:
                logger.error("Intelligence (imagem) requer image ingestion concluído primeiro.")
                sys.exit(1)
            from modules.intelligence.image_intelligence_module import ImageIntelligenceModule
            ctx.content = ImageIntelligenceModule().run(ctx, ctx.source)
            if args.only == "intelligence":
                _print_generated_content(ctx.content)
                return

        # ---- ETAPA 3: ASSETS ----
        if args.only in ("assets", "all") and pipeline_cfg["run_asset_prep"]:
            if ctx.source is None:
                logger.error("Assets (imagem) requer image ingestion concluído primeiro.")
                sys.exit(1)
            from modules.assets.assets_module import AssetsModule
            ctx.assets = AssetsModule().run_image(ctx, ctx.source)
            if args.only == "assets":
                return

    # ---- ETAPA 4: RENDER ----
    if args.only in ("render", "all") and pipeline_cfg["run_render"]:
        if any(x is None for x in [ctx.source, ctx.content, ctx.assets]):
            logger.error("Render requer Ingestion + Intelligence + Assets completos.")
            sys.exit(1)
        from modules.render.render_module import RenderModule
        ctx.rendered = RenderModule().run(
            ctx, ctx.assets, ctx.content, template=args.template
        )

    # ---- ETAPA 5: OUTPUT ----
    if pipeline_cfg["run_output"] and ctx.rendered:
        from modules.output.output_module import OutputModule
        OutputModule().run(ctx, ctx.source, ctx.content, ctx.rendered)

def _print_generated_content(content) -> None:
    print("\n" + "=" * 50)
    print(f"CURIOSIDADE:\n{content.curiosity_text}")
    print(f"\nCOMENTÁRIO:\n{content.comment_text}")
    print(f"\nHASHTAGS: {' '.join(content.hashtags)}")
    print("=" * 50)


if __name__ == "__main__":
    Path("logs").mkdir(exist_ok=True)
    parser = build_parser()
    args = parser.parse_args()
    run_pipeline(args)