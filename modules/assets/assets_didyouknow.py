"""
assets/assets_didyouknow.py — Busca imagens em Pexels, Unsplash e Pixabay para Did You Know.

Cascata: consulta os três em paralelo e combina os resultados.
Variáveis de ambiente necessárias (pelo menos uma):
  PEXELS_API_KEY   — pexels.com/api
  UNSPLASH_ACCESS_KEY — unsplash.com/developers
  PIXABAY_API_KEY  — pixabay.com/api/docs
"""
import json
import logging
import os
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class DYKAssetsModule:

    def __init__(self):
        self._pexels    = os.environ.get("PEXELS_API_KEY", "")
        self._unsplash  = os.environ.get("UNSPLASH_ACCESS_KEY", "")
        self._pixabay   = os.environ.get("PIXABAY_API_KEY", "")

        active = [k for k, v in [("Pexels", self._pexels), ("Unsplash", self._unsplash), ("Pixabay", self._pixabay)] if v]
        if not active:
            logger.warning("[DYKAssets] Nenhuma API key de imagens configurada.")
        else:
            logger.info(f"[DYKAssets] Fontes ativas: {', '.join(active)}")

    # ── Busca combinada ────────────────────────────────────────────────────────

    def search(self, query: str, per_source: int = 3) -> list[str]:
        """Busca nos três serviços em paralelo e retorna URLs combinadas."""
        tasks = []
        if self._pexels:   tasks.append(("pexels",   self._search_pexels))
        if self._unsplash: tasks.append(("unsplash", self._search_unsplash))
        if self._pixabay:  tasks.append(("pixabay",  self._search_pixabay))

        if not tasks:
            return []

        results: list[str] = []
        with ThreadPoolExecutor(max_workers=len(tasks)) as pool:
            futures = {pool.submit(fn, query, per_source): name for name, fn in tasks}
            for future in as_completed(futures):
                name = futures[future]
                try:
                    urls = future.result()
                    results.extend(urls)
                    logger.info(f"[DYKAssets] {name}: {len(urls)} resultado(s) para '{query}'")
                except Exception as e:
                    logger.warning(f"[DYKAssets] {name} falhou para '{query}': {e}")

        return results

    def search_all(self, queries: list[str], per_source: int = 3) -> list[list[str]]:
        """Busca imagens para cada query."""
        return [self.search(q, per_source) for q in queries]

    # ── Pexels ────────────────────────────────────────────────────────────────

    def _search_pexels(self, query: str, per_page: int) -> list[str]:
        url = (
            f"https://api.pexels.com/v1/search"
            f"?query={urllib.parse.quote(query)}"
            f"&per_page={per_page}&orientation=portrait"
        )
        req = urllib.request.Request(url, headers={
            "Authorization": self._pexels,
            "User-Agent": "shorts-agent/1.0",
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        return [p["src"]["large"] for p in data.get("photos", [])]

    # ── Unsplash ──────────────────────────────────────────────────────────────

    def _search_unsplash(self, query: str, per_page: int) -> list[str]:
        url = (
            f"https://api.unsplash.com/search/photos"
            f"?query={urllib.parse.quote(query)}"
            f"&per_page={per_page}&orientation=portrait"
        )
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Client-ID {self._unsplash}"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        return [p["urls"]["regular"] for p in data.get("results", [])]

    # ── Pixabay ───────────────────────────────────────────────────────────────

    def _search_pixabay(self, query: str, per_page: int) -> list[str]:
        url = (
            f"https://pixabay.com/api/"
            f"?key={urllib.parse.quote(self._pixabay)}"
            f"&q={urllib.parse.quote(query)}"
            f"&image_type=photo&orientation=vertical"
            f"&per_page={per_page}&safesearch=true"
        )
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
        return [h["largeImageURL"] for h in data.get("hits", [])]
