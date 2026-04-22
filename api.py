"""
api.py — Servidor FastAPI que expõe o pipeline existente via HTTP.

Coloque este arquivo na raiz do projeto shorts-creator-agent/,
ao lado de main.py.

Instale as dependências:
    pip install fastapi uvicorn pyyaml

Rode com:
    uvicorn api:app --reload --port 8000
"""

import asyncio
import json
import logging
import platform
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Shorts Creator API", version="1.0.0")

# Permite requisições do Remotion Studio (porta 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger("api")

# Caminhos relativos à raiz do projeto (onde api.py está)
ROOT       = Path(__file__).parent
CONFIG_PATH = ROOT / "config.yaml"
SHORTS_DIR  = ROOT / "output" / "shorts"

# Jobs em memória (reinicia quando o servidor reinicia)
jobs: dict[str, dict] = {}


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def save_config(config: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, sort_keys=False)


# ── Schemas ───────────────────────────────────────────────────────────────────

class RunRequest(BaseModel):
    template: str = "comentario-reddit"
    profile: str = "Synthvator"
    subreddit: Optional[str] = None
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    url: Optional[str] = None
    comment_tone: Optional[str] = None
    curiosity_max_chars: Optional[int] = None
    comment_max_chars: Optional[int] = None
    post_index: Optional[int] = None  # índice do post já selecionado na GUI

class PatchConfigRequest(BaseModel):
    content: Optional[dict] = None
    pipeline: Optional[dict] = None
    reddit: Optional[dict] = None

class CreateProfileRequest(BaseModel):
    name: str
    language: str = "pt-BR"
    niche: str
    account_name: str
    avatar_path: str = "assets/profiles/synthvator.png"
    background_video: str = "assets/backgrounds/bg_default.mp4"
    music_path: str = "assets/music/bg_music.mp3"
    cta_video_path: str = ""

class OpenFolderRequest(BaseModel):
    path: str

class DYKGenerateRequest(BaseModel):
    topic: str
    profile: str = "Synthvator"
    num_facts: int = 5

class DYKFactInput(BaseModel):
    text: str
    image_url: str
    duration_seconds: Optional[float] = None  # override por card; None = usa config padrão

class DYKRenderRequest(BaseModel):
    facts: list[DYKFactInput]
    profile: str = "Synthvator"
    music_name: Optional[str] = None
    topic: Optional[str] = None  # usado para gerar metadata SEO após render

class ImageSearchRequest(BaseModel):
    query: str
    per_source: int = 3


# ── Config endpoints ──────────────────────────────────────────────────────────

@app.get("/config")
def get_config():
    return load_config()

@app.patch("/config")
def patch_config(req: PatchConfigRequest):
    config = load_config()
    if req.content:
        config.setdefault("content", {}).update(req.content)
    if req.pipeline:
        config.setdefault("pipeline", {}).update(req.pipeline)
    if req.reddit:
        config.setdefault("comentario-reddit", {}).update(req.reddit)
    save_config(config)
    return {"ok": True, "config": load_config()}

@app.get("/profiles")
def list_profiles():
    return load_config().get("profiles", {})

@app.post("/profiles")
def create_profile(req: CreateProfileRequest):
    config = load_config()
    config.setdefault("profiles", {})[req.name] = {
        "language": req.language,
        "niche": req.niche,
        "account_name": req.account_name,
        "avatar_path": req.avatar_path,
        "background_video": req.background_video,
        "music_path": req.music_path,
        "cta_video_path": req.cta_video_path,
    }
    save_config(config)
    return {"ok": True}

@app.delete("/profiles/{name}")
def delete_profile(name: str):
    config = load_config()
    if name not in config.get("profiles", {}):
        raise HTTPException(404, f"Perfil '{name}' não encontrado")
    del config["profiles"][name]
    save_config(config)
    return {"ok": True}


# ── Posts browser (Reddit) ────────────────────────────────────────────────────

