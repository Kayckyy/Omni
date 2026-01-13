# src/renderer.py
"""Módulo responsável por renderizar o projeto OmniAudio a partir de .omni."""

from pathlib import Path
import json
import numpy as np
import soundfile as sf
from typing import Optional

from src.dsp.hrtf_engine import HRTFEngine
from src.dsp.processor import OMNIProcessor
from src.core.omni_format import OMNIFormat
from src.audio_io import load_audio


def render_omni_project(
    omni_path: Path,
    processor: OMNIProcessor,
    output_format: str = "binaural"
) -> Path:
    """Renderiza um projeto .omni para áudio binaural ou multi-speaker."""
    if not omni_path.exists():
        raise FileNotFoundError(f"Arquivo .omni não encontrado: {omni_path}")

    # Carrega dados do .omni
    with open(omni_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    sr = data['sample_rate']
    duration = data['duration']
    master_len = int(duration * sr)
    master_mix = np.zeros((master_len, 2), dtype=np.float32)

    print(f"[Render] Iniciando renderização (modo: {output_format})...")
    print(f"  Duração: {duration:.2f}s | SR: {sr}Hz | Objetos: {len(data['objects'])}")

    for obj in data['objects']:
        obj_name = obj['name']
        obj_file = obj['file']
        role = obj.get('role', 'spatial')
        physics = obj.get('physics', {})

        print(f"  Processando objeto: {obj_name} ({role})")

        # Carrega áudio do objeto
        audio, audio_sr = load_audio(obj_file)
        if audio_sr != sr:
            print(f"    Aviso: SR do objeto {obj_name} ({audio_sr}Hz) != projeto ({sr}Hz)")
            # Aqui poderia resamplear, mas por enquanto assumimos igual

        # Converte pra mono se necessário
        if len(audio.shape) > 1:
            audio = np.mean(audio, axis=1)

        # Processa conforme o formato escolhido
        if output_format == 'cinema_binaural':
            if len(audio.shape) == 1:
                audio = np.stack([audio, audio], axis=1)
            l, r = processor.process_stereo_cinema(audio, sr)
            res = np.stack([l, r], axis=1)

        elif output_format in ['static_binaural', 'static_speaker']:
            if len(audio.shape) == 1:
                audio = np.stack([audio, audio], axis=1)
            l, r = processor.process_stereo_fixed(audio, sr)
            res = np.stack([l, r], axis=1)

        else:  # binaural padrão ou speaker_3d
            if len(audio.shape) > 1:
                audio = np.mean(audio, axis=1)
            l, r = processor.process_object_binaural(audio, sr, obj)
            res = np.stack([l, r], axis=1)

        # Adiciona ao mix (com overlap seguro)
        l_mix = min(len(res), master_len)
        master_mix[:l_mix] += res[:l_mix]

    # Aplicações finais
    if output_format in ['speaker_3d', 'static_speaker']:
        master_mix = processor.apply_xtc(master_mix, sr)

    # Normalização (evita clipping)
    peak = np.max(np.abs(master_mix))
    if peak > 0:
        master_mix /= (peak + 1e-6)

    # Salva saída
    out_name = omni_path.with_name(f"{omni_path.stem}_{output_format}.wav")
    sf.write(str(out_name), master_mix, sr)

    print(f"[Render] Finalizado! Saída salva em: {out_name}")
    return out_name