"""
video_types/comment_card.py — Tipo "Comment Card Short"

Layout em 3 zonas empilhadas dentro de um card centralizado:
  ┌─────────────────────────┐
  │  [fundo animado do canal]│
  │  ┌───────────────────┐  │
  │  │ 1. Curiosidade    │  │
  │  │ 2. Clipe do vídeo │  │
  │  │ 3. Comentário     │  │
  │  └───────────────────┘  │
  └─────────────────────────┘

É o tipo padrão atual. Para outros formatos, crie um novo arquivo
herdando de BaseVideoType sem alterar este.
"""
import textwrap
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from modules.models import GeneratedContent, PreparedAssets
from modules.render.video_types.base import BaseVideoType


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Tenta carregar uma fonte do sistema; cai para default do Pillow se falhar."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _draw_rounded_rect(draw: ImageDraw.Draw, xy, radius: int, fill, opacity: int = 255):
    """Desenha retângulo com bordas arredondadas."""
    x0, y0, x1, y1 = xy
    r = radius
    fill_rgba = (*fill, opacity)
    draw.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=fill_rgba)


def _draw_wrapped_text(
    draw: ImageDraw.Draw,
    text: str,
    font: ImageFont.FreeTypeFont,
    color: tuple,
    x: int,
    y: int,
    max_width: int,
    line_spacing: int = 8,
) -> int:
    """Desenha texto com quebra de linha automática. Retorna y final."""
    avg_char_width = font.getlength("A")
    chars_per_line = max(1, int(max_width / avg_char_width))
    lines = textwrap.wrap(text, width=chars_per_line)
    current_y = y
    for line in lines:
        draw.text((x, current_y), line, font=font, fill=color)
        bbox = font.getbbox(line)
        current_y += (bbox[3] - bbox[1]) + line_spacing
    return current_y


class CommentCardVideoType(BaseVideoType):
    """Tipo de short: card com curiosidade + clipe + comentário."""

    type_id = "comment_card"

    def __init__(self, layout_cfg: dict, clip_frames: list[np.ndarray]):
        self._layout = layout_cfg
        self._clip_frames = clip_frames  # frames pré-extraídos do clipe
        self._clip_fps = 30              # ajustado pelo Render Module

    def get_audio_path(self, assets: PreparedAssets) -> Path:
        # Usa o áudio direto do clipe — sem alterações
        return assets.clip_path

    def compose_frame(
        self,
        assets: PreparedAssets,
        content: GeneratedContent,
        layout_cfg: dict,
        timestamp: float,
    ) -> np.ndarray:
        W = layout_cfg["width"]
        H = layout_cfg["height"]
        padding = layout_cfg["card_padding"]
        card_bg = _hex_to_rgb(layout_cfg["card_background_color"])
        text_primary = _hex_to_rgb(layout_cfg["text_color_primary"])
        text_secondary = _hex_to_rgb(layout_cfg["text_color_secondary"])
        border_radius = layout_cfg["card_border_radius"]
        card_opacity = int(layout_cfg["card_opacity"] * 255)

        # --- Canvas base (RGBA para suportar transparência do card) ---
        canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)

        # --- Dimensões do card ---
        card_h = int(H * layout_cfg["card_height_ratio"])
        card_w = int(W * 0.88)
        card_x = (W - card_w) // 2
        card_y = (H - card_h) // 2

        # --- Zonas internas do card ---
        inner_w = card_w - 2 * padding
        inner_x = card_x + padding

        zone1_h = int(card_h * 0.22)   # Curiosidade
        zone2_h = int(card_h * 0.48)   # Clipe
        zone3_h = int(card_h * 0.22)   # Comentário
        gap = int(card_h * 0.026)

        zone1_y = card_y + padding
        zone2_y = zone1_y + zone1_h + gap
        zone3_y = zone2_y + zone2_h + gap

        # --- Desenha o card ---
        _draw_rounded_rect(
            draw,
            (card_x, card_y, card_x + card_w, card_y + card_h),
            radius=border_radius,
            fill=card_bg,
            opacity=card_opacity,
        )

        # --- ZONA 1: Curiosidade ---
        font_curiosity = _load_font(38, bold=True)
        font_small = _load_font(28)
        font_comment = _load_font(30)
        font_name = _load_font(28, bold=True)

        label_font = _load_font(22)
        draw.text(
            (inner_x, zone1_y),
            "💡 Você sabia?",
            font=label_font,
            fill=(*text_secondary, 255),
        )
        label_h = label_font.getbbox("A")[3] + 10
        _draw_wrapped_text(
            draw,
            content.curiosity_text,
            font_curiosity,
            (*text_primary, 255),
            inner_x,
            zone1_y + label_h,
            inner_w,
            line_spacing=6,
        )

        # --- ZONA 2: Frame do clipe ---
        clip_frame_idx = int(timestamp * self._clip_fps) % max(1, len(self._clip_frames))
        if self._clip_frames:
            frame_rgb = self._clip_frames[clip_frame_idx]
            clip_img = Image.fromarray(frame_rgb).resize(
                (inner_w, zone2_h), Image.LANCZOS
            )
            # Borda arredondada no clipe
            clip_mask = Image.new("L", (inner_w, zone2_h), 0)
            mask_draw = ImageDraw.Draw(clip_mask)
            mask_draw.rounded_rectangle(
                [0, 0, inner_w, zone2_h], radius=12, fill=255
            )
            canvas.paste(clip_img, (inner_x, zone2_y), clip_mask)

        # --- ZONA 3: Comentário (avatar + nome + texto) ---
        avatar_size = 56
        avatar_x = inner_x
        avatar_y = zone3_y + (zone3_h - avatar_size) // 2

        if assets.avatar_path.exists():
            avatar_img = Image.open(assets.avatar_path).convert("RGBA")
            avatar_img = avatar_img.resize((avatar_size, avatar_size), Image.LANCZOS)
            # Máscara circular
            mask = Image.new("L", (avatar_size, avatar_size), 0)
            ImageDraw.Draw(mask).ellipse([0, 0, avatar_size, avatar_size], fill=255)
            canvas.paste(avatar_img, (avatar_x, avatar_y), mask)

        text_after_avatar_x = avatar_x + avatar_size + 12
        draw.text(
            (text_after_avatar_x, zone3_y + 8),
            assets.account_name,
            font=font_name,
            fill=(*text_primary, 255),
        )
        _draw_wrapped_text(
            draw,
            content.comment_text,
            font_comment,
            (*text_secondary, 255),
            text_after_avatar_x,
            zone3_y + 8 + font_name.getbbox("A")[3] + 8,
            inner_w - avatar_size - 12,
            line_spacing=4,
        )

        return np.array(canvas.convert("RGB"))