@app.get("/posts")
def list_posts(subreddit: str, profile: str = "Synthvator"):
    """Retorna a lista de posts de um subreddit sem iniciar o pipeline."""
    import sys as _sys
    _sys.path.insert(0, str(ROOT))
    from modules.ingestion.ingestion_reddit import RedditIngestionModule

    config = load_config()
    config.setdefault("comentario-reddit", {})["subreddit"] = subreddit

    if profile not in config.get("profiles", {}):
        raise HTTPException(400, f"Perfil '{profile}' não encontrado")

    try:
        posts = RedditIngestionModule().fetch_posts_data(config["comentario-reddit"])
        return {"posts": posts, "subreddit": subreddit}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/image-proxy")
def image_proxy(url: str):
    """
    Proxy de imagens para contornar CORS ao exibir thumbnails do Reddit no browser.
    Uso: <img src="http://localhost:8000/image-proxy?url=https://preview.redd.it/...">
    """
    from urllib.parse import urlparse, unquote
    # O browser pode double-encode a URL — decodifica até estabilizar
    decoded = url
    for _ in range(3):
        next_dec = unquote(decoded)
        if next_dec == decoded:
            break
        decoded = next_dec
    # Substitui &amp; residual que vem do HTML do Reddit
    decoded = decoded.replace("&amp;", "&")

    ALLOWED_HOSTS = ("preview.redd.it", "external-preview.redd.it", "i.redd.it", "i.imgur.com")
    host = urlparse(decoded).netloc
    if not any(host.endswith(h) for h in ALLOWED_HOSTS):
        raise HTTPException(403, f"Host não permitido: {host}")
    try:
        req = urllib.request.Request(decoded, headers={"User-Agent": "shorts-agent/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
            content_type = resp.headers.get("Content-Type", "image/jpeg")
        return Response(content=data, media_type=content_type,
                        headers={"Cache-Control": "max-age=3600"})
    except Exception as e:
        raise HTTPException(502, f"Erro ao buscar imagem: {e}")


# ── Pipeline endpoints ────────────────────────────────────────────────────────

@app.post("/run")
async def run_pipeline(req: RunRequest):
    """Dispara main.py como subprocesso e retorna job_id para polling."""
    job_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    jobs[job_id] = {
        "status": "running",
        "log": [],
        "started_at": datetime.now().isoformat(),
    }

    cmd = [
        sys.executable, str(ROOT / "main.py"),
        "--template", req.template,
        "--profile",  req.profile,
    ]
    if req.subreddit:            cmd += ["--subreddit",           req.subreddit]
    if req.image_url:            cmd += ["--image-url",           req.image_url]
    if req.video_url:            cmd += ["--video-url",           req.video_url]
    if req.url:                  cmd += ["--url",                 req.url]
    if req.comment_tone:         cmd += ["--comment-tone",        req.comment_tone]
    if req.curiosity_max_chars:  cmd += ["--curiosity-max-chars", str(req.curiosity_max_chars)]
    if req.comment_max_chars:    cmd += ["--comment-max-chars",   str(req.comment_max_chars)]
    if req.post_index is not None: cmd += ["--post-index",        str(req.post_index)]

    async def _run():
        env = {**__import__('os').environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(ROOT),
            env=env,
        )
        async for raw in proc.stdout:
            line = raw.decode("utf-8", errors="replace").rstrip()
            jobs[job_id]["log"].append(line)
        await proc.wait()
        jobs[job_id]["status"] = "done" if proc.returncode == 0 else "error"
        jobs[job_id]["returncode"] = proc.returncode
        jobs[job_id]["finished_at"] = datetime.now().isoformat()

    asyncio.create_task(_run())
    return {"job_id": job_id}

@app.get("/run/{job_id}")
def job_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404, "Job não encontrado")
    return jobs[job_id]

@app.get("/jobs")
def list_jobs():
    """Lista jobs sem o log completo (só metadados)."""
    return [
        {k: v for k, v in job.items() if k != "log"} | {"job_id": jid}
        for jid, job in sorted(jobs.items(), reverse=True)
    ]


# ── Output endpoints ──────────────────────────────────────────────────────────

@app.get("/shorts")
def list_shorts():
    if not SHORTS_DIR.exists():
        return []
    files = sorted(SHORTS_DIR.glob("*.mp4"), key=lambda f: f.stat().st_mtime, reverse=True)
    return [
        {
            "name": f.name,
            "path": str(f),
            "size_mb": round(f.stat().st_size / 1_048_576, 2),
            "created_at": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
        }
        for f in files
    ]

@app.post("/open-folder")
def open_folder(req: OpenFolderRequest):
    """Abre o explorador de arquivos na pasta do arquivo."""
    folder = str(Path(req.path).parent)
    try:
        if platform.system() == "Windows":
            subprocess.Popen(["explorer", folder])
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", folder])
        else:
            subprocess.Popen(["xdg-open", folder])
    except Exception as e:
        raise HTTPException(500, str(e))
    return {"ok": True}


# ── Subreddits ────────────────────────────────────────────────────────────────

@app.get("/music")
def list_music():
    """Lista arquivos de música disponíveis em assets/music/."""
    music_dir = ROOT / "assets" / "music"
    if not music_dir.exists():
        return []
    extensions = {".mp3", ".wav", ".ogg", ".m4a", ".flac"}
    files = sorted(f for f in music_dir.iterdir() if f.suffix.lower() in extensions)
    return [{"name": f.name, "path": str(f)} for f in files]


@app.get("/videos")
def list_videos():
    """Lista vídeos locais disponíveis em assets/videos/."""
    videos_dir = ROOT / "assets" / "videos"
    if not videos_dir.exists():
        return []
    extensions = {".mp4", ".mov", ".webm", ".mkv"}
    files = sorted(f for f in videos_dir.iterdir() if f.suffix.lower() in extensions)
    return [{"name": f.name, "path": str(f)} for f in files]


@app.post("/cleanup")
def cleanup_public():
    """Remove imagens temporárias dyk_img_* da pasta public do Remotion."""
    public_dir = ROOT / "video-renderer" / "public"
    deleted = []
    if public_dir.exists():
        for f in public_dir.glob("dyk_img_*"):
            f.unlink(missing_ok=True)
            deleted.append(f.name)
    return {"deleted": deleted, "count": len(deleted)}


@app.post("/dyk/upload-video")
async def upload_dyk_video(file: UploadFile = File(...)):
    """Recebe um vídeo local e salva em assets/videos/ para uso nos cards."""
    allowed = {".mp4", ".mov", ".webm", ".mkv"}
    suffix = Path(file.filename or "video.mp4").suffix.lower()
    if suffix not in allowed:
        raise HTTPException(400, f"Formato não suportado: {suffix}. Use: {', '.join(allowed)}")
    videos_dir = ROOT / "assets" / "videos"
    videos_dir.mkdir(parents=True, exist_ok=True)
    dest = videos_dir / (file.filename or f"uploaded{suffix}")
    dest.write_bytes(await file.read())
    return {"name": dest.name, "ok": True}


@app.post("/dyk/search-images")
def dyk_search_images(req: ImageSearchRequest):
    """Busca imagens adicionais via Pexels/Unsplash/Pixabay sem apagar o contexto atual."""
    import sys as _sys
    _sys.path.insert(0, str(ROOT))
    from modules.assets.assets_didyouknow import DYKAssetsModule
    per_source = max(1, min(10, req.per_source))
    try:
        images = DYKAssetsModule().search(req.query, per_source=per_source)
        return {"images": images, "query": req.query}
    except Exception as e:
        raise HTTPException(500, f"Erro na busca de imagens: {e}")


@app.post("/dyk/generate")
def dyk_generate(req: DYKGenerateRequest):
    """ Gera fatos DYK via Groq + candidatos de imagem nos provedores de imagem disponíveis. """
    import sys as _sys
    _sys.path.insert(0, str(ROOT))
    from modules.intelligence.intelligence_didyouknow import DYKIntelligenceModule
    from modules.assets.assets_didyouknow import DYKAssetsModule

    config = load_config()
    if req.profile not in config.get("profiles", {}):
        raise HTTPException(400, f"Perfil '{req.profile}' não encontrado")

    profile  = config["profiles"][req.profile]
    groq_cfg = config.get("groq", {"temperature": 0.8, "max_tokens": 1024})
    dyk_cfg  = config.get("did-you-know", {})
    num_facts = req.num_facts or dyk_cfg.get("num_facts", 5)
    imgs_per_source = dyk_cfg.get("imgs_per_source", 3)

    try:
        content = DYKIntelligenceModule().run(
            topic=req.topic,
            num_facts=num_facts,
            language=profile.get("language", "pt-BR"),
            niche=profile.get("niche", "curiosidades"),
            temperature=float(groq_cfg.get("temperature", 0.8)),
            max_tokens=int(groq_cfg.get("max_tokens", 1024)),
        )
    except Exception as e:
        raise HTTPException(500, f"Erro ao gerar fatos: {e}")

    queries = [f.image_query for f in content.facts]
    candidates_per_fact = DYKAssetsModule().search_all(queries, per_source=imgs_per_source)

    facts_out = [
        {
            "text":        fact.text,
            "image_query": fact.image_query,
            "candidates":  candidates_per_fact[i] if i < len(candidates_per_fact) else [],
        }
        for i, fact in enumerate(content.facts)
    ]
    return {"topic": content.topic, "facts": facts_out}


@app.post("/dyk/render")
async def dyk_render(req: DYKRenderRequest):
    """Baixa imagens escolhidas e renderiza o template DidYouKnow via Remotion."""
    import shutil
    import urllib.request as _ur

    config = load_config()
    if req.profile not in config.get("profiles", {}):
        raise HTTPException(400, f"Perfil '{req.profile}' não encontrado")

    profile    = config["profiles"][req.profile]
    public_dir = ROOT / "video-renderer" / "public"
    public_dir.mkdir(parents=True, exist_ok=True)

    # Download das imagens / cópia de vídeos locais escolhidos
    fact_props: list[dict] = []
    for i, fact in enumerate(req.facts):
        if fact.image_url.startswith("video:"):
            # Vídeo local de assets/videos/
            video_name = fact.image_url[6:]
            video_src  = ROOT / "assets" / "videos" / video_name
            video_dst  = public_dir / video_name
            if video_src.exists() and not video_dst.exists():
                shutil.copy2(str(video_src), str(video_dst))
            fact_props.append({"text": fact.text, "video": video_name})
        else:
            img_filename = f"dyk_img_{i:02d}.jpg"
            img_path     = public_dir / img_filename
            try:
                r = _ur.Request(fact.image_url, headers={"User-Agent": "shorts-agent/1.0"})
                with _ur.urlopen(r, timeout=15) as resp:
                    img_path.write_bytes(resp.read())
            except Exception as e:
                raise HTTPException(502, f"Erro ao baixar imagem {i}: {e}")
            fact_props.append({"text": fact.text, "image": img_filename})

    # Config de duração — suporte a override por card
    fps              = config.get("layout", {}).get("fps", 30)
    default_seconds  = config.get("did-you-know", {}).get("card_duration_seconds", 9)
    default_frames   = int(default_seconds * fps)

    card_frames_list = [
        int((fact.duration_seconds or default_seconds) * fps)
        for fact in req.facts
    ]
    total_frames = sum(card_frames_list)

    props: dict = {
        "facts": fact_props,
        "cardFrames": default_frames,
        "cardFramesList": card_frames_list,
    }

    # Música — usa override se fornecido, senão fallback do perfil
    if req.music_name:
        music_src = ROOT / "assets" / "music" / req.music_name
    else:
        music_cfg = profile.get("music_path")
        music_src = ROOT / music_cfg if music_cfg else None
    if music_src and music_src.exists():
        music_dst = public_dir / music_src.name
        if not music_dst.exists():
            shutil.copy2(str(music_src), str(music_dst))
        props["music"] = music_src.name

    # Avatar
    avatar_cfg = profile.get("avatar_path", "")
    if avatar_cfg:
        avatar_src = ROOT / avatar_cfg
        if avatar_src.exists():
            avatar_dst = public_dir / avatar_src.name
            if not avatar_dst.exists():
                shutil.copy2(str(avatar_src), str(avatar_dst))
            props["avatar"] = avatar_src.name

    props["nome"] = profile.get("account_name", "")

    # CTA video por perfil
    cta_path_cfg = profile.get("cta_video_path", "")
    if cta_path_cfg:
        cta_src = ROOT / cta_path_cfg
        if cta_src.exists():
            cta_dst = public_dir / cta_src.name
            if not cta_dst.exists():
                shutil.copy2(str(cta_src), str(cta_dst))
            props["ctaVideo"] = cta_src.name

    # Configura job
    job_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    jobs[job_id] = {"status": "running", "log": [], "started_at": datetime.now().isoformat()}

    import platform as _plat
    npx          = "npx.cmd" if _plat.system() == "Windows" else "npx"
    remotion_dir = ROOT / "video-renderer"
    output_dir   = ROOT / "output" / "shorts"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"dyk_{req.profile}_{job_id}.mp4"

    cmd = [
        npx, "remotion", "render",
        "src/index.ts",
        "DidYouKnow",
        str(output_path),
        "--props", json.dumps(props, ensure_ascii=False),
        "--duration", str(total_frames),
        "--fps", str(fps),
        "--offthread-video-cache-size-in-bytes", "512000000",
    ]

    def _run_sync():
        import subprocess
        env = {**__import__('os').environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=str(remotion_dir),
            env=env,
        )
        for raw in proc.stdout:
            line = raw.decode("utf-8", errors="replace").rstrip()
            jobs[job_id]["log"].append(line)
        proc.wait()
        jobs[job_id]["status"]      = "done" if proc.returncode == 0 else "error"
        jobs[job_id]["returncode"]  = proc.returncode
        jobs[job_id]["finished_at"] = datetime.now().isoformat()
        if proc.returncode == 0:
            for img_file in public_dir.glob("dyk_img_*"):
                img_file.unlink(missing_ok=True)
            # Gera metadata SEO
            try:
                import sys as _sys2
                _sys2.path.insert(0, str(ROOT))
                from modules.intelligence.intelligence_didyouknow import DYKIntelligenceModule
                meta = DYKIntelligenceModule().generate_metadata(
                    topic=req.topic or "",
                    facts=[f.text for f in req.facts],
                    language=profile.get("language", "pt-BR"),
                )
                meta_dir = ROOT / "output" / "metadata"
                meta_dir.mkdir(parents=True, exist_ok=True)
                (meta_dir / f"{job_id}.json").write_text(
                    json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                jobs[job_id]["metadata"] = meta
            except Exception as _me:
                jobs[job_id]["metadata_error"] = str(_me)

    asyncio.create_task(asyncio.to_thread(_run_sync))
    return {"job_id": job_id}


@app.get("/subreddits/suggestions")
def subreddit_suggestions():
    return [
        {"name": "interestingasfuck",    "category": "curiosidades"},
        {"name": "nextfuckinglevel",      "category": "impressionante"},
        {"name": "oddlysatisfying",       "category": "satisfatório"},
        {"name": "blackmagicfuckery",     "category": "truques"},
        {"name": "BeAmazed",             "category": "incrível"},
        {"name": "Damnthatsinteresting", "category": "fatos"},
        {"name": "mildlyinteresting",    "category": "curioso"},
        {"name": "woahdude",             "category": "mente explode"},
        {"name": "movies",               "category": "filmes"},
        {"name": "television",           "category": "séries"},
    ]