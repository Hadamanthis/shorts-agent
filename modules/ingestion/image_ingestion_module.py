"""
image_ingestion/image_ingestion_module.py — Obtém imagens para o ComentarioImagem.
"""
import hashlib
import json
import logging
import re
import sys
import urllib.request
from pathlib import Path
from typing import Optional

from modules.models import ImageSource, PipelineContext

logger = logging.getLogger(__name__)

IMAGE_DIR   = Path("output") / "images"
CACHE_DIR   = Path("output") / "cache"
REDDIT_BASE = "https://www.reddit.com"
HEADERS     = {"User-Agent": "shorts-agent/1.0 (content creator bot)"}


def _url_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:12]


def _ansi_link(url: str, text: str) -> str:
    """Retorna URL clicável via escape ANSI OSC 8 (suportado por iTerm2, Kitty, WezTerm, GNOME Terminal etc.)"""
    return f"\033]8;;{url}\033\\{text}\033]8;;\033\\"


def save_image_source(src: ImageSource) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"image_{_url_id(src.source_url)}.json"
    path.write_text(json.dumps({
        "origin": src.origin,
        "image_path": str(src.image_path),
        "source_url": src.source_url,
        "title": src.title,
        "context_comments": src.context_comments,
        "subreddit": src.subreddit,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"[ImageIngestion] Cache salvo: {path}")
    return path


def load_image_source(url: str) -> Optional[ImageSource]:
    path = CACHE_DIR / f"image_{_url_id(url)}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    logger.info(f"[ImageIngestion] Cache carregado: {path}")
    return ImageSource(
        origin=data["origin"],
        image_path=Path(data["image_path"]),
        source_url=data["source_url"],
        title=data["title"],
        context_comments=data["context_comments"],
        subreddit=data["subreddit"],
    )


class ImageIngestionModule:

    def run_reddit(self, ctx: PipelineContext) -> ImageSource:
        """Modo automático — pega o top-1 sem interação. Mantido para uso programático."""
        cfg          = ctx.config.get("image_ingestion", {})
        subreddit    = cfg.get("subreddit", "interestingasfuck")
        listing      = cfg.get("listing", "hot")
        time_filter  = cfg.get("time_filter", "day")
        max_comments = cfg.get("max_comments", 5)
        min_score    = cfg.get("min_score", 1000)

        logger.info(f"[ImageIngestion] Reddit — r/{subreddit} [{listing}]")
        posts      = self._find_reddit_posts(subreddit, listing, time_filter, min_score, limit=1)
        post       = posts[0]
        image_path = self._download_image(post["url"], post["id"])
        comments   = self._fetch_reddit_comments(post["permalink"], max_comments)

        src = ImageSource(
            origin="reddit",
            image_path=image_path,
            source_url=REDDIT_BASE + post["permalink"],
            title=post.get("title", ""),
            context_comments=comments,
            subreddit=subreddit,
        )
        save_image_source(src)
        return src

    def run_reddit_interactive(self, ctx: PipelineContext) -> ImageSource:
        """Modo interativo — exibe top-n posts e deixa o usuário escolher via TUI."""
        cfg          = ctx.config.get("image_ingestion", {})
        subreddit    = cfg.get("subreddit", "interestingasfuck")
        listing      = cfg.get("listing", "hot")
        time_filter  = cfg.get("time_filter", "day")
        max_comments = cfg.get("max_comments", 5)
        min_score    = cfg.get("min_score", 1000)
        top_n        = cfg.get("top_n_posts", 5)

        logger.info(f"[ImageIngestion] Reddit interativo — r/{subreddit} [{listing}] top {top_n}")
        posts = self._find_reddit_posts(subreddit, listing, time_filter, min_score, limit=top_n)

        post = self._prompt_post_selection(posts, subreddit)

        logger.info(f"[ImageIngestion] Post escolhido: {post['title'][:60]}")
        image_path = self._download_image(post["url"], post["id"])
        comments   = self._fetch_reddit_comments(post["permalink"], max_comments)

        src = ImageSource(
            origin="reddit",
            image_path=image_path,
            source_url=REDDIT_BASE + post["permalink"],
            title=post.get("title", ""),
            context_comments=comments,
            subreddit=subreddit,
        )
        save_image_source(src)
        return src

    def run_manual(self, ctx: PipelineContext, image_url: str) -> ImageSource:
        logger.info(f"[ImageIngestion] Manual — {image_url}")
        image_path = self._download_image(image_url, _url_id(image_url))
        src = ImageSource(
            origin="manual",
            image_path=image_path,
            source_url=image_url,
            title="",
            context_comments=[],
            subreddit="",
        )
        save_image_source(src)
        return src

    # ── TUI ──────────────────────────────────────────────────────────────────

    def _prompt_post_selection(self, posts: list[dict], subreddit: str) -> dict:
        """
        Exibe menu interativo com setas usando questionary.
        Fallback para input numérico se questionary não estiver instalado.
        """
        try:
            import questionary
            from questionary import Style

            custom_style = Style([
                ("qmark",        "fg:#00b4d8 bold"),
                ("question",     "fg:#ffffff bold"),
                ("highlighted",  "fg:#00b4d8 bold"),
                ("selected",     "fg:#90e0ef"),
                ("pointer",      "fg:#00b4d8 bold"),
                ("answer",       "fg:#90e0ef bold"),
            ])

            # Monta as choices — o valor é o índice para recuperar o post depois
            choices = []
            for i, p in enumerate(posts):
                score    = p.get("score", 0)
                n_comms  = p.get("num_comments", 0)
                title    = p.get("title", "")
                img_url  = p.get("url", "")

                # Título truncado para caber no terminal
                title_short = title if len(title) <= 72 else title[:69] + "…"

                # URL clicável (OSC 8) — aparece como texto curto mas é clicável em terminais compatíveis
                clickable = _ansi_link(img_url, "🔗 ver imagem")

                label = (
                    f"[{i+1}] {title_short}\n"
                    f"     ⬆ {score:,}  💬 {n_comms:,}  {clickable}"
                )
                choices.append(questionary.Choice(title=label, value=i))

            print(f"\n📋 Posts disponíveis em r/{subreddit}:\n")
            selected_index = questionary.select(
                "Escolha um post com ↑↓ e Enter:",
                choices=choices,
                style=custom_style,
                use_shortcuts=False,
            ).ask()

            if selected_index is None:
                # Usuário cancelou com Ctrl+C
                print("\nOperação cancelada.")
                sys.exit(0)

            return posts[selected_index]

        except ImportError:
            return self._prompt_post_selection_fallback(posts, subreddit)

    def _prompt_post_selection_fallback(self, posts: list[dict], subreddit: str) -> dict:
        """Fallback numérico caso questionary não esteja disponível."""
        print(f"\n📋 Posts disponíveis em r/{subreddit}:\n")
        for i, p in enumerate(posts):
            score   = p.get("score", 0)
            n_comms = p.get("num_comments", 0)
            title   = p.get("title", "")
            img_url = p.get("url", "")
            clickable = _ansi_link(img_url, img_url)
            print(f"  [{i+1}] {title}")
            print(f"       ⬆ {score:,}  💬 {n_comms:,}  {clickable}\n")

        while True:
            try:
                raw = input(f"Escolha um número [1-{len(posts)}]: ").strip()
                idx = int(raw) - 1
                if 0 <= idx < len(posts):
                    return posts[idx]
                print(f"  Digite um número entre 1 e {len(posts)}.")
            except (ValueError, KeyboardInterrupt):
                print("\nOperação cancelada.")
                sys.exit(0)

    # ── Internos ─────────────────────────────────────────────────────────────

    def _fetch_json(self, url: str) -> dict:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())

    def _find_reddit_posts(
        self,
        subreddit: str,
        listing: str,
        time_filter: str,
        min_score: int,
        limit: int,
    ) -> list[dict]:
        """
        Retorna até `limit` posts com imagem válida do subreddit.
        Faz paginação automática se necessário para encontrar posts suficientes.
        """
        IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")
        IMGUR_RE = re.compile(r"https?://(?:i\.)?imgur\.com/(\w+)(?:\.\w+)?$")

        # Busca mais itens do que o necessário para compensar posts sem imagem
        fetch_limit = min(limit * 6, 100)
        url = f"{REDDIT_BASE}/r/{subreddit}/{listing}.json?limit={fetch_limit}"
        if listing == "top":
            url += f"&t={time_filter}"

        raw_posts = self._fetch_json(url)["data"]["children"]
        found: list[dict] = []

        for item in raw_posts:
            if len(found) >= limit:
                break

            p = item["data"]
            if p.get("score", 0) < min_score or p.get("is_video") or p.get("stickied"):
                continue

            post_url: str = p.get("url", "")

            if any(post_url.lower().endswith(ext) for ext in IMAGE_EXTENSIONS):
                found.append(p)
                continue

            m = IMGUR_RE.match(post_url)
            if m:
                p["url"] = f"https://i.imgur.com/{m.group(1)}.jpg"
                found.append(p)
                continue

            if "gallery_data" in p and p.get("media_metadata"):
                first_id = list(p["media_metadata"].keys())[0]
                meta = p["media_metadata"][first_id]
                if meta.get("status") == "valid" and "s" in meta:
                    img_url = meta["s"].get("u", "").replace("&amp;", "&")
                    if img_url:
                        p["url"] = img_url
                        found.append(p)
                        continue

        if not found:
            raise RuntimeError(
                f"Nenhum post com imagem em r/{subreddit} com score >= {min_score}. "
                f"Tente diminuir min_score ou mudar o subreddit."
            )

        return found

    def _download_image(self, url: str, uid: str) -> Path:
        IMAGE_DIR.mkdir(parents=True, exist_ok=True)
        ext = Path(url.split("?")[0]).suffix.lower()
        if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
            ext = ".jpg"
        dest = IMAGE_DIR / f"img_{uid}{ext}"
        if dest.exists():
            logger.info(f"[ImageIngestion] Imagem já existe, pulando download: {dest}")
            return dest
        logger.info(f"[ImageIngestion] Baixando imagem: {url}")
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=30) as resp:
            dest.write_bytes(resp.read())
        logger.info(f"[ImageIngestion] Imagem salva: {dest}")
        return dest

    def _fetch_reddit_comments(self, permalink: str, max_n: int) -> list[str]:
        url = f"{REDDIT_BASE}{permalink}.json?limit={max_n}&sort=top"
        try:
            comments_data = self._fetch_json(url)[1]["data"]["children"]
            comments = []
            for c in comments_data:
                body = c["data"].get("body", "").strip()
                if body and body not in ("[deleted]", "[removed]"):
                    comments.append(body)
                if len(comments) >= max_n:
                    break
            return comments
        except Exception as e:
            logger.warning(f"[ImageIngestion] Não foi possível buscar comentários: {e}")
            return []