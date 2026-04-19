"""
video_types/base.py — Contrato base para tipos de vídeo.

Para adicionar um novo tipo de short no futuro:
  1. Crie um arquivo em modules/render/video_types/
  2. Herde de BaseVideoType
  3. Implemente os métodos abstratos
  4. Registre em video_types/__init__.py

O pipeline não precisará mudar.
"""
from abc import ABC, abstractmethod
from pathlib import Path

from modules.models import GeneratedContent, PreparedAssets


class BaseVideoType(ABC):
    """
    Define o contrato que todo tipo de vídeo deve implementar.
    O Render Module chama esses métodos sem saber qual tipo está executando.
    """

    @property
    @abstractmethod
    def type_id(self) -> str:
        """Identificador único do tipo. Ex: 'comment_card', 'split_reaction'"""
        ...

    @abstractmethod
    def compose_frame(
        self,
        assets: PreparedAssets,
        content: GeneratedContent,
        layout_cfg: dict,
        timestamp: float,
    ):
        """
        Retorna um frame numpy (H x W x 3) para o timestamp dado.
        O Render Module chama isso frame a frame.
        """
        ...

    @abstractmethod
    def get_audio_path(self, assets: PreparedAssets) -> Path:
        """Retorna o caminho do áudio que será usado no short."""
        ...