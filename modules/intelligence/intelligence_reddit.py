"""
intelligence/intelligence_reddit.py — Gera hook, story e comentário para Reddit (imagem e vídeo).

A única diferença entre os dois modos é a chamada ao Groq:
  - mode="image": envia a imagem como base64 (vision model)
  - mode="video": envia só título + comentários como texto (text model)

Devolve sempre um GeneratedContent com os mesmos campos.
"""
import base64
import json
import logging
import os
import re
from pathlib import Path
from typing import Literal, Union

from groq import Groq
from dotenv import load_dotenv

from modules.models import GeneratedContent, ImageSource, VideoSource, PipelineContext

load_dotenv()
logger = logging.getLogger(__name__)

VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
TEXT_MODEL   = "llama-3.3-70b-versatile"

Mode = Literal["image", "video"]

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
    "assustado":   "O comentário deve soar com medo ou receio"
}


class RedditIntelligenceModule:

    def __init__(self):
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError("GROQ_API_KEY não encontrada.")
        self._client = Groq(api_key=api_key)

    def run(
        self,
        ctx: PipelineContext,
        source: Union[ImageSource, VideoSource],
        mode: Mode,
    ) -> GeneratedContent:
        profile     = ctx.config["profiles"][ctx.profile_name]
        content_cfg = ctx.config["content"]
        groq_cfg    = ctx.config["groq"]
        language    = profile["language"]
        niche       = profile["niche"]

        title = source.title if hasattr(source, "title") else ""
        logger.info(f"[Intelligence] Gerando conteúdo para: {title[:60]}")

        system_prompt = self._build_system_prompt(content_cfg, profile, language, niche)

        if mode == "image":
            assert isinstance(source, ImageSource)
            messages = self._build_image_messages(system_prompt, source, content_cfg)
            response_text = self._call_groq(messages, groq_cfg, model=VISION_MODEL)
        else:
            assert isinstance(source, VideoSource)
            messages = self._build_video_messages(system_prompt, source, content_cfg)
            response_text = self._call_groq(messages, groq_cfg, model=TEXT_MODEL)

        content = self._parse_response(response_text, language)
        logger.info(f"[Intelligence] Hook: {content.curiosity_text[:60]}...")
        logger.info(f"[Intelligence] Comentário: {content.comment_text[:60]}...")
        return content

    # ── System prompt (igual para ambos os modos) ─────────────────────────────

    def _build_system_prompt(self, content_cfg: dict, profile, language: str, niche: str) -> str:
        lang_instruction = _LANGUAGE_INSTRUCTIONS.get(language, _LANGUAGE_INSTRUCTIONS["pt-BR"])
        tone_instruction = _TONE_INSTRUCTIONS.get(profile["comment_tone"], _TONE_INSTRUCTIONS["surpreso"])

        return f"""Você é um roteirista de YouTube Shorts virais no nicho de {niche}.
{lang_instruction}
Sua única saída é um objeto JSON válido, sem texto antes ou depois, sem markdown, não use triplas aspas.

Você gera conteúdo para um short de 45–60 segundos. 
Você faz buscas na internet em fontes confiáveis para adicionar informação.
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

STORY — A história por trás da imagem. Informativo, denso, envolvente.
- Use o título e comentários do Reddit como base — não invente fatos, pesquise na internet para ter mais contexto.
- Escreva como um parágrafo de enciclopédia reescrito por alguém que adora contar histórias.
- Inclua: contexto histórico, como funcionava na prática, detalhes específicos e curiosos,
  consequências ou comparações que ajudem o espectador a visualizar.
- Texto longo o suficiente para o espectador passar 15–20 segundos lendo.
- Termine com uma afirmação conclusiva — sem perguntas, sem convites a comentar.
  Isso é papel do COMMENT, não do STORY.
- Mínimo 4 frases, máximo 7.

HIGHLIGHTS — Palavras ou expressões que trazem a maior parte do contexto e são as mais relevantes no que você escreveu.
  REGRAS OBRIGATÓRIAS:
  - O PRIMEIRO item deve ser uma palavra ou expressão presente no HOOK que você escreveu, escrita exatamente igual.
  - Os demais (mínimo 2, máximo 5) devem ser palavras ou expressões presentes no STORY que você escreveu, escritas exatamente igual.
    — copie exatamente como escreveu, incluindo acentos e maiúsculas.
  - Escolha: datas, nomes de lugares, números com unidade, nomes próprios que tenham a maior relevância para o contexto.
  - NUNCA inclua somente artigos, preposições ou palavras comuns ("o", "de", "em", "e").
  - Total: mínimo 6 itens, máximo 8.

COMMENT — Apenas 2 frases sobre o assunto. Escreva como uma pessoa real comentando no YouTube e seja criativo.
Imagine que você é alguém que acabou de ler o story e teve uma reação genuína, fazendo correlações para comentários inteligentes.
- Não faça comentários genéricos! O comentário deve acrescentar o seu ponto de vista sobre o assunto.

- Frase 1: reação direta e específica ao conteúdo — humor, ironia ou espanto natural.
  Sempre use um fato curioso que não foi dito no STORY, afim de adicionar ainda mais informação. 
  Use uma busca na internet se for preciso. 

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

HASHTAGS — 3 a 5 hashtags relevantes, com o caractere #.

YOUTUBE_TITLE — Título do Short para o YouTube. Máximo 95 caracteres.
- Deve chamar atenção, usar o hook como base mas pode ser ligeiramente diferente.
- Sempre com 3 hashtags que facilitem o SEO ao final.

YOUTUBE_DESCRIPTION — Descrição do Short, na ordem. Deve ser um parágrafo com 4 ou 5 linhas
- Expansão do hook.
- O que o espectador vai descobrir assistindo.
- As hashtags separadas por espaço no idioma do texto (com #).
- Sem emojis."""

    # ── Mensagens por modo ────────────────────────────────────────────────────

    def _build_image_messages(
        self, system_prompt: str, source: ImageSource, content_cfg: dict
    ) -> list[dict]:
        image_b64  = base64.standard_b64encode(source.image_path.read_bytes()).decode()
        media_type = {
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".png": "image/png",  ".webp": "image/webp",
            ".gif": "image/gif",
        }.get(source.image_path.suffix.lower(), "image/jpeg")

        context_block = ""
        if source.title:
            context_block += f'Título do post: "{source.title}"\n'
        if source.context_comments:
            context_block += "Comentários reais:\n"
            context_block += "\n".join(f"  - {c}" for c in source.context_comments[:5])
            context_block += "\n"

        user_text = f"""{context_block}
Analise a imagem e gere o conteúdo seguindo exatamente as regras do sistema.

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
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{image_b64}"}},
                    {"type": "text", "text": user_text},
                ],
            },
        ]

    def _build_video_messages(
        self, system_prompt: str, source: VideoSource, content_cfg: dict
    ) -> list[dict]:
        context_block = f'Título do post: "{source.title}"\n'
        if source.channel_name:
            context_block += f'Subreddit: {source.channel_name}\n'
        if source.comments:
            context_block += "Comentários reais:\n"
            context_block += "\n".join(f"  - {c}" for c in source.comments[:5])
            context_block += "\n"

        user_text = f"""{context_block}
Gere o conteúdo com base no título e comentários acima.

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

    # ── Groq call ─────────────────────────────────────────────────────────────

    def _call_groq(self, messages: list[dict], groq_cfg: dict, model: str) -> str:
        response = self._client.chat.completions.create(
            model=model,
            temperature=groq_cfg["temperature"],
            max_tokens=groq_cfg["max_tokens"],
            messages=messages,
        )
        return response.choices[0].message.content.strip()

    # ── Parse ─────────────────────────────────────────────────────────────────

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
            highlights=data.get("highlights", []),
            hashtags=data.get("hashtags", []),
            language=language,
            youtube_title=data.get("youtube_title", "").strip(),
            youtube_description=data.get("youtube_description", "").strip(),
        )