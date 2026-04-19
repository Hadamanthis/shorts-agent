"""
intelligence/image_intelligence_module.py — Gera hook e comentário a partir de uma imagem.

Usa Groq Vision (llava ou llama com vision) para analisar a imagem visualmente
e gerar conteúdo original — não depende só do texto ao redor da imagem.

Responsabilidades:
  - Codificar a imagem em base64
  - Montar prompt com contexto do Reddit (se houver) + a imagem
  - Chamar Groq com modelo vision
  - Devolver GeneratedContent

Não sabe nada sobre download, layout ou render.
"""
import base64
import json
import logging
import os
import re
from pathlib import Path

from groq import Groq
from dotenv import load_dotenv

from modules.models import GeneratedContent, ImageSource, PipelineContext

load_dotenv()
logger = logging.getLogger(__name__)

# Modelo com suporte a vision disponível no Groq
VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

_LANGUAGE_INSTRUCTIONS = {
    "pt-BR": "Responda SEMPRE em português brasileiro informal e natural.",
    "en-US": "Always respond in casual, natural American English.",
    "es-ES": "Responde SIEMPRE en español informal y natural.",
}

_TONE_INSTRUCTIONS = {
    "surpreso":    "O comentário deve soar surpreso e impressionado.",
    "humoristico": "O comentário deve ser bem-humorado e leve.",
    "reflexivo":   "O comentário deve soar reflexivo e pensativo.",
    "emocional":   "O comentário deve soar emocionado e tocado.",
}


class ImageIntelligenceModule:

    def __init__(self):
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError("GROQ_API_KEY não encontrada.")
        self._client = Groq(api_key=api_key)

    def run(self, ctx: PipelineContext, image_source: ImageSource) -> GeneratedContent:
        profile     = ctx.config["profiles"][ctx.profile_name]
        content_cfg = ctx.config["content"]
        groq_cfg    = ctx.config["groq"]
        language    = profile["language"]
        niche       = profile["niche"]

        logger.info(f"[ImageIntelligence] Analisando imagem: {image_source.image_path.name}")

        image_b64  = self._encode_image(image_source.image_path)
        media_type = self._media_type(image_source.image_path)

        messages = self._build_messages(
            image_b64=image_b64,
            media_type=media_type,
            image_source=image_source,
            content_cfg=content_cfg,
            language=language,
            niche=niche,
        )

        response_text = self._call_groq(messages, groq_cfg)
        content = self._parse_response(response_text, language)

        logger.info(f"[ImageIntelligence] Hook: {content.curiosity_text[:60]}...")
        logger.info(f"[ImageIntelligence] Comentário: {content.comment_text[:60]}...")
        return content

    # ── Internos ─────────────────────────────────────────────────────────────

    def _encode_image(self, path: Path) -> str:
        return base64.standard_b64encode(path.read_bytes()).decode("utf-8")

    def _media_type(self, path: Path) -> str:
        ext = path.suffix.lower()
        return {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".gif": "image/gif",
        }.get(ext, "image/jpeg")

    def _build_messages(
        self,
        image_b64: str,
        media_type: str,
        image_source: ImageSource,
        content_cfg: dict,
        language: str,
        niche: str,
    ) -> list[dict]:
        lang_instruction = _LANGUAGE_INSTRUCTIONS.get(language, _LANGUAGE_INSTRUCTIONS["pt-BR"])
        tone_instruction = _TONE_INSTRUCTIONS.get(
            content_cfg["comment_tone"], _TONE_INSTRUCTIONS["surpreso"]
        )

        # Contexto textual (Reddit title + comentários, se houver)
        context_block = ""
        if image_source.title:
            context_block += f'Título do post: "{image_source.title}"\n'
        if image_source.context_comments:
            context_block += "Comentários reais sobre essa imagem:\n"
            context_block += "\n".join(f"  - {c}" for c in image_source.context_comments)
            context_block += "\n"

        system_prompt = (
            f"Você é um criador de conteúdo especializado no nicho de {niche}. "
            f"{lang_instruction} "
            f"Retorne SOMENTE um objeto JSON válido, sem texto antes ou depois, sem markdown."
        )

        user_text = f"""{context_block}
Analise a imagem acima e gere conteúdo para um YouTube Short no formato card com 3 zonas:
  - hook: {content_cfg['num_facts']} frase(s) de gancho que desperte curiosidade sobre o que está na imagem. Máximo {content_cfg['curiosity_max_chars']} caracteres.
  - comentario: um comentário de espectador autêntico. {tone_instruction} Máximo {content_cfg['comment_max_chars']} caracteres.
  - hashtags: lista de 3 a 5 hashtags relevantes.

Retorne SOMENTE este JSON:
{{
  "curiosity_text": "...",
  "comment_text": "...",
  "hashtags": ["...", "..."]
}}"""

        return [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{image_b64}"
                        },
                    },
                    {"type": "text", "text": user_text},
                ],
            },
        ]

    def _call_groq(self, messages: list[dict], groq_cfg: dict) -> str:
        response = self._client.chat.completions.create(
            model=VISION_MODEL,
            temperature=groq_cfg["temperature"],
            max_tokens=groq_cfg["max_tokens"],
            messages=messages,
        )
        return response.choices[0].message.content.strip()

    def _parse_response(self, text: str, language: str) -> GeneratedContent:
        clean = re.sub(r"```(?:json)?|```", "", text).strip()
        try:
            data = json.loads(clean)
        except json.JSONDecodeError as e:
            raise ValueError(f"LLM não retornou JSON válido: {e}\nResposta:\n{text}")

        return GeneratedContent(
            curiosity_text=data.get("curiosity_text", "").strip(),
            comment_text=data.get("comment_text", "").strip(),
            hashtags=data.get("hashtags", []),
            language=language,
        )