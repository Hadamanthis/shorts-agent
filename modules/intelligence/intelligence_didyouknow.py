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

Gere {num_facts} fatos sobre "{topic}" que, juntos, contam uma história envolvente — não uma lista mecânica.

Estrutura narrativa obrigatória:
- Fato 1 (gancho): Um fato que quebra uma expectativa ou revela algo contra-intuitivo. Deve fisgar.
- Fatos intermediários: Aprofundam, revelam detalhes humanos, contradizem o senso comum, constroem tensão.
- Último fato (desfecho): Uma virada, consequência marcante ou perspectiva que muda tudo.

REGRA CRÍTICA: Antes de escrever cada fato, pesquise na internet para verificar datas, números,
nomes e eventos. NUNCA invente ou estime dados — use apenas fatos verificáveis e precisos.

Regras para cada fato (TEXT):
- 1-2 frases conversacionais. Máximo 150 caracteres.
- Escreva como alguém contando uma descoberta fascinante num papo, não como verbete de enciclopédia.
- Use números, datas, nomes de lugares e pessoas reais e verificados.
- Os fatos devem se conectar — o leitor deve sentir que está descobrindo uma história, não lendo uma lista.
- NUNCA comece com "Sabia que", "Você sabia", "É importante", "Fascinante".
- NUNCA invente dados — se não encontrar na pesquisa, use um fato diferente que consiga verificar.

IMAGE_QUERY: Query em inglês para busca de foto portrait no Pexels/Unsplash. 2-4 palavras específicas.
Ex: "ancient roman aqueduct", "deep ocean bioluminescence", "1960s NASA control room".

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

    def generate_metadata(self, topic: str, facts: list[str], language: str = "pt-BR") -> dict:
        lang_instruction = _LANGUAGE_INSTRUCTIONS.get(language, _LANGUAGE_INSTRUCTIONS["pt-BR"])
        facts_text = "\n".join(f"- {f}" for f in facts)

        system_prompt = f"""Você é especialista em SEO para YouTube Shorts e Instagram Reels, focado no público brasileiro.
{lang_instruction}
Sua única saída é um objeto JSON válido, sem texto antes ou depois, sem markdown.

Crie metadados otimizados para SEO de um vídeo "Você Sabia?" com os fatos abaixo.

REGRAS:
- Título: chamativo, inclui emoji, máx 90 caracteres. Não use hashtags no título.
- Descrição: 3-4 linhas curiosas e naturais com hashtags integradas ao texto. Bloco de hashtags no final. Máx 500 caracteres.
- Hashtags: lista de 15-20 hashtags. Misture: nicho (#vocesabia, #curiosidades, #fatos), tópico específico e virais (#shorts, #reels, #trending). Foco no público BR 18-35 anos.

Retorne SOMENTE este JSON:
{{
  "title": "...",
  "description": "...",
  "hashtags": ["#hashtag1", "#hashtag2", ...]
}}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Tópico: {topic}\n\nFatos:\n{facts_text}"},
        ]

        try:
            response = self._client.chat.completions.create(
                model=TEXT_MODEL,
                temperature=0.7,
                max_tokens=1024,
                messages=messages,
            )
            raw = response.choices[0].message.content.strip()
            clean = re.sub(r"```(?:json)?|```", "", raw).strip()
            data = json.loads(clean)
            return {
                "title": data.get("title", topic),
                "description": data.get("description", ""),
                "hashtags": data.get("hashtags", []),
            }
        except Exception as e:
            logger.warning(f"[DYK Metadata] Falha ao gerar metadata: {e}")
            return {"title": topic, "description": "", "hashtags": []}
