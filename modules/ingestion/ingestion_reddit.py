"""
ingestion/ingestion_reddit.py — Ingestion unificado para Reddit (imagem e vídeo).

Busca posts de qualquer tipo (imagem ou vídeo) em um subreddit e exibe
uma TUI paginada para o usuário escolher. O tipo do post escolhido determina
o que é retornado: ImageSource ou VideoSource.

Modos públicos:
  - run_interactive(ctx)         : TUI paginada — padrão para comentario-reddit
  - run_manual(ctx, url, mode)   : URL direta, pula a listagem
"""
import hashlib
import json
import logging
import re
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Literal, Optional, Union

from modules.models import ImageSource, VideoSource, PipelineContext

logger = logging.getLogger(__name__)

IMAGE_DIR   = Path("output") / "images"
VIDEO_DIR   = Path("output") / "clips"
CACHE_DIR   = Path("output") / "cache"
REDDIT_BASE = "https://www.reddit.com"
HEADERS     = {"User-Agent": "shorts-agent/1.0 (content creator bot)"}

Mode = Literal["image", "video"]

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")
VIDEO_DOMAINS    = ("v.redd.it", "youtube.com", "youtu.be", "gfycat.com", "streamable.com")
IMGUR_RE         = re.compile(r"https?://(?:i\.)?imgur\.com/(\w+)(?:\.\w+)?$")


# ── Cache helpers ─────────────────────────────────────────────────────────────

def _url_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:12]


def save_image_source(src: ImageSource) -> None:
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
    logger.info(f"[Ingestion] Cache salvo: {path}")


def load_image_source(url: str) -> Optional[ImageSource]:
    path = CACHE_DIR / f"image_{_url_id(url)}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    logger.info(f"[Ingestion] Cache carregado: {path}")
    return ImageSource(
        origin=data["origin"],
        image_path=Path(data["image_path"]),
        source_url=data["source_url"],
        title=data["title"],
        context_comments=data["context_comments"],
        subreddit=data["subreddit"],
    )


def save_video_source(src: VideoSource) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"reddit_video_{_url_id(src.url)}.json"
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
    logger.info(f"[Ingestion] Cache salvo: {path}")


def load_video_source(url: str) -> Optional[VideoSource]:
    path = CACHE_DIR / f"reddit_video_{_url_id(url)}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    logger.info(f"[Ingestion] Cache carregado: {path}")
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


# ── Módulo principal ──────────────────────────────────────────────────────────

