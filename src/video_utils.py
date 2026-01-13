# src/video_utils.py
"""Utilitários para extração, separação e muxing de áudio/vídeo usando ffmpeg."""

from pathlib import Path
import subprocess
import soundfile as sf
from typing import List, Dict, Optional

VIDEO_EXTENSIONS = ('.mp4', '.mkv', '.mov', '.avi', '.flv', '.wmv', '.webm')


def is_video_file(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXTENSIONS


def extract_audio_from_video(video_path: str) -> str:
    """Extrai áudio de vídeo para WAV 44.1kHz."""
    video_path = Path(video_path).resolve()
    if not is_video_file(video_path):
        return str(video_path)  # Já é áudio

    output_wav = video_path.with_suffix(".extracted.wav")

    # Detecta número de canais
    probe = subprocess.run(
        ['ffprobe', '-v', 'error', '-select_streams', 'a:0',
         '-show_entries', 'stream=channels', '-of', 'csv=p=0', str(video_path)],
        capture_output=True, text=True, check=False
    )
    channels = int(probe.stdout.strip()) if probe.stdout.strip() else 2

    cmd = [
        'ffmpeg', '-i', str(video_path),
        '-vn', '-acodec', 'pcm_s16le', '-ar', '44100',
        str(output_wav), '-y'
    ]
    if channels <= 2:
        cmd.extend(['-ac', '2'])

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Erro ao extrair áudio: {e.stderr.decode().strip()}")

    return str(output_wav)


def split_multichannel(wav_path: str, output_dir: Path) -> Optional[List[Dict[str, str]]]:
    """Separa áudio multi-channel em arquivos mono por canal."""
    wav_path = Path(wav_path)
    info = sf.info(str(wav_path))

    if info.channels <= 2:
        return None

    layout = ["FL", "FR", "FC", "LFE", "SL", "SR", "BL", "BR"][:info.channels]
    stems = []

    for i, name in enumerate(layout):
        ch_file = output_dir / f"{name}.wav"
        cmd = [
            'ffmpeg', '-i', str(wav_path),
            '-af', f'pan=mono|c0=c{i}',
            str(ch_file), '-y'
        ]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            stems.append({"name": name, "file": str(ch_file)})
        except subprocess.CalledProcessError as e:
            print(f"Aviso: Falha ao separar canal {name}: {e}")

    return stems if stems else None


def merge_audio_to_video(video_path: str, audio_3d_path: str) -> None:
    """Muxa áudio binaural/3D de volta no vídeo original."""
    video_path = Path(video_path)
    audio_path = Path(audio_3d_path)
    output_video = video_path.with_name(video_path.stem + "_Omni_3D.mp4")

    cmd = [
        'ffmpeg',
        '-i', str(video_path),
        '-i', str(audio_path),
        '-c:v', 'copy',
        '-map', '0:v:0',
        '-map', '1:a:0',
        '-c:a', 'aac',
        '-b:a', '320k',
        '-movflags', '+faststart',
        str(output_video),
        '-y'
    ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        print(f"✅ Vídeo final gerado: {output_video}")
        # Limpeza
        audio_path.unlink(missing_ok=True)
        extracted = video_path.with_suffix(".extracted.wav")
        extracted.unlink(missing_ok=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao muxar vídeo: {e.stderr.decode().strip()}")