"""
intelligence/intelligence_didyouknow.py — Gera fatos "Did You Know?" via Groq.
"""
import json
import logging
import os
import re

from groq import Groq
from dotenv import load_dotenv

from modules.models import DidYouKnowContent, DidYouKnowFact

load_dotenv()
logger = logging.getLogger(__name__)

TEXT_MODEL = "llama-3.3-70b-versatile"

_LANGUAGE_INSTRUCTIONS = {
    "pt-BR": "Responda SEMPRE em português brasileiro informal e natural.",
    "en-US": "Always respond in casual, natural American English.",
    "es-ES": "Responde SIEMPRE en español informal y natural.",
}


class DYKIntelligenceModule:

    def __init__(self):
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError("GROQ_API_KEY não encontrada.")
        self._client = Groq(api_key=api_key)

    def run(
        self,
        topic: str,
        num_facts: int,
        language: str,
        niche: str,
        temperature: float = 0.8,
        max_tokens: int = 1024,
    ) -> DidYouKnowContent:
        lang_instruction = _LANGUAGE_INSTRUCTIONS.get(language, _LANGUAGE_INSTRUCTIONS["pt-BR"])

        system_prompt = f"""Você é um roteirista de YouTube Shorts virais no nicho de {niche}.
{lang_instruction}
Sua única saída é um objeto JSON válido, sem texto antes ou depois, sem markdown.

Gere {num_facts} fatos fascinantes e surpreendentes sobre o tópico fornecido.

Para cada fato:
- TEXT: O fato em si. Conciso, impactante, surpreendente. 1-2 frases. Máximo 130 caracteres.
  - NÃO comece com "Sabia que", "Você sabia" ou variações.
  - Use números, datas, locais específicos quando possível.
  - Pesquise para garantir que é factual.
- IMAGE_QUERY: Uma query em inglês para Pexels que retorne uma imagem portrait/vertical
  relevante para o fato. 2-4 palavras. Ex: "ancient roman architecture", "deep ocean creatures".

Retorne SOMENTE este JSON:
{{
  "facts": [
    {{"text": "...", "image_query": "..."}},
    ...
  ]
}}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Tópico: {topic}"},
        ]

        response = self._client.chat.completions.create(
            model=TEXT_MODEL,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=messages,
        )
        raw = response.choices[0].message.content.strip()

        clean = re.sub(r"```(?:json)?|```", "", raw).strip()
        try:
            data = json.loads(clean)
        except json.JSONDecodeError as e:
            raise ValueError(f"LLM não retornou JSON válido: {e}\nResposta:\n{raw}")

        facts = [
            DidYouKnowFact(text=f["text"], image_query=f["image_query"])
            for f in data.get("facts", [])
        ]

        logger.info(f"[DYK Intelligence] Gerou {len(facts)} fatos sobre '{topic}'")
        return DidYouKnowContent(topic=topic, facts=facts, language=language)
