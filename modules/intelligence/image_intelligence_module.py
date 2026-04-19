"""
intelligence/image_intelligence_module.py — Gera hook, story e comentário a partir de uma imagem.
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

        logger.info(f"[ImageIntelligence] Analisando: {image_source.image_path.name}")

        image_b64  = base64.standard_b64encode(image_source.image_path.read_bytes()).decode()
        media_type = {
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".png": "image/png",  ".webp": "image/webp",
            ".gif": "image/gif",
        }.get(image_source.image_path.suffix.lower(), "image/jpeg")

        messages = self._build_messages(image_b64, media_type, image_source, content_cfg, language, niche)
        response_text = self._call_groq(messages, groq_cfg)
        content = self._parse_response(response_text, language)

        logger.info(f"[ImageIntelligence] Hook: {content.curiosity_text[:60]}...")
        logger.info(f"[ImageIntelligence] Comentário: {content.comment_text[:60]}...")
        return content

    def _build_messages(self, image_b64, media_type, image_source, content_cfg, language, niche):
        lang_instruction = _LANGUAGE_INSTRUCTIONS.get(language, _LANGUAGE_INSTRUCTIONS["pt-BR"])
        tone_instruction = _TONE_INSTRUCTIONS.get(content_cfg["comment_tone"], _TONE_INSTRUCTIONS["surpreso"])

        context_block = ""
        if image_source.title:
            context_block += f'Título do post: "{image_source.title}"\n'
        if image_source.context_comments:
            context_block += "Comentários reais:\n"
            context_block += "\n".join(f"  - {c}" for c in image_source.context_comments[:5])
            context_block += "\n"

        system_prompt = f"""Você é um roteirista de YouTube Shorts virais no nicho de {niche}.
{lang_instruction}
Sua única saída é um objeto JSON válido, sem texto antes ou depois, sem markdown.

Você gera conteúdo para um short de 45–60 segundos. Regras por campo:

HOOK — Fato factual em UMA linha. Máximo 8 palavras.
- Concreto: datas, lugares, números, comportamentos específicos.
- Sem opinião, sem adjetivo emocional, sem verbo de comando.
- Exemplos certos:  "No Japão, bêbados dormem na rua sem ser perturbados"
                    "Em 1888, abolir escravidão era 'destruir a economia'"
- Exemplos errados: "Isso vai te surpreender!" / "Fato incrível sobre o Japão"
Máximo {content_cfg['curiosity_max_chars']} caracteres.

STORY — A história por trás da imagem. Informativo, denso, envolvente.
- Use o título e comentários do Reddit como base — não invente fatos.
- Escreva como um parágrafo de enciclopédia reescrito por alguém que adora contar histórias.
- Inclua: contexto histórico, como funcionava na prática, detalhes específicos e curiosos,
  consequências ou comparações que ajudem o espectador a visualizar.
- Texto longo o suficiente para o espectador passar 15–20 segundos lendo.
- Termine com uma afirmação conclusiva — sem perguntas, sem convites a comentar.
  Isso é papel do COMMENT, não do STORY.
- Mínimo 4 frases, máximo 7. Máximo {content_cfg['curiosity_max_chars'] * 3} caracteres.

COMMENT — 2 frases curtas. Escreva como uma pessoa real comentando no YouTube.
Imagine alguém que acabou de ler o story e teve uma reação genuína no calor do momento.

- Frase 1: reação direta e específica ao conteúdo — humor, ironia ou espanto natural.
  Faça referência a um detalhe concreto do story (uma contradição, uma comparação absurda).
  Exemplos certos:
    "O mais engraçado é que isso parece exatamente com aquele jogo de adivinhação de personagem."
    "Basicamente criaram um manual de preconceito e chamaram de ciência."
    "Eles literalmente desenharam um catálogo de estereótipos e acharam que era investigação."
  Exemplos errados:
    "Isso reflete uma sociedade complexa." / "É fascinante como a história nos ensina."

- Frase 2: pergunta ou provocação que convide a discussão de forma natural — não um CTA.
  Deve surgir da frase 1, não ser genérica.
  Exemplos certos:
    "Será que algum dia a gente vai parar de julgar cara por cara?"
    "Imagina isso sendo usado hoje — quantas pessoas inocentes seriam fichadas?"
  Exemplos errados:
    "E você, o que acha?" / "Isso muda como você vê a história?"

NUNCA use: "reflete uma sociedade", "é fascinante", "nos ensina que", "é importante".
NUNCA termine com reticências (...).
{tone_instruction}
Máximo {content_cfg['comment_max_chars']} caracteres.

HASHTAGS — 3 a 5 hashtags relevantes."""

        user_text = f"""{context_block}
Analise a imagem e gere o conteúdo seguindo exatamente as regras do sistema.

Retorne SOMENTE este JSON:
{{
  "hook": "...",
  "story": "...",
  "comment": "...",
  "hashtags": ["...", "..."]
}}"""

        return [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{image_b64}"}},
                    {"type": "text", "text": user_text},
                ],
            },
        ]

    def _call_groq(self, messages, groq_cfg) -> str:
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
            curiosity_text=data.get("hook", data.get("curiosity_text", "")).strip(),
            story_text=data.get("story", "").strip(),
            comment_text=data.get("comment", data.get("comment_text", "")).strip(),
            hashtags=data.get("hashtags", []),
            language=language,
        )