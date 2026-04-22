"""
assets/assets_didyouknow.py — Busca imagens no Pexels para Did You Know.
"""
import json
import logging
import os
import urllib.parse
import urllib.request

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

PEXELS_API = "https://api.pexels.com/v1/search"


class DYKAssetsModule:

    def __init__(self):
        self._key = os.environ.get("PEXELS_API_KEY", "")
        if not self._key:
            logger.warning("[DYKAssets] PEXELS_API_KEY não encontrada — buscas retornarão vazias.")

    def search(self, query: str, per_page: int = 3) -> list[str]:
        """Retorna até per_page URLs de imagens portrait do Pexels."""
        if not self._key:
            return []
        url = f"{PEXELS_API}?query={urllib.parse.quote(query)}&per_page={per_page}&orientation=portrait"
        req = urllib.request.Request(url, headers={"Authorization": self._key})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
            return [p["src"]["large"] for p in data.get("photos", [])]
        except Exception as e:
            logger.warning(f"[DYKAssets] Pexels search falhou para '{query}': {e}")
            return []

    def search_all(self, queries: list[str], per_page: int = 3) -> list[list[str]]:
        """Busca imagens para cada query em sequência."""
        return [self.search(q, per_page) for q in queries]
