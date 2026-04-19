"""
intelligence/intelligence_module.py — Gera curiosidade e comentário via LLM (Groq).

Responsabilidades:
  - Montar um prompt rico com contexto do vídeo
  - Chamar a Groq API com o modelo configurado
  - Parsear e validar o JSON retornado
  - Adaptar o idioma conforme o perfil

Não sabe nada sobre vídeo, layout ou render.
"""
import json
import logging
import os
import re

from groq import Groq

from modules.models import GeneratedContent, PipelineContext, VideoSource

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Mapeamento de idioma → instrução no system prompt
_LANGUAGE_INSTRUCTIONS = {
    "pt-BR": "Responda SEMPRE em português brasileiro informal e natural.",
    "en-US": "Always respond in casual, natural American English.",
    "es-ES": "Responde SIEMPRE en español informal y natural.",
}

# Mapeamento de tom → instrução no prompt
_TONE_INSTRUCTIONS = {
    "surpreso":    "O comentário deve soar surpreso e impressionado.",
    "humoristico": "O comentário deve ser bem-humorado e leve.",
    "reflexivo":   "O comentário deve soar reflexivo e pensativo.",
    "emocional":   "O comentário deve soar emocionado e tocado.",
}


class IntelligenceModule:

    def __init__(self):
        load_dotenv()
        '''api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "GROQ_API_KEY não encontrada. "
                "Exporte a variável: export GROQ_API_KEY=sua_chave"
            )
        self._client = Groq(api_key=api_key)'''
        self._client = Groq()

    def run(self, ctx: PipelineContext, source: VideoSource) -> GeneratedContent:
        profile = ctx.config["profiles"][ctx.profile_name]
        content_cfg = ctx.config["content"]
        groq_cfg = ctx.config["groq"]
        language = profile["language"]
        niche = profile["niche"]

        logger.info(f"[Intelligence] Gerando conteúdo para: {source.title}")

        system_prompt = self._build_system_prompt(language, niche)
        user_prompt = self._build_user_prompt(source, content_cfg, language)

        response_text = self._call_groq(system_prompt, user_prompt, groq_cfg)
        content = self._parse_response(response_text, language)

        logger.info(f"[Intelligence] Curiosidade: {content.curiosity_text[:60]}...")
        logger.info(f"[Intelligence] Comentário: {content.comment_text[:60]}...")
        return content

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _build_system_prompt(self, language: str, niche: str) -> str:
        lang_instruction = _LANGUAGE_INSTRUCTIONS.get(
            language, _LANGUAGE_INSTRUCTIONS["pt-BR"]
        )
        return f"""Você é um criador de conteúdo especializado no nicho de {niche}.
{lang_instruction}
Sua tarefa é gerar conteúdo para YouTube Shorts no formato de card com 3 zonas:
  - Zona 1: um fato curioso ou insight sobre o vídeo
  - Zona 3: um comentário autêntico de espectador

Você DEVE retornar apenas um objeto JSON válido, sem texto antes ou depois, sem markdown.
"""

    def _build_user_prompt(
        self, source: VideoSource, content_cfg: dict, language: str
    ) -> str:
        tone_instruction = _TONE_INSTRUCTIONS.get(
            content_cfg["comment_tone"], _TONE_INSTRUCTIONS["surpreso"]
        )
        comments_block = "\n".join(
            f"  - {c}" for c in source.comments
        ) or "  (nenhum comentário disponível)"

        return f"""Vídeo: "{source.title}"
Canal: {source.channel_name}
Descrição: {source.description[:500]}

Comentários reais do vídeo (use como referência de tom e reação do público):
{comments_block}

Gere o conteúdo seguindo EXATAMENTE estas restrições:
  - curiosity_text: {content_cfg['num_facts']} fato(s) curioso(s) sobre o vídeo. Máximo {content_cfg['curiosity_max_chars']} caracteres.
  - comment_text: um comentário de espectador autêntico. {tone_instruction} Máximo {content_cfg['comment_max_chars']} caracteres.
  - hashtags: lista de 3 a 5 hashtags relevantes.

Retorne SOMENTE este JSON (sem markdown, sem explicações):
{{
  "curiosity_text": "...",
  "comment_text": "...",
  "hashtags": ["...", "..."]
}}"""

    def _call_groq(self, system: str, user: str, groq_cfg: dict) -> str:
        response = self._client.chat.completions.create(
            model=groq_cfg["model"],
            temperature=groq_cfg["temperature"],
            max_tokens=groq_cfg["max_tokens"],
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content.strip()

    def _parse_response(self, text: str, language: str) -> GeneratedContent:
        """Parseia JSON do LLM com fallback tolerante a markdown."""
        # Remove blocos de código markdown se o modelo insistir em colocá-los
        clean = re.sub(r"```(?:json)?|```", "", text).strip()
        try:
            data = json.loads(clean)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"LLM não retornou JSON válido. Erro: {e}\nResposta:\n{text}"
            )

        return GeneratedContent(
            curiosity_text=data.get("curiosity_text", "").strip(),
            comment_text=data.get("comment_text", "").strip(),
            hashtags=data.get("hashtags", []),
            language=language,
        )