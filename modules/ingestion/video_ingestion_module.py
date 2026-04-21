"""
video_ingestion/video_ingestion_module.py — Obtém vídeos do Reddit para o ComentarioVideo.

Estrutura idêntica ao image_ingestion_module, mas busca posts com vídeo
(v.redd.it, gifv, etc.) e usa yt-dlp para baixar.

Modos:
  - run_reddit()            : pega o top-1 automaticamente
  - run_reddit_interactive(): TUI para escolher entre os top-n
  - run_manual()            : URL direta de vídeo

Devolve um VideoSource preenchido (mesmo contrato do pipeline YouTube).
"""
import hashlib
import json
import logging
import re
import sys
import subprocess
import urllib.request
from pathlib import Path
from typing import Optional

from modules.models import VideoSource, PipelineContext

logger = logging.getLogger(__name__)

VIDEO_DIR  = Path("output") / "clips"
CACHE_DIR  = Path("output") / "cache"
REDDIT_BASE = "https://www.reddit.com"
HEADERS     = {"User-Agent": "shorts-agent/1.0 (content creator bot)"}


def _url_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:12]


def _ansi_link(url: str, text: str) -> str:
    return f"\033]8;;{url}\033\\{text}\033]8;;\033\\"


def save_video_source(src: VideoSource) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_id = _url_id(src.url)
    path = CACHE_DIR / f"reddit_video_{cache_id}.json"
    path.write_text(json.dumps({
        "url": src.url,
        "video_id": src.video_id,
        "title": src.title,
        "description": src.description,
        "channel_name": src.channel_name,
        "duration_seconds": src.duration_seconds,
        "clip_path": str(src.clip_path),
        "comments": src.comments,
        "thumbnail_url": src.thumbnail_url,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"[VideoIngestion] Cache salvo: {path}")
    return path


def load_video_source(url: str) -> Optional[VideoSource]:
    cache_id = _url_id(url)
    path = CACHE_DIR / f"reddit_video_{cache_id}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    logger.info(f"[VideoIngestion] Cache carregado: {path}")
    return VideoSource(
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


class VideoIngestionModule:

    def run_reddit(self, ctx: PipelineContext) -> VideoSource:
        """Modo automático — pega o top-1 sem interação."""
        cfg = ctx.config.get("video_ingestion", {})
        posts = self._find_reddit_posts(cfg, limit=1)
        return self._process_post(posts[0], ctx)

    def run_reddit_interactive(self, ctx: PipelineContext) -> VideoSource:
        """Modo interativo — TUI para escolher entre os top-n posts."""
        cfg   = ctx.config.get("video_ingestion", {})
        top_n = cfg.get("top_n_posts", 5)
        posts = self._find_reddit_posts(cfg, limit=top_n)
        post  = self._prompt_post_selection(posts, cfg.get("subreddit", "videos"))
        return self._process_post(post, ctx)

    def run_manual(self, ctx: PipelineContext, video_url: str) -> VideoSource:
        """Baixa um vídeo a partir de uma URL direta."""
        logger.info(f"[VideoIngestion] Manual — {video_url}")
        uid       = _url_id(video_url)
        clip_path = self._download_video(video_url, uid, ctx)
        comments  = []

        src = VideoSource(
            url=video_url,
            video_id=uid,
            title="",
            description="",
            channel_name="",
            duration_seconds=0,
            clip_path=clip_path,
            comments=comments,
        )
        save_video_source(src)
        return src

    # ── Internos ─────────────────────────────────────────────────────────────

    def _process_post(self, post: dict, ctx: PipelineContext) -> VideoSource:
        cfg          = ctx.config.get("video_ingestion", {})
        max_comments = cfg.get("max_comments", 5)

        post_url  = post["url"]
        post_id   = post["id"]
        permalink = post["permalink"]

        logger.info(f"[VideoIngestion] Baixando: {post.get('title', '')[:60]}")
        clip_path = self._download_video(post_url, post_id, ctx)
        comments  = self._fetch_reddit_comments(permalink, max_comments)

        src = VideoSource(
            url=REDDIT_BASE + permalink,
            video_id=post_id,
            title=post.get("title", ""),
            description="",
            channel_name=post.get("subreddit_name_prefixed", ""),
            duration_seconds=int(post.get("media", {}).get("reddit_video", {}).get("duration", 0)),
            clip_path=clip_path,
            comments=comments,
            thumbnail_url=post.get("thumbnail", ""),
        )
        save_video_source(src)
        return src

    def _find_reddit_posts(self, cfg: dict, limit: int) -> list[dict]:
        subreddit    = cfg.get("subreddit", "nextfuckinglevel")
        listing      = cfg.get("listing", "hot")
        time_filter  = cfg.get("time_filter", "day")
        min_score    = cfg.get("min_score", 500)
        max_duration = cfg.get("max_post_duration", 180)

        VIDEO_DOMAINS = ("v.redd.it", "youtube.com", "youtu.be", "imgur.com", "gfycat.com", "streamable.com")

        # No modo interativo limit=top_n, mas buscamos sempre 50 para ter material de sobra
        fetch_limit = cfg.get("fetch_limit", 50)
        url = f"{REDDIT_BASE}/r/{subreddit}/{listing}.json?limit={fetch_limit}"
        if listing == "top":
            url += f"&t={time_filter}"

        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = json.loads(resp.read().decode())

        found: list[dict] = []
        for item in raw["data"]["children"]:
            p = item["data"]
            if p.get("score", 0) < min_score or p.get("stickied"):
                continue

            post_url: str = p.get("url", "")
            is_video = p.get("is_video", False)
            is_video_domain = any(d in post_url for d in VIDEO_DOMAINS)

            if not (is_video or is_video_domain):
                continue

            if is_video and "media" in p and p["media"] and "reddit_video" in p["media"]:
                duration = int(p["media"]["reddit_video"].get("duration", 0))
                if duration > max_duration:
                    continue
                p["url"] = p["media"]["reddit_video"]["fallback_url"]
                p["_duration"] = duration
            
            found.append(p)

        # Modo automático: retorna só o top-1
        if limit == 1:
            if not found:
                raise RuntimeError(
                    f"Nenhum post de vídeo em r/{subreddit} com score >= {min_score} "
                    f"e duração <= {max_duration}s."
                )
            return found[:1]

        # Modo interativo: retorna tudo que passou nos filtros
        if not found:
            raise RuntimeError(
                f"Nenhum post de vídeo em r/{subreddit} com score >= {min_score} "
                f"e duração <= {max_duration}s."
            )
        return found

    def _download_video(self, url: str, uid: str, ctx: PipelineContext) -> Path:
        VIDEO_DIR.mkdir(parents=True, exist_ok=True)
        video_cfg   = ctx.config.get("video_ingestion", {})
        max_dur     = video_cfg.get("max_clip_duration", 30)
        start_offset = video_cfg.get("clip_start_offset", 0)

        dest = VIDEO_DIR / f"reddit_{uid}_clip.mp4"
        if dest.exists():
            logger.info(f"[VideoIngestion] Clip já existe: {dest}")
            return dest

        raw = VIDEO_DIR / f"reddit_{uid}_raw.mp4"

        # yt-dlp consegue baixar v.redd.it, YouTube, Streamable, etc.
        dl_cmd = [
            "yt-dlp",
            "--format", "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best",
            "--merge-output-format", "mp4",
            "--output", str(raw),
            "--no-playlist",
            "--quiet",
            url,
        ]
        logger.info(f"[VideoIngestion] Baixando vídeo com yt-dlp...")
        result = subprocess.run(dl_cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise RuntimeError(f"yt-dlp falhou:\n{result.stderr}")

        # Recorta com FFmpeg
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-ss", str(start_offset),
            "-i", str(raw),
            "-t", str(max_dur),
            "-c:v", "libx264",
            "-c:a", "aac",
            "-vsync", "cfr",        # <-- força constant frame rate
            "-r", "30",             # <-- fixa em 30fps
            "-movflags", "+faststart",
            str(dest),
        ]
        logger.info(f"[VideoIngestion] Recortando {start_offset}s → {start_offset + max_dur}s")
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg falhou:\n{result.stderr}")

        raw.unlink(missing_ok=True)
        return dest

    def _fetch_reddit_comments(self, permalink: str, max_n: int) -> list[str]:
        url = f"{REDDIT_BASE}{permalink}.json?limit={max_n}&sort=top"
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
            comments = []
            for c in data[1]["data"]["children"]:
                body = c["data"].get("body", "").strip()
                if body and body not in ("[deleted]", "[removed]"):
                    comments.append(body)
                if len(comments) >= max_n:
                    break
            return comments
        except Exception as e:
            logger.warning(f"[VideoIngestion] Comentários indisponíveis: {e}")
            return []

    # ── TUI ──────────────────────────────────────────────────────────────────

    def _prompt_post_selection(self, posts: list[dict], subreddit: str) -> dict:
        try:
            import questionary
            from questionary import Style

            custom_style = Style([
                ("qmark", "fg:#00b4d8 bold"), ("question", "fg:#ffffff bold"),
                ("highlighted", "fg:#00b4d8 bold"), ("selected", "fg:#90e0ef"),
                ("pointer", "fg:#00b4d8 bold"), ("answer", "fg:#90e0ef bold"),
            ])

            PAGE_SIZE = 5
            page = 0
            total_pages = max(1, (len(posts) + PAGE_SIZE - 1) // PAGE_SIZE)

            while True:
                start = page * PAGE_SIZE
                page_posts = posts[start: start + PAGE_SIZE]

                choices = []
                for i, p in enumerate(page_posts):
                    global_i = start + i
                    title = p.get("title", "")
                    title_short = title if len(title) <= 72 else title[:69] + "…"
                    score = p.get("score", 0)
                    n_comms = p.get("num_comments", 0)
                    duration = p.get("_duration", 0)
                    dur_str = f"⏱ {duration}s" if duration else ""
                    label = (
                        f"[{global_i+1}] {title_short}\n"
                        f"     ⬆ {score:,}  💬 {n_comms:,}  {dur_str}"
                    )
                    choices.append(questionary.Choice(title=label, value=global_i))

                if page > 0:
                    choices.append(questionary.Choice(title="◀ Página anterior", value="prev"))
                if page < total_pages - 1:
                    choices.append(questionary.Choice(title=f"▶ Próxima página ({page+2}/{total_pages})", value="next"))
                choices.append(questionary.Choice(title="✖ Cancelar", value="cancel"))

                print(f"\n🎬 r/{subreddit} — {len(posts)} posts disponíveis, página {page+1}/{total_pages}:\n")
                selected = questionary.select(
                    "Escolha com ↑↓ e Enter:",
                    choices=choices,
                    style=custom_style,
                ).ask()

                if selected is None or selected == "cancel":
                    print("\nOperação cancelada.")
                    sys.exit(0)
                elif selected == "prev":
                    page -= 1
                elif selected == "next":
                    page += 1
                else:
                    return posts[selected]

        except ImportError:
            return self._prompt_fallback(posts, subreddit)

    def _prompt_fallback(self, posts: list[dict], subreddit: str) -> dict:
        PAGE_SIZE = 5
        page = 0
        total_pages = max(1, (len(posts) + PAGE_SIZE - 1) // PAGE_SIZE)

        while True:
            start = page * PAGE_SIZE
            page_posts = posts[start: start + PAGE_SIZE]

            print(f"\n🎬 r/{subreddit} — página {page+1}/{total_pages}:\n")
            for i, p in enumerate(page_posts):
                global_i = start + i
                duration = p.get("_duration", 0)
                dur_str = f"⏱ {duration}s  " if duration else ""
                print(f"  [{global_i+1}] {p.get('title', '')}")
                print(f"       ⬆ {p.get('score',0):,}  💬 {p.get('num_comments',0):,}  {dur_str}\n")

            nav = []
            if page > 0:
                nav.append("'p' anterior")
            if page < total_pages - 1:
                nav.append("'n' próxima")
            nav.append(f"1-{len(posts)} para escolher")

            try:
                raw = input(f"  [{' | '.join(nav)}]: ").strip().lower()
                if raw == "n" and page < total_pages - 1:
                    page += 1
                elif raw == "p" and page > 0:
                    page -= 1
                else:
                    idx = int(raw) - 1
                    if 0 <= idx < len(posts):
                        return posts[idx]
                    print(f"  Digite um número entre 1 e {len(posts)}.")
            except (ValueError, KeyboardInterrupt):
                print("\nOperação cancelada.")
                sys.exit(0)