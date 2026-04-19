"""
models.py — Contratos de dados do pipeline.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union


@dataclass
class VideoSource:
    url: str
    video_id: str
    title: str
    description: str
    channel_name: str
    duration_seconds: int
    clip_path: Path
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
    origin: str                                        # "reddit" | "manual"
    image_path: Path                                   # sempre Path, nunca str
    source_url: str                                    # URL original
    title: str = ""
    context_comments: list[str] = field(default_factory=list)
    subreddit: str = ""

    def to_dict(self) -> dict:
        return {
            "kind": "image",
            "source_url": self.source_url,
            "title": self.title,
            "subreddit": self.subreddit,
            "origin": self.origin,
        }


@dataclass
class GeneratedContent:
    curiosity_text: str          # hook curto (zona 1)
    comment_text: str            # comentário (zona 3)
    story_text: str = ""         # narrativa da imagem (zona 2)
    hashtags: list[str] = field(default_factory=list)
    language: str = "pt-BR"


@dataclass
class PreparedAssets:
    background_video_path: Path
    avatar_path: Path
    account_name: str
    clip_path: Optional[Path] = None
    image_path: Optional[Path] = None
    music_path: Optional[Path] = None


@dataclass
class RenderedShort:
    video_path: Path
    width: int
    height: int
    duration_seconds: float


@dataclass
class PipelineContext:
    profile_name: str
    config: dict
    source: Optional[Union[VideoSource, ImageSource]] = None
    image_source: Optional[ImageSource] = None         # pipeline de imagem
    content: Optional[GeneratedContent] = None
    assets: Optional[PreparedAssets] = None
    rendered: Optional[RenderedShort] = None