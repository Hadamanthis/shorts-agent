"""
image_ingestion/image_ingestion_module.py — Obtém imagens para o ComentarioImagem.
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
HEADERS     = {"User-Agent": "shorts-agent/1.0 (content creator bot)"}


def _url_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:12]


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
        cfg          = ctx.config.get("image_ingestion", {})
        subreddit    = cfg.get("subreddit", "interestingasfuck")
        listing      = cfg.get("listing", "hot")
        time_filter  = cfg.get("time_filter", "day")
        max_comments = cfg.get("max_comments", 5)
        min_score    = cfg.get("min_score", 1000)

        logger.info(f"[ImageIngestion] Reddit — r/{subreddit} [{listing}]")
        post       = self._find_reddit_post(subreddit, listing, time_filter, min_score)
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

    # ── Internos ─────────────────────────────────────────────────────────────

    def _fetch_json(self, url: str) -> dict:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())

    def _find_reddit_post(self, subreddit, listing, time_filter, min_score) -> dict:
        IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")
        IMGUR_RE = re.compile(r"https?://(?:i\.)?imgur\.com/(\w+)(?:\.\w+)?$")

        url = f"{REDDIT_BASE}/r/{subreddit}/{listing}.json?limit=50"
        if listing == "top":
            url += f"&t={time_filter}"

        posts = self._fetch_json(url)["data"]["children"]

        for item in posts:
            p = item["data"]
            if p.get("score", 0) < min_score or p.get("is_video") or p.get("stickied"):
                continue

            post_url: str = p.get("url", "")

            if any(post_url.lower().endswith(ext) for ext in IMAGE_EXTENSIONS):
                logger.info(f"[ImageIngestion] Post: {p['title'][:60]} (score: {p['score']})")
                return p

            m = IMGUR_RE.match(post_url)
            if m:
                p["url"] = f"https://i.imgur.com/{m.group(1)}.jpg"
                logger.info(f"[ImageIngestion] Post Imgur: {p['title'][:60]}")
                return p

            if "gallery_data" in p and p.get("media_metadata"):
                first_id = list(p["media_metadata"].keys())[0]
                meta = p["media_metadata"][first_id]
                if meta.get("status") == "valid" and "s" in meta:
                    img_url = meta["s"].get("u", "").replace("&amp;", "&")
                    if img_url:
                        p["url"] = img_url
                        logger.info(f"[ImageIngestion] Gallery: {p['title'][:60]}")
                        return p

        raise RuntimeError(
            f"Nenhum post com imagem em r/{subreddit} com score >= {min_score}. "
            f"Tente diminuir min_score ou mudar o subreddit."
        )

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