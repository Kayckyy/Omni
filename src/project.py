# src/project.py
"""Gerenciamento de projetos OmniAudio: pastas temporárias e criação de .omni."""

from pathlib import Path
import os
from typing import List, Dict
from src.core.omni_format import OMNIFormat  # Ajuste o import conforme sua estrutura
import soundfile as sf


def create_project_directory(audio_path: str) -> Path:
    """Cria pasta temporária para o projeto baseada no nome do arquivo."""
    audio_path = Path(audio_path)
    proj_name = audio_path.stem.replace("_extracted", "")
    proj_dir = Path("temp") / proj_name

    proj_dir.mkdir(parents=True, exist_ok=True)
    return proj_dir


def create_omni_file(
    stems: List[Dict[str, str]],
    audio_path: str,
    proj_dir: Path,
    is_surround: bool = False,
    seed: str = None,
    keyframes: list = None
) -> Path:
    """Cria arquivo .omni para o projeto."""
    audio_path = Path(audio_path)
    info = sf.info(str(audio_path))

    omni_path = proj_dir / f"{proj_dir.name}.omni"

    OMNIFormat.create_multi_stem_omni(
        stems_list=stems,
        duration=info.duration,
        sr=info.samplerate,
        path=str(omni_path),
        is_surround=is_surround,
        seed=seed,
        keyframes=keyframes or []
    )

    return omni_path