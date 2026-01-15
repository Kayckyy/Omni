# OmniAudio

**A powerful free and open-source program that uses Impulse Responses to generate a 3D space and manipulate sounds around your head.**

Compatible with headphones, speakers and surround setups.

![Demo GIF ou screenshot - adicione depois](demo.gif) <!-- Se tiver GIF/screenshot, coloque aqui -->

## O que é o OmniAudio?

OmniAudio transforma qualquer áudio (música, filme, jogo, podcast) em uma experiência espacial 3D usando **HRTFs (Head-Related Transfer Functions)** de alta qualidade (SADIE II com 9201 direções).

Você pode:
- Posicionar sons em qualquer direção ao redor da cabeça (azimute + elevação)
- Criar trajetórias de movimento (procedural ou keyframes)
- Renderizar para binaural (fones), cinema binaural, estéreo fixo ou multi-speaker (5.1/7.1 com XTC)
- Extrair áudio de vídeos e muxar o resultado de volta

## Recursos atuais

- Suporte a HRTFs SADIE II (ou qualquer set de IRs compatível)
- Separação de stems (placeholder para Demucs/UVR)
- Criação e edição de arquivos .omni (presets de posições + keyframes)
- Renderização offline para WAV/MP3
- Interface gráfica com visualizador 3D interativo (drag & drop)
- Modo CLI para automação

## Instalação

### Pré-requisitos

- Python 3.8+
- ffmpeg (instalado no sistema)

### Passo a passo

```bash
# Clone o repositório
git clone https://github.com/Kayckyy/OmniAudio.git
cd OmniAudio

# Instale as dependências
pip install -r requirements.txt

# (Opcional) modo editável
pip install -e .
```

# Executar

Abre a interface gráfica
```
python main.py gui

```

# Ou modos CLI
```
python main.py auto "meu_video.mp4"
python main.py process_multi "projeto.omni" --format binaural
```
# Como usar
• Importar uma faixa ou vídeo na aba "Importar"

• Gerar o arquivo .omni

• Customizar posições, trajetórias e keyframes na aba "Customizar"

• Renderizar na aba "Renderizar" (escolha o formato desejado)

# Contribua
Reporte bugs → Issues

Sugira features ou envie pull requests

Compartilhe com amigos que curtem áudio espacial
Licença

MIT License - veja LICENSE

# Agradecimentos
SADIE II HRTF dataset
Bibliotecas: numpy, scipy, soundfile, pydub, PyQt5, pyqtgraph, PyOpenGL
