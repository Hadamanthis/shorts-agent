"""
models.py — Contratos de dados do pipeline.

Cada módulo recebe e devolve dataclasses tipadas.
Nenhum módulo passa dicionários soltos entre si.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union


@dataclass
class VideoSource:
    """Resultado do módulo de Ingestion."""
    url: str
    video_id: str
    title: str
    description: str
    channel_name: str
    duration_seconds: int
    clip_path: Path                    # Trecho recortado (.mp4)
    comments: list[str] = field(default_factory=list)
    thumbnail_url: str = ""

    def to_dict(self) -> dict:
        return {
            "kind": "video",
            "url": self.url,
            "video_id": self.video_id,
            "title": self.title,
            "channel": self.channel_name,
        }

@dataclass
class ImageSource:
    """Resultado do módulo de Ingestion Image."""
    url: str
    origin: str
    image_path: str
    title: str
    context_comments: str
    subreddit: str

    def to_dict(self) -> dict:
        return {
            "kind": "image",
            "url": self.url,
            "title": self.title,
            "subreddit": self.subreddit,
            "origin": self.origin,
        }

@dataclass
class GeneratedContent:
    curiosity_text: str      # Zona 1 — hook curto (≤ 12 palavras), pergunta ou afirmação chocante
    comment_text: str        # Zona 3 — reação que provoca comentários
    story_text: str = ""         # Zona 2: narrativa da imagem (3–5 frases), o "o que aconteceu"
    hashtags: list[str] = field(default_factory=list)
    language: str = "pt-BR"

@dataclass
class PreparedAssets:
    """Resultado do módulo de Asset Preparation."""
    background_video_path: Path        # Vídeo de fundo do canal
    avatar_path: Path                  # Foto de perfil da conta
    account_name: str                  # Nome exibido no comentário
    clip_path: Optional[Path] = None   # Trecho final (mesmo do VideoSource por ora)
    image_path: Optional[Path] = None  # None no pipeline de vídeo

@dataclass
class RenderedShort:
    """Resultado do módulo de Render."""
    video_path: Path                   # short final .mp4
    width: int
    height: int
    duration_seconds: float


@dataclass
class PipelineContext:
    """
    Objeto central que percorre todo o pipeline.
    Cada módulo preenche seu campo correspondente.
    """
    profile_name: str
    config: dict                       # Config carregada do config.yaml

    # Preenchidos progressivamente por cada módulo
    source: Optional[Union[VideoSource, ImageSource]] = None
    content: Optional[GeneratedContent] = None
    assets: Optional[PreparedAssets] = None
    rendered: Optional[RenderedShort] = None