class RedditIngestionModule:

    def fetch_posts_data(self, cfg: dict) -> list[dict]:
        """
        Retorna lista de posts prontos para exibição em GUI/API.
        Não faz download de mídia — apenas metadata.
        Cada item tem: index, title, score, num_comments, post_type, duration, thumbnail_url, url
        """
        posts = self._find_posts(cfg)
        result = []
        for i, p in enumerate(posts):
            result.append({
                "index": i,
                "title": p.get("title", ""),
                "score": p.get("score", 0),
                "num_comments": p.get("num_comments", 0),
                "post_type": p.get("_post_type", "image"),
                "duration": p.get("_duration", 0),
                "thumbnail_url": self._best_preview_url(p),
                "url": p.get("url", ""),
                "permalink": p.get("permalink", ""),
                "subreddit": p.get("subreddit_name_prefixed", ""),
            })
        return result

    def _best_preview_url(self, p: dict) -> str:
        """
        Retorna a melhor URL de preview disponível para exibição na GUI.
        Prioridade: preview.images resolutions (Reddit CDN) -> thumbnail direto.
        URLs do Reddit CDN têm &amp; que precisa ser decodificado.
        """
        try:
            previews = p.get("preview", {}).get("images", [])
            if previews:
                resolutions = previews[0].get("resolutions", [])
                # Pega resolução ~320px de largura (terceira ou a maior disponível)
                candidates = [r for r in resolutions if r.get("width", 0) >= 200]
                chosen = candidates[0] if candidates else (resolutions[-1] if resolutions else None)
                if chosen:
                    return chosen["url"].replace("&amp;", "&")
                # Fallback: source
                source = previews[0].get("source", {})
                if source.get("url"):
                    return source["url"].replace("&amp;", "&")
        except Exception:
            pass
        # Último recurso: thumbnail (pode ser bloqueada por CORS)
        thumb = p.get("thumbnail", "")
        if thumb and thumb not in ("default", "self", "nsfw", ""):
            return thumb
        return ""

    def run_from_index(self, ctx: PipelineContext, posts_data: list[dict], index: int) -> Union[ImageSource, VideoSource]:
        """
        Processa um post já selecionado pela GUI (sem TUI).
        posts_data deve ser a lista retornada por fetch_posts_data().
        """
        cfg = ctx.config.get("comentario-reddit", {})
        # Re-fetch para ter os dados completos do post
        all_posts = self._find_posts(cfg)
        if index < 0 or index >= len(all_posts):
            raise ValueError(f"Índice {index} fora do intervalo (0-{len(all_posts)-1})")
        post = all_posts[index]
        return self._process_post(post, ctx, cfg)

    def run_interactive(self, ctx: PipelineContext) -> Union[ImageSource, VideoSource]:
        """TUI paginada com todos os posts (imagem + vídeo) do subreddit."""
        cfg   = ctx.config.get("comentario-reddit", {})
        posts = self._find_posts(cfg)
        post  = self._prompt_post_selection(posts, cfg.get("subreddit", ""))
        return self._process_post(post, ctx, cfg)

    def run_manual(self, ctx: PipelineContext, url: str, mode: Mode) -> Union[ImageSource, VideoSource]:
        """URL direta fornecida pelo usuário, pula a listagem."""
        logger.info(f"[Ingestion] Manual {mode} — {url}")
        cfg = ctx.config.get("comentario-reddit", {})
        uid = _url_id(url)

        if mode == "image":
            image_path = self._download_image(url, uid)
            src = ImageSource(
                origin="manual",
                image_path=image_path,
                source_url=url,
                title="",
                context_comments=[],
                subreddit="",
            )
            save_image_source(src)
            return src
        else:
            clip_path = self._download_video(url, uid, cfg)
            src = VideoSource(
                url=url,
                video_id=uid,
                title="",
                description="",
                channel_name="",
                duration_seconds=0,
                clip_path=clip_path,
                comments=[],
                thumbnail_url="",
            )
            save_video_source(src)
            return src

    # ── Post discovery ────────────────────────────────────────────────────────

    def _find_posts(self, cfg: dict) -> list[dict]:
        """
        Retorna todos os posts válidos (imagem ou vídeo) do subreddit,
        respeitando min_score, max_post_duration e fetch_limit.

        Cada post recebe:
          _post_type : "image" | "video"
          _duration  : duração em segundos (só vídeos nativos do Reddit)
        """
        subreddit    = cfg.get("subreddit", "")
        listing      = cfg.get("listing", "hot")
        time_filter  = cfg.get("time_filter", "day")
        min_score    = cfg.get("min_score", 500)
        fetch_limit  = cfg.get("fetch_limit", 50)
        max_duration = cfg.get("max_post_duration", 180)

        if not subreddit:
            raise ValueError("Subreddit não configurado. Use --subreddit ou defina em config.yaml.")

        url = f"{REDDIT_BASE}/r/{subreddit}/{listing}.json?limit={fetch_limit}"
        if listing == "top":
            url += f"&t={time_filter}"

        logger.info(f"[Ingestion] Buscando posts em r/{subreddit} [{listing}]...")
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = json.loads(resp.read().decode())

        found: list[dict] = []
        for item in raw["data"]["children"]:
            p = item["data"]
            if p.get("score", 0) < min_score or p.get("stickied"):
                continue

            post_url: str = p.get("url", "")

            # Tenta classificar como vídeo primeiro
            is_native_video = p.get("is_video", False)
            is_video_domain = any(d in post_url for d in VIDEO_DOMAINS)

            if is_native_video or is_video_domain:
                if is_native_video and "media" in p and p["media"] and "reddit_video" in p["media"]:
                    duration = int(p["media"]["reddit_video"].get("duration", 0))
                    if duration > max_duration:
                        continue
                    p["url"]       = p["media"]["reddit_video"]["fallback_url"]
                    p["_duration"] = duration
                p["_post_type"] = "video"
                found.append(p)
                continue

            # Tenta classificar como imagem
            img_url = self._extract_image_url(p, post_url)
            if img_url:
                p["url"]        = img_url
                p["_post_type"] = "image"
                found.append(p)

        if not found:
            raise RuntimeError(
                f"Nenhum post encontrado em r/{subreddit} com score >= {min_score}. "
                f"Tente diminuir min_score ou mudar o subreddit."
            )

        logger.info(f"[Ingestion] {len(found)} posts encontrados.")
        return found

    def _extract_image_url(self, p: dict, post_url: str) -> Optional[str]:
        if any(post_url.lower().endswith(ext) for ext in IMAGE_EXTENSIONS):
            return post_url
        m = IMGUR_RE.match(post_url)
        if m:
            return f"https://i.imgur.com/{m.group(1)}.jpg"
        if "gallery_data" in p and p.get("media_metadata"):
            first_id = list(p["media_metadata"].keys())[0]
            meta = p["media_metadata"][first_id]
            if meta.get("status") == "valid" and "s" in meta:
                img_url = meta["s"].get("u", "").replace("&amp;", "&")
                if img_url:
                    return img_url
        return None

    # ── Post processing ───────────────────────────────────────────────────────

    def _process_post(
        self, post: dict, ctx: PipelineContext, cfg: dict
    ) -> Union[ImageSource, VideoSource]:
        max_comments = cfg.get("max_comments", 5)
        subreddit    = cfg.get("subreddit", "")
        permalink    = post["permalink"]
        post_type    = post.get("_post_type", "image")

        logger.info(f"[Ingestion] Post selecionado ({post_type}): {post.get('title', '')[:60]}")
        comments = self._fetch_comments(permalink, max_comments)

        if post_type == "image":
            image_path = self._download_image(post["url"], post["id"])
            src = ImageSource(
                origin="reddit",
                image_path=image_path,
                source_url=REDDIT_BASE + permalink,
                title=post.get("title", ""),
                context_comments=comments,
                subreddit=subreddit,
            )
            save_image_source(src)
            return src
        else:
            clip_path = self._download_video(post["url"], post["id"], cfg)
            src = VideoSource(
                url=REDDIT_BASE + permalink,
                video_id=post["id"],
                title=post.get("title", ""),
                description="",
                channel_name=post.get("subreddit_name_prefixed", ""),
                duration_seconds=int(post.get("_duration", 0)),
                clip_path=clip_path,
                comments=comments,
                thumbnail_url=post.get("thumbnail", ""),
            )
            save_video_source(src)
            return src

    # ── Downloads ─────────────────────────────────────────────────────────────

    def _download_image(self, url: str, uid: str) -> Path:
        IMAGE_DIR.mkdir(parents=True, exist_ok=True)
        ext = Path(url.split("?")[0]).suffix.lower()
        if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
            ext = ".jpg"
        dest = IMAGE_DIR / f"img_{uid}{ext}"
        if dest.exists():
            logger.info(f"[Ingestion] Imagem já existe, pulando download: {dest}")
            return dest
        logger.info(f"[Ingestion] Baixando imagem: {url}")
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=30) as resp:
            dest.write_bytes(resp.read())
        logger.info(f"[Ingestion] Imagem salva: {dest}")
        return dest

    def _download_video(self, url: str, uid: str, cfg: dict) -> Path:
        VIDEO_DIR.mkdir(parents=True, exist_ok=True)
        max_dur      = cfg.get("max_clip_duration", 30)
        start_offset = cfg.get("clip_start_offset", 0)

        dest = VIDEO_DIR / f"reddit_{uid}_clip.mp4"
        if dest.exists():
            logger.info(f"[Ingestion] Clip já existe: {dest}")
            return dest

        raw = VIDEO_DIR / f"reddit_{uid}_raw.mp4"

        dl_cmd = [
            "yt-dlp",
            "--format", "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best",
            "--merge-output-format", "mp4",
            "--output", str(raw),
            "--no-playlist",
            "--quiet",
            url,
        ]
        logger.info(f"[Ingestion] Baixando vídeo com yt-dlp...")
        result = subprocess.run(dl_cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise RuntimeError(f"yt-dlp falhou:\n{result.stderr}")

        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-ss", str(start_offset),
            "-i", str(raw),
            "-t", str(max_dur),
            "-c:v", "libx264",
            "-preset", "fast",        # <-- adiciona (era padrão implícito, agora explícito)
            "-crf", "18",             # <-- adiciona (qualidade boa para o clip final)
            "-g", "30",               # <-- adiciona: keyframe a cada 1s (30fps)
            "-keyint_min", "30",      # <-- adiciona: força keyframe mínimo
            "-sc_threshold", "0",     # <-- adiciona: desativa keyframe por cena
            "-c:a", "aac",
            "-vsync", "cfr",
            "-r", "30",
            "-movflags", "+faststart",
            str(dest),
        ]
        logger.info(f"[Ingestion] Recortando {start_offset}s -> {start_offset + max_dur}s")
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg falhou:\n{result.stderr}")

        raw.unlink(missing_ok=True)
        return dest

    # ── Comments ──────────────────────────────────────────────────────────────

    def _fetch_comments(self, permalink: str, max_n: int) -> list[str]:
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
            logger.warning(f"[Ingestion] Comentários indisponíveis: {e}")
            return []

    # ── TUI ───────────────────────────────────────────────────────────────────

    def _prompt_post_selection(self, posts: list[dict], subreddit: str) -> dict:
        try:
            import questionary
            from questionary import Style

            custom_style = Style([
                ("qmark",       "fg:#00b4d8 bold"),
                ("question",    "fg:#ffffff bold"),
                ("highlighted", "fg:#00b4d8 bold"),
                ("selected",    "fg:#90e0ef"),
                ("pointer",     "fg:#00b4d8 bold"),
                ("answer",      "fg:#90e0ef bold"),
            ])

            PAGE_SIZE   = 5
            page        = 0
            total_pages = max(1, (len(posts) + PAGE_SIZE - 1) // PAGE_SIZE)

            while True:
                start      = page * PAGE_SIZE
                page_posts = posts[start: start + PAGE_SIZE]

                choices = []
                for i, p in enumerate(page_posts):
                    global_i    = start + i
                    title       = p.get("title", "")
                    title_short = title if len(title) <= 68 else title[:65] + "…"
                    score       = p.get("score", 0)
                    n_comms     = p.get("num_comments", 0)
                    post_type   = p.get("_post_type", "image")
                    duration    = p.get("_duration", 0)
                    type_icon   = "🎬" if post_type == "video" else "🖼 "
                    dur_str     = f"  ⏱ {duration}s" if duration else ""
                    label = (
                        f"{type_icon} [{global_i+1}] {title_short}\n"
                        f"      ⬆ {score:,}  💬 {n_comms:,}{dur_str}"
                    )
                    choices.append(questionary.Choice(title=label, value=global_i))

                if page > 0:
                    choices.append(questionary.Choice(title="◀ Página anterior", value="prev"))
                if page < total_pages - 1:
                    choices.append(questionary.Choice(
                        title=f"▶ Próxima página ({page+2}/{total_pages})", value="next"))
                choices.append(questionary.Choice(title="✖ Cancelar", value="cancel"))

                print(f"\n📋 r/{subreddit} — {len(posts)} posts, página {page+1}/{total_pages}:\n")
                selected = questionary.select(
                    "Escolha com ↑↓ e Enter:",
                    choices=choices,
                    style=custom_style,
                    use_shortcuts=False,
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
        PAGE_SIZE   = 5
        page        = 0
        total_pages = max(1, (len(posts) + PAGE_SIZE - 1) // PAGE_SIZE)

        while True:
            start      = page * PAGE_SIZE
            page_posts = posts[start: start + PAGE_SIZE]

            print(f"\n📋 r/{subreddit} — página {page+1}/{total_pages}:\n")
            for i, p in enumerate(page_posts):
                global_i  = start + i
                post_type = p.get("_post_type", "image")
                duration  = p.get("_duration", 0)
                type_icon = "🎬" if post_type == "video" else "🖼 "
                dur_str   = f"  ⏱ {duration}s" if duration else ""
                print(f"  {type_icon} [{global_i+1}] {p.get('title', '')}")
                print(f"       ⬆ {p.get('score', 0):,}  💬 {p.get('num_comments', 0):,}{dur_str}\n")

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