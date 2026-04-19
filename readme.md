# Shorts Agent 🎬

Gerador automático de YouTube Shorts a partir de vídeos virais.

## Estrutura do projeto

```
shorts_agent/
├── main.py                          # Ponto de entrada (CLI)
├── config.yaml                      # Toda a configuração editável
├── requirements.txt
├── modules/
│   ├── models.py                    # Contratos de dados do pipeline
│   ├── ingestion/
│   │   └── ingestion_module.py      # Download + comentários via yt-dlp
│   ├── intelligence/
│   │   └── intelligence_module.py   # Geração de conteúdo via Groq
│   ├── assets/
│   │   └── assets_module.py         # Validação e prep de assets
│   ├── render/
│   │   ├── render_module.py         # Composição do short final
│   │   └── video_types/
│   │       ├── base.py              # Contrato base (para novos tipos)
│   │       ├── comment_card.py      # Tipo atual: card 3 zonas
│   │       └── __init__.py          # Registry de tipos
│   └── output/
│       └── output_module.py         # Salva mp4 + metadata.json
├── assets/
│   ├── backgrounds/                 # Vídeo de fundo do canal (bg_default.mp4)
│   ├── fonts/                       # Fontes customizadas (opcional)
│   └── profiles/                    # Avatares (avatar_br.png, avatar_en.png)
└── output/
    ├── clips/                       # Trechos baixados
    └── shorts/                      # Shorts finais gerados
```

## Setup

### 1. Instalar dependências de sistema

```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# Mac
brew install ffmpeg
```

### 2. Instalar dependências Python

```bash
pip install -r requirements.txt
```

### 3. Configurar variável de ambiente

```bash
export GROQ_API_KEY=sua_chave_aqui
# Obtenha sua chave gratuita em: https://console.groq.com
```

### 4. Adicionar assets do canal

```bash
# Coloque seu vídeo de fundo (identidade visual do canal):
assets/backgrounds/bg_default.mp4

# Coloque os avatares dos perfis:
assets/profiles/avatar_br.png
assets/profiles/avatar_en.png
```

## Uso

### Geração completa (modo padrão)
```bash
python main.py --url "https://youtube.com/watch?v=SEU_VIDEO"
```

### Com opções customizadas
```bash
python main.py \
  --url "https://youtube.com/watch?v=SEU_VIDEO" \
  --profile FilmFactsEN \
  --max-duration 25 \
  --num-facts 2 \
  --comment-tone humoristico
```

### Testar etapas isoladas (útil para desenvolvimento)
```bash
# Só baixar o vídeo e comentários
python main.py --url "..." --only ingestion

# Só gerar o conteúdo textual (requer ingestion concluída)
python main.py --url "..." --only intelligence

# Só renderizar (requer ingestion + intelligence + assets)
python main.py --url "..." --only render
```

## Parâmetros da CLI

| Parâmetro | Descrição | Default |
|---|---|---|
| `--url` | URL do vídeo de origem | obrigatório |
| `--profile` | Perfil do canal (`config.yaml`) | `CuriosidadesBR` |
| `--video-type` | Tipo de short | `comment_card` |
| `--max-duration` | Duração máxima do trecho (s) | do config.yaml |
| `--clip-start` | Início do trecho no vídeo (s) | do config.yaml |
| `--num-facts` | Nº de fatos na curiosidade | do config.yaml |
| `--comment-tone` | Tom do comentário | do config.yaml |
| `--curiosity-max-chars` | Máx. chars da curiosidade | do config.yaml |
| `--comment-max-chars` | Máx. chars do comentário | do config.yaml |
| `--only` | Executar apenas uma etapa | `all` |

## Adicionar um novo tipo de vídeo (futuro)

1. Crie `modules/render/video_types/meu_tipo.py` herdando de `BaseVideoType`
2. Implemente `type_id`, `compose_frame()` e `get_audio_path()`
3. Adicione no dict `REGISTRY` em `modules/render/video_types/__init__.py`
4. Use com `--video-type meu_tipo`

## Roadmap

- [x] Download de vídeo + comentários (yt-dlp)
- [x] Geração de conteúdo via Groq
- [x] Layout card 3 zonas (curiosidade + clipe + comentário)
- [x] Sistema extensível de tipos de vídeo
- [x] Configuração centralizada via `config.yaml`
- [ ] Remoção de marca d'água
- [ ] Upload automático para YouTube
- [ ] Notificação via Telegram
- [ ] Modo batch (processar lista de URLs)