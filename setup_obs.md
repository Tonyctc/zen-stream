# OBS Setup Guide — Zen Stream

## Quick Setup (5 minutos)

### Requisitos
- **OBS Studio** instalado (https://obsproject.com/)
- **obs-shadertastic** plugin (https://github.com/xurei/obs-shadertastic)
- Vídeo MP4 gerado pelo `zen_stream.py` OU shader ao vivo

---

## Método 1: Usar vídeo MP4 gerado (mais simples)

### Passo 1: Gerar o vídeo
```bash
# No terminal (WSL ou Linux/Mac)
cd zen-stream
python3 zen_stream.py -d 3600 -r 1080p -t julia -p zen -m meditation
```
Isso gera `output/zen_julia_zen.mp4` (1 hora de vídeo com áudio).

### Passo 2: Configurar OBS
1. Abrir OBS
2. Criar nova cena: **Scene Collection → New → "Zen Stream"**
3. Adicionar source:
   - **+ → Media Source**
   - Name: `Zen Video`
   - Local File: selecionar o MP4 gerado
   - ✅ Loop
   - ✅ Restart playback when source becomes active
4. Configurar áudio:
   - O áudio já está embutido no MP4
   - Settings → Audio → Desktop Audio → habilitar

### Passo 3: Configurar stream
1. **Settings → Stream**
   - Service: YouTube - RTMP
   - Stream Key: (sua chave do YouTube)
2. **Settings → Video**
   - Base Resolution: 1920x1080
   - Output Resolution: 1920x1080
   - FPS: 30
3. **Settings → Output → Streaming**
   - Encoder: x264 (ou NVENC se tiver GPU NVIDIA)
   - Bitrate: 4500 Kbps
   - Audio Bitrate: 128

### Passo 4: Iniciar stream
Clicar **Start Streaming**

---

## Método 2: Shader ao vivo (sem pré-gerar vídeo)

Este método renderiza o fractal em tempo real no OBS.

### Passo 1: Instalar obs-shadertastic
1. Baixar de: https://github.com/xurei/obs-shadertastic/releases
2. Extrair na pasta de plugins do OBS:
   - Windows: `%APPDATA%/obs-studio/plugins/`
   - Linux: `~/.config/obs-studio/plugins/`

### Passo 2: Criar o shader
1. Copiar o arquivo `zen_fractal.effect.hlsl` para:
   ```
   <OBS config>/obs-shadertastic/effects/
   ```

### Passo 3: Configurar OBS
1. **Criar nova cena**: "Fractal Live"
2. **Adicionar Source → Color Source**
   - Name: "Fractal Base"
   - Color: qualquer cor (será substituída pelo shader)
3. **Adicionar filtro**:
   - Clicar com botão direito na source → Filters
   - + → Shadertastic Filter
   - Selecionar "Zen Fractal"
   - Ajustar parâmetros:
     - **Speed**: 0.2-0.5 (velocidade da animação)
     - **Complexity**: 0.5-1.0 (detalhe do fractal)
     - **Color Shift**: 0.0-1.0 (variação de cor)

### Passo 4: Adicionar áudio
1. **Source → Media Source**
   - Name: "Zen Audio"
   - Local File: `output/zen_meditation.wav`
   - ✅ Loop

---

## Método 3: Automação total com script

Para automatizar completamente a geração + upload:

### Script de upload para YouTube (requer YouTube API)
```python
# upload_youtube.py (exemplo conceitual)
# Requer: pip install google-api-python-client

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def upload_video(file_path, title, description, tags):
    youtube = build('youtube', 'v3', developerKey='YOUR_API_KEY')
    
    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': tags,
            'categoryId': '10'  # Music
        },
        'status': {
            'privacyStatus': 'public',
            'selfDeclaredMadeForKids': False
        }
    }
    
    media = MediaFileUpload(file_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(
        part='snippet,status',
        body=body,
        media_body=media
    )
    response = request.execute()
    print(f"Uploaded: https://youtube.com/watch?v={response['id']}")
```

### Agendamento automático (cron)
```bash
# Gerar e fazer upload 1x por dia às 6h da manhã
0 6 * * * cd /home/user/zen-stream && python3 zen_stream.py -d 3600 -r 1080p && python3 upload_youtube.py
```

---

## Dicas

### Para lives 24/7
- Use o **Método 2** (shader ao vivo) — não precisa gerar nada previamente
- Configure o áudio para loop infinito
- Use o plugin **obs-ndi** para reduzir uso de CPU

### Para uploads periódicos
- Gere vídeos de 1-8 horas com `zen_stream.py`
- Faça upload via YouTube API ou manualmente
- Canal de "lofi beats" ou "meditation music" funciona bem

### Otimização de CPU
- 240p/360p para testes
- 480p para YouTube (bom custo-benefício)
- 720p/1080p para qualidade profissional
- Reduza `--iterations` para 30-50 para render mais rápido

### Variações de estilo
```bash
# Oceano calmo
python3 zen_stream.py -t plasma -p ocean -m sleep

# Aurora boreal
python3 zen_stream.py -t julia -p aurora -m meditation

# Embers/fogueira
python3 zen_stream.py -t mandelbrot -p ember -m focus

# Profundezas
python3 zen_stream.py -t julia -p zen -m nature
```
