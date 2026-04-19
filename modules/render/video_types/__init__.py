"""
video_types/__init__.py — Registry de tipos de vídeo.

Para adicionar um novo tipo:
  1. Crie modules/render/video_types/meu_tipo.py herdando de BaseVideoType
  2. Importe e adicione no dicionário REGISTRY abaixo
  3. Pronto — o pipeline encontra automaticamente pelo type_id
"""
from modules.render.video_types.comment_card import CommentCardVideoType

REGISTRY: dict = {
    CommentCardVideoType.type_id: CommentCardVideoType,
    # "split_reaction": SplitReactionVideoType,   # exemplo futuro
    # "facts_only":     FactsOnlyVideoType,        # exemplo futuro
}


def get_video_type(type_id: str):
    """Retorna a classe do tipo de vídeo pelo ID. Lança ValueError se não existir."""
    if type_id not in REGISTRY:
        available = list(REGISTRY.keys())
        raise ValueError(
            f"Tipo de vídeo '{type_id}' não encontrado. "
            f"Disponíveis: {available}"
        )
    return REGISTRY[type_id]