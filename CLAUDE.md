# shorts-creator-agent — CLAUDE.md

## Sobre o projeto

Agente para criação automatizada de vídeos curtos (Shorts/Reels).
Repositório: `Hadamanthis/shorts-agent`
Caminho local: `C:\Users\geova\VSCode Projects\shorts-creator-agent`

---

## Stack

| Camada | Tecnologia |
|---|---|
| Backend | Python · FastAPI (`api.py`) |
| Pipeline | módulos em `modules/` |
| Frontend | React + TypeScript · Vite standalone |
| Renderização | Remotion (`video-renderer/`) |
| LLM | Groq — `llama-3.3-70b-versatile` (texto) · `llama-4-scout` (visão) |
| Imagens | Pexels + Unsplash + Pixabay (cascata paralela) |

---

## Como rodar

```bash
# Backend (FastAPI)
uvicorn api:app --reload

# Frontend (React standalone)
cd video-renderer
npm run ui          # → http://localhost:5173

# Render de vídeo (Remotion)
cd video-renderer
npx remotion render
```

---

## Arquitetura

```
shorts-creator-agent/
├── api.py                         # Todos os endpoints REST
├── main.py                        # Entry point CLI
├── config.yaml                    # Perfis de configuração
├── modules/
│   ├── models.py
│   ├── assets/
│   │   └── assets_didyouknow.py   # Cascata Pexels+Unsplash+Pixabay
│   ├── intelligence/
│   │   ├── intelligence_module.py
│   │   ├── intelligence_didyouknow.py   # Geração de fatos DYK
│   │   ├── intelligence_reddit.py
│   │   ├── image_intelligence_module.py
│   │   └── video_intelligence_module.py
│   ├── ingestion/
│   ├── output/
│   └── render/
└── video-renderer/
    └── src/
        ├── templates/
        │   ├── DidYouKnow.tsx         # Template principal DYK
        │   ├── ComentarioImagem.tsx
        │   ├── ComentarioVideo.tsx
        │   └── Curiosidade.tsx
        └── ui/
            ├── AppRouter.tsx          # Routing + estado global curationConfig
            ├── standalone.tsx         # Entry point Vite
            └── pages/
                ├── DashboardPage.tsx
                ├── CurationPage.tsx   # Curadoria drag-and-drop DYK
                ├── ShortsPage.tsx
                └── ConfigPage.tsx
```

---

## Templates implementados

### DidYouKnow (DYK)
- Fluxo: tópico → `intelligence_didyouknow.py` → fatos narrativos → curadoria UI → render `DidYouKnow.tsx`
- Ken Burns no fundo, progress bar, texto palavra-a-palavra, "VOCÊ SABIA?" grande, perfil no topo
- UI: drag-and-drop, seletor de música, numCards configurável

### Comentário
- `comentario-reddit` / `comentario-assets` / `comentario-youtube` — fluxo existente

---

## Endpoints da API

| Método | Rota | Descrição |
|---|---|---|
| POST | `/dyk/generate` | Gera fatos DYK para um tópico |
| POST | `/dyk/render` | Renderiza vídeo DidYouKnow |
| GET | `/music` | Lista músicas disponíveis |

---

## Decisões arquiteturais confirmadas

1. **Home screen** — cards visuais por template (substituir `DashboardPage` atual); cada template tem sua própria página dedicada
2. **Top bar** — seletor de perfil global + acesso a configurações de perfil editáveis
3. **Vídeo nos cards DYK** — vídeo local (`assets/videos/`) substitui imagem estática como fundo
4. **CTA por perfil** — campo `cta_video_path` no perfil em `config.yaml`; vídeo pré-renderizado concatenado automaticamente ao final
5. **Storage cleanup** — limpeza automática de `public/dyk_img_*` após render + botão "limpar cache" na UI
6. **Automação máxima** — se o software puder fazer algo automaticamente, deve fazer

---

## Tarefas pendentes

- [x] Home screen com template cards
- [x] Top bar com profile selector global
- [x] Vídeo nos cards DYK (pasta `assets/videos/`) — drag "video:filename" → slot
- [x] CTA video por perfil (`cta_video_path` no config)
- [x] Storage cleanup (automático pós-render + botão na UI)
- [x] Endpoint `GET /videos` para listar vídeos em `assets/videos/`

---

## Convenções de commit

- Commits em português, prefixo semântico: `feat:`, `fix:`, `refactor:`, `chore:`
- **Não incluir** linha `Co-Authored-By: Claude` nas mensagens de commit
- **Sempre** após qualquer alteração no código, fazer commit e `git push` imediatamente

---

## Estilo de código

- React: inline styles com objetos `Record<string, React.CSSProperties>` (padrão `s`, `sq`, `pl`)
- TypeScript strict — sempre verificar com `npx tsc --noEmit` antes de commitar
- Python: FastAPI, async quando possível, tipagem com Pydantic
