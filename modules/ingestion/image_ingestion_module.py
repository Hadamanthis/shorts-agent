"""
image_ingestion/image_ingestion_module.py — Obtém imagens para o ComentarioImagem.

Dois modos selecionados automaticamente pelo main.py:
  - reddit : busca posts virais com imagem num subreddit configurado
  - manual : recebe URL ou path local direto pela CLI (--image-url / --image-path)

Responsabilidades:
  - Encontrar / receber a imagem
  - Baixar para output/images/
  - Coletar contexto textual (título + comentários do Reddit, ou vazio se manual)
  - Salvar cache em output/cache/image_<id>.json
  - Devolver um ImageSource preenchido

Não sabe nada sobre LLM, layout ou render.
"""
import hashlib
import json
import logging
import re
import urllib.request
from pathlib import Path
from typing import Optional

from modules.models import ImageSource, PipelineContext

logger = logging.getLogger(__name__)

IMAGE_DIR   = Path("output") / "images"
CACHE_DIR   = Path("output") / "cache"
REDDIT_BASE = "https://www.reddit.com"

HEADERS = {
    "User-Agent": "shorts-agent/1.0 (content creator bot)"
}


# ── Helpers de cache ────────────────────────────────────────────────────────

def _url_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:12]


def save_image_source(src: ImageSource) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_id = _url_id(src.url)
    path = CACHE_DIR / f"image_{cache_id}.json"
    data = {
        "origin": src.origin,
        "image_path": str(src.image_path),
        "source_url": src.url,
        "title": src.title,
        "context_comments": src.context_comments,
        "subreddit": src.subreddit,
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    logger.info(f"[ImageIngestion] Cache salvo: {path}")
    return path


def load_image_source(url: str) -> Optional[ImageSource]:
    cache_id = _url_id(url)
    path = CACHE_DIR / f"image_{cache_id}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    src = ImageSource(
        origin=data["origin"],
        image_path=Path(data["image_path"]),
        source_url=data["source_url"],
        title=data["title"],
        context_comments=data["context_comments"],
        subreddit=data["subreddit"],
    )
    logger.info(f"[ImageIngestion] Cache carregado: {path}")
    return src


# ── Módulo principal ─────────────────────────────────────────────────────────

class ImageIngestionModule:

    def run_reddit(self, ctx: PipelineContext) -> ImageSource:
        """
        Busca o post mais viral com imagem no subreddit configurado.
        Usa a API JSON pública do Reddit (sem autenticação).
        """
        cfg = ctx.config.get("image_ingestion", {})
        subreddit  = cfg.get("subreddit", "interestingasfuck")
        listing    = cfg.get("listing", "hot")       # hot | top | rising
        time_filter = cfg.get("time_filter", "day")  # hour|day|week|month|year|all (só p/ top)
        max_comments = cfg.get("max_comments", 5)
        min_score    = cfg.get("min_score", 1000)

        logger.info(f"[ImageIngestion] Reddit — r/{subreddit} [{listing}]")
        post = self._find_reddit_post(subreddit, listing, time_filter, min_score)
        image_path = self._download_image(post["url"], post["id"])
        comments   = self._fetch_reddit_comments(post["permalink"], max_comments)

        src = ImageSource(
            origin="reddit",
            image_path=image_path,
            url=REDDIT_BASE + post["permalink"],
            title=post.get("title", ""),
            context_comments=comments,
            subreddit=subreddit,
        )
        save_image_source(src)
        return src

    def run_manual(self, ctx: PipelineContext, image_url: str) -> ImageSource:
        """
        Recebe uma URL de imagem diretamente e a baixa.
        Sem comentários de contexto — o LLM vai depender só da visão.
        """
        logger.info(f"[ImageIngestion] Manual — {image_url}")
        uid = _url_id(image_url)
        image_path = self._download_image(image_url, uid)

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

    # ── Internos ─────────────────────────────────────────────────────────────

    def _fetch_json(self, url: str) -> dict:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())

    def _find_reddit_post(
        self, subreddit: str, listing: str, time_filter: str, min_score: int
    ) -> dict:
        """
        Percorre os posts do listing até achar um com imagem direta
        (jpg, png, webp) e score acima do mínimo.
        """
        IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")
        IMGUR_RE = re.compile(r"https?://(?:i\.)?imgur\.com/(\w+)(?:\.\w+)?$")

        url = f"{REDDIT_BASE}/r/{subreddit}/{listing}.json?limit=50"
        if listing == "top":
            url += f"&t={time_filter}"

        data = self._fetch_json(url)
        posts = data["data"]["children"]

        for item in posts:
            p = item["data"]
            if p.get("score", 0) < min_score:
                continue
            if p.get("is_video") or p.get("stickied"):
                continue

            post_url: str = p.get("url", "")

            # Imagem direta
            if any(post_url.lower().endswith(ext) for ext in IMAGE_EXTENSIONS):
                logger.info(f"[ImageIngestion] Post encontrado: {p['title'][:60]} (score: {p['score']})")
                return p

            # Imgur sem extensão → adiciona .jpg
            m = IMGUR_RE.match(post_url)
            if m:
                p["url"] = f"https://i.imgur.com/{m.group(1)}.jpg"
                logger.info(f"[ImageIngestion] Post Imgur: {p['title'][:60]}")
                return p

            # Reddit gallery — pega a primeira imagem
            if "gallery_data" in p and p.get("media_metadata"):
                first_id = list(p["media_metadata"].keys())[0]
                meta = p["media_metadata"][first_id]
                if meta.get("status") == "valid" and "s" in meta:
                    img_url = meta["s"].get("u", "").replace("&amp;", "&")
                    if img_url:
                        p["url"] = img_url
                        logger.info(f"[ImageIngestion] Gallery post: {p['title'][:60]}")
                        return p

        raise RuntimeError(
            f"Nenhum post com imagem encontrado em r/{subreddit} "
            f"com score >= {min_score}. Tente diminuir min_score ou mudar o subreddit."
        )

    def _download_image(self, url: str, uid: str) -> Path:
        IMAGE_DIR.mkdir(parents=True, exist_ok=True)

        # Determina extensão a partir da URL
        clean_url = url.split("?")[0]
        ext = Path(clean_url).suffix.lower()
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
        """Busca os top comentários do post pelo permalink."""
        url = f"{REDDIT_BASE}{permalink}.json?limit={max_n}&sort=top"
        try:
            data = self._fetch_json(url)
            # data[1] é o listing de comentários
            comments_data = data[1]["data"]["children"]
            comments = []
            for c in comments_data:
                body = c["data"].get("body", "").strip()
                if body and body != "[deleted]" and body != "[removed]":
                    comments.append(body)
                if len(comments) >= max_n:
                    break
            return comments
        except Exception as e:
            logger.warning(f"[ImageIngestion] Não foi possível buscar comentários: {e}")
            return []