# src/audio_io.py
"""Módulo para carregar arquivos de áudio em diferentes formatos."""

from pathlib import Path
import numpy as np
import soundfile as sf
from pydub import AudioSegment


def load_audio(path: str) -> tuple[np.ndarray, int]:
    """Carrega áudio de arquivo (WAV, FLAC ou outros via pydub).
    
    Args:
        path: Caminho do arquivo de áudio.
    
    Returns:
        (data: np.ndarray, sr: int) - Áudio como array (mono ou stereo) e sample rate.
    
    Raises:
        FileNotFoundError: Se o arquivo não existir.
        ValueError: Se o formato não for suportado.
    """
    path = Path(path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    ext = path.suffix.lower()

    if ext in ['.wav', '.flac']:
        data, sr = sf.read(str(path))
    else:
        try:
            audio = AudioSegment.from_file(str(path))
            samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
            samples /= float(1 << (8 * audio.sample_width - 1))  # Normaliza
            if audio.channels == 2:
                samples = samples.reshape((-1, 2))
            data, sr = samples, audio.frame_rate
        except Exception as e:
            raise ValueError(f"Erro ao carregar áudio {path}: {e}")

    return data, sr