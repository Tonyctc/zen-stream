# Zen Stream

Gere vídeos de meditação/lofi com **áudio zen procedural** + **fundo fractal animado**. Pipeline 100% automatizada, zero dependências externas (apenas Python puro + ffmpeg).

## Instalação

```bash
git clone https://github.com/Tonyctc/zen-stream.git
cd zen-stream

# Requisitos: Python 3.8+ e ffmpeg
python3 --version
ffmpeg --version
```

## Uso Rápido

```bash
# Teste rápido (10 segundos)
bash quickstart.sh

# 1 hora de zen meditation (720p)
bash quickstart.sh zen

# 8 horas de sono (480p)
bash quickstart.sh sleep

# Loop infinito — gera vídeos para sempre
bash quickstart.sh loop zen
```

## Modos de Operação

### 1. Vídeo único
```bash
# Usando preset
python3 zen_stream.py --preset zen

# Configuração manual
python3 zen_stream.py -d 3600 -r 720p -t julia -p aurora -m meditation
```

### 2. Batch (múltiplos vídeos)
```bash
# Gerar config de exemplo
python3 zen_stream.py --sample-config

# Editar presets.json e executar
python3 zen_stream.py --batch presets.json
```

### 3. Loop infinito
```bash
# Gerar vídeos para sempre (Ctrl+C para parar)
python3 zen_stream.py --loop --preset zen
```

### 4. Apenas áudio ou vídeo
```bash
python3 zen_stream.py --audio-only -d 3600 -m sleep
python3 zen_stream.py --video-only -d 3600 -t julia -p zen
```

## Áudio v2 — O que mudou

O gerador de áudio foi completamente reescrito. Resultado: áudio profissional que não parece "sintético".

| Recurso | v1 (antes) | v2 (agora) |
|---|---|---|
| Canais | Mono | **Estéreo** com largura espacial |
| Reverb | Nenhuma | **Schroeder** (4 comb + 2 allpass) |
| Ondas | Senoide pura | **Warm saw, triangle, FM, vibrato** |
| Binaural | Não | **Sim** — delta/theta/alpha por modo |
| Filtros | 1-pole básico | **Biquad LP com ressonância** |
| Efeitos | Nenhum | **Chorus estéreo** |
| Sinos | Harmônicos simples | **Singing bowls com parciais inarmônicos** |
| Natureza | Vento+ruido | **Vento + chuva + gotas com pitch glide** |
| Afinação | 440Hz fixo | **432Hz padrão** (configurável) |

### Binaural beats por modo
| Modo | Frequência | Efeito |
|---|---|---|
| meditation | 6Hz (Theta) | Relaxamento profundo |
| sleep | 2Hz (Delta) | Sono profundo |
| focus | 10Hz (Alpha) | Concentração alerta |
| nature | 7.83Hz | Ressonância Schumann |

## Presets

| Preset | Fractal | Paleta | Áudio | Resolução | Duração |
|---|---|---|---|---|---|
| `zen` | julia | zen | meditation | 720p | 1h |
| `sleep` | plasma | ocean | sleep | 480p | 8h |
| `focus` | mandelbrot | ember | focus | 720p | 2h |
| `aurora` | julia | aurora | meditation | 1080p | 1h |
| `nature` | plasma | zen | nature | 720p | 1h |

## Parâmetros

### Orquestrador (`zen_stream.py`)
```
--preset          Usar preset predefinido
--batch CONFIG    Gerar múltiplos vídeos de um JSON
--loop            Gerar vídeos infinitamente
--sample-config   Criar presets.json de exemplo
-d, --duration    Duração em segundos
-r, --resolution  Resolução (240p/360p/480p/720p/1080p)
-t, --type        Fractal (julia/mandelbrot/plasma)
-p, --palette     Paleta (zen/aurora/ember/ocean)
-m, --mode        Áudio (meditation/sleep/focus/nature)
--tuning          Frequência base em Hz (padrão: 432)
-i, --iterations  Máx iterações do fractal
--audio-only      Gerar apenas áudio
--video-only      Gerar apenas vídeo
--keep-frames     Manter frames PPM intermediários
```

## Estrutura do Projeto

```
zen-stream/
├── zen_audio.py               # Gerador de áudio procedural v2
├── fractal_video.py           # Gerador de frames fractais (PPM)
├── zen_stream.py              # Orquestrador principal
├── quickstart.sh              # Launcher rápido
├── zen_fractal.effect.hlsl    # Shader HLSL para OBS
├── setup_obs.md               # Guia de configuração do OBS
├── obs_scene.json             # Config de scene do OBS
├── upload_youtube.py          # Upload YouTube (TODO v2.0)
├── README.md                  # Este arquivo
├── LICENSE                    # MIT License
└── output/                    # Vídeos gerados (gitignored)
```

## Performance

| Resolução | Velocidade | 1 min de vídeo |
|---|---|---|
| 240p | ~8 fps | ~3 min |
| 480p | ~3 fps | ~8 min |
| 720p | ~1.5 fps | ~16 min |
| 1080p | ~0.5 fps | ~48 min |

## OBS (Live 24/7 no YouTube)

Para fazer lives com shader fractal ao vivo, veja o guia em [setup_obs.md](setup_obs.md).

## Custo

**R$ 0** — Tudo roda 100% local. Sem APIs, sem dependências pagas.

---

## Roadmap

### v1.0 — Completo
- [x] Gerador de áudio zen procedural
- [x] Gerador de vídeo fractal (Julia, Mandelbrot, Plasma)
- [x] Orquestrador com presets
- [x] Modo batch (múltiplos vídeos)
- [x] Modo loop infinito
- [x] Suporte a ffmpeg para composição automática
- [x] Shader HLSL para OBS

### v1.5 — Áudio v2 (atual)
- [x] Reverb Schroeder (comb + allpass)
- [x] Áudio estéreo com chorus
- [x] Binaural beats (delta/theta/alpha)
- [x] Ondas ricas (warm saw, FM, vibrato)
- [x] Singing bowls com parciais inarmônicos
- [x] Camada de chuva + gotas com pitch glide
- [x] Afinação 432Hz (configurável via --tuning)

### v2.0 — Próxima versão
- [ ] **Upload automático para YouTube** via YouTube Data API v3
- [ ] Autenticação OAuth 2.0 persistente
- [ ] Agendamento automático (cron integration)
- [ ] Thumbnails gerados por IA
- [ ] Títulos/descrições gerados por IA
- [ ] Suporte a TikTok e Instagram (via APIs)

### v3.0 — Futuro
- [ ] Geração com GPU (OpenGL/CUDA)
- [ ] Suporte a mais tipos de fractal (Burning Ship, Tricorn)
- [ ] Editor visual de presets
- [ ] Dashboard de monitoramento
- [ ] Multi-canal simultâneo
