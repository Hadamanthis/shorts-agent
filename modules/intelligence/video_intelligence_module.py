"""
intelligence/video_intelligence_module.py — Gera hook, story e comentário a partir de um vídeo do Reddit.

Sem vision (vídeos não podem ser enviados como base64 ao Groq),
usa título + comentários do Reddit como contexto.
"""
import json
import logging
import os
import re

from groq import Groq
from dotenv import load_dotenv

from modules.models import GeneratedContent, VideoSource, PipelineContext

load_dotenv()
logger = logging.getLogger(__name__)

TEXT_MODEL = "llama-3.3-70b-versatile"

_LANGUAGE_INSTRUCTIONS = {
    "pt-BR": "Responda SEMPRE em português brasileiro informal e natural.",
    "en-US": "Always respond in casual, natural American English.",
    "es-ES": "Responde SIEMPRE en español informal y natural.",
}

_TONE_INSTRUCTIONS = {
    "surpreso":    "O comentário deve soar surpreso e impressionado.",
    "humoristico": "O comentário deve ser bem-humorado e fazendo boas referências.",
    "reflexivo":   "O comentário deve soar reflexivo e pensativo.",
    "emocional":   "O comentário deve soar emocionado e tocado.",
}


class VideoIntelligenceModule:

    def __init__(self):
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError("GROQ_API_KEY não encontrada.")
        self._client = Groq(api_key=api_key)

    def run(self, ctx: PipelineContext, source: VideoSource) -> GeneratedContent:
        profile     = ctx.config["profiles"][ctx.profile_name]
        content_cfg = ctx.config["content"]
        groq_cfg    = ctx.config["groq"]
        language    = profile["language"]
        niche       = profile["niche"]

        logger.info(f"[VideoIntelligence] Gerando conteúdo para: {source.title[:60]}")

        messages = self._build_messages(source, content_cfg, profile, language, niche)
        response_text = self._call_groq(messages, groq_cfg)
        content = self._parse_response(response_text, language)

        logger.info(f"[VideoIntelligence] Hook: {content.curiosity_text[:60]}...")
        logger.info(f"[VideoIntelligence] Comentário: {content.comment_text[:60]}...")
        return content

    def _build_messages(self, source: VideoSource, content_cfg: dict, profile: dict, language: str, niche: str) -> list[dict]:
        lang_instruction = _LANGUAGE_INSTRUCTIONS.get(language, _LANGUAGE_INSTRUCTIONS["pt-BR"])
        tone_instruction = _TONE_INSTRUCTIONS.get(profile["comment_tone"], _TONE_INSTRUCTIONS["surpreso"])

        context_block = f'Título do post: "{source.title}"\n'
        if source.channel_name:
            context_block += f'Subreddit: {source.channel_name}\n'
        if source.comments:
            context_block += "Comentários reais:\n"
            context_block += "\n".join(f"  - {c}" for c in source.comments[:5])
            context_block += "\n"

        system_prompt = f"""Você é um roteirista de YouTube Shorts virais no nicho de {niche}.
{lang_instruction}
Sua única saída é um objeto JSON válido, sem texto antes ou depois, sem markdown, não use triplas aspas.

Gere conteúdo para um short de 45–60 segundos com base no título e comentários do post do Reddit abaixo.
Regras por campo:

HOOK — Manchete de jornal sensacionalista mas factual. Máximo 10 palavras.
  - Tom de manchete: direto, impactante, pode usar contraste ou ironia.
  - Use fatos reais: datas, lugares, números, nomes.
  - Pode exagerar o drama sem mentir.
  - Exemplos: "Boston Enterrou Carros Vivos na Neve por Meses"
              "A URSS Classificava Criminosos Pela Cara — E Acertava Poucos"
              "Prefeitura Gastou Zero Reais Para 'Sumir' Com 6 Carros"
  - NUNCA use: "Incrível", "Chocante", "Você não vai acreditar".
  Máximo {content_cfg['curiosity_max_chars']} caracteres.

STORY — A história por trás do vídeo. Informativo, denso, envolvente.
- Use o título e comentários do Reddit como base — não invente fatos, pesquise na internet para ter mais contexto.
- Escreva como um parágrafo de enciclopédia reescrito por alguém que adora contar histórias.
- Inclua: contexto histórico, como funcionava na prática, detalhes específicos e curiosos,
  consequências ou comparações que ajudem o espectador a visualizar.
- Texto longo o suficiente para o espectador passar 15–20 segundos lendo.
- Termine com uma afirmação conclusiva — sem perguntas, sem convites a comentar.
  Isso é papel do COMMENT, não do STORY.
- Mínimo 4 frases, máximo 7. Máximo {content_cfg['curiosity_max_chars'] * 3} caracteres.

HIGHLIGHTS — Palavras ou expressões que trazem a maior parte do contexto e são as mais relevantes no que você escreveu.
  REGRAS OBRIGATÓRIAS:
  - O PRIMEIRO item deve ser uma palavra ou expressão presente no HOOK que você escreveu, escrita exatamente igual.
  - Os demais (mínimo 2, máximo 5) devem ser palavras ou expressões presentes no STORY que você escreveu, escritas exatamente igual.
    — copie exatamente como escreveu, incluindo acentos e maiúsculas.
  - Escolha: datas, nomes de lugares, números com unidade, nomes próprios que tenham a maior relevância para o contexto.
  - NUNCA inclua somente artigos, preposições ou palavras comuns ("o", "de", "em", "e").
  - Total: mínimo 3 itens, máximo 6 itens.

COMMENT — Apenas 2 frases sobre o assunto. Escreva como uma pessoa real comentando no YouTube e seja criativo.
Imagine que você é alguém que acabou de ler o story e teve uma reação genuína, fazendo correlações para comentários inteligentes.

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

HASHTAGS — 3 a 5 hashtags relevantes.

YOUTUBE_TITLE — Título do Short para o YouTube. Máximo 95 caracteres.
- Deve chamar atenção, usar o hook como base mas pode ser ligeiramente diferente.
- Sempre com 3 hashtags que facilitem o SEO ao final.

YOUTUBE_DESCRIPTION — Descrição do Short, na ordem. Deve ser um parágrafo com 4 ou 5 linhas
- Expansão do hook.
- O que o espectador vai descobrir assistindo.
- As hashtags separadas por espaço no idioma do texto (com #).
- Sem emojis."""

        user_text = f"""{context_block}
Retorne SOMENTE este JSON:
{{
  "hook": "...",
  "story": "...",
  "comment": "...",
  "highlights": ["...", "..."],
  "hashtags": ["...", "..."],
  "youtube_title": "...",
  "youtube_description": "..."
}}"""

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ]

    def _call_groq(self, messages: list[dict], groq_cfg: dict) -> str:
        response = self._client.chat.completions.create(
            model=TEXT_MODEL,
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
            curiosity_text=data.get("hook", "").strip(),
            story_text=data.get("story", "").strip(),
            comment_text=data.get("comment", "").strip(),
            highlights=data.get("highlights", []),
            hashtags=data.get("hashtags", []),
            language=language,
            youtube_title=data.get("youtube_title", "").strip(),
            youtube_description=data.get("youtube_description", "").strip(),
        )