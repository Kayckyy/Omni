# src/core/omni_format.py
"""Formato .omni para armazenar configurações de objetos espaciais."""

import json
import random
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional


class OMNIFormat:
    """Classe estática para criação e manipulação de arquivos .omni."""

    SURROUND_MAP = {
        "FL":  {"azi": 30,  "role": "spatial"},
        "FR":  {"azi": 330, "role": "spatial"},
        "FC":  {"azi": 0,   "role": "anchor"},
        "LFE": {"azi": 0,   "role": "lfe_focused"},
        "SL":  {"azi": 110, "role": "spatial"},
        "SR":  {"azi": 250, "role": "spatial"},
        "BL":  {"azi": 150, "role": "spatial"},
        "BR":  {"azi": 210, "role": "spatial"}
    }

    @staticmethod
    def _detect_role(name: str) -> str:
        name = name.lower()
        if any(kw in name for kw in ['vocal', 'voice', 'voz', 'lead', 'dialog', 'fc']):
            return 'anchor'
        if any(kw in name for kw in ['bass', 'baixo', 'kick', 'sub', '808', 'lfe']):
            return 'lfe_focused'
        if any(kw in name for kw in ['air', 'pad', 'ambience', 'noise', 'fx', 'atm']):
            return 'ethereal'
        return 'spatial'

    @staticmethod
    def _generate_seed(input_str: Optional[str] = None) -> str:
        if input_str:
            return hashlib.md5(input_str.encode()).hexdigest()[:16]
        return hashlib.md5(str(random.random()).encode()).hexdigest()[:16]

    @staticmethod
    def create_multi_stem_omni(
        stems_list: List[Dict[str, str]],
        duration: float,
        sr: int,
        path: str | Path,
        is_surround: bool = False,
        seed: Optional[str] = None,
        keyframes: Optional[List[Dict]] = None
    ) -> str:
        """Cria arquivo .omni com configuração de objetos."""
        path = Path(path)
        seed = seed or OMNIFormat._generate_seed()
        keyframes = keyframes or []

        data: Dict[str, Any] = {
            "version": "5.1 (Enhanced with Keyframes)",
            "created_at": datetime.now().isoformat(),
            "seed": seed,
            "duration": duration,
            "sample_rate": sr,
            "keyframes": keyframes,
            "objects": []
        }

        random.seed(seed)

        for stem in stems_list:
            name_key = stem['name'].upper()
            role = OMNIFormat.SURROUND_MAP[name_key]['role'] if is_surround and name_key in OMNIFormat.SURROUND_MAP else OMNIFormat._detect_role(stem['name'])

            if is_surround and name_key in OMNIFormat.SURROUND_MAP:
                physics = {
                    "speed": 0.0,
                    "direction": 1,
                    "start_phase": OMNIFormat.SURROUND_MAP[name_key]['azi'],
                    "randomness": 0.0
                }
            else:
                speed = random.uniform(0.3, 1.2) if role == 'spatial' else 0.05 if role == 'anchor' else 1.2
                direction = random.choice([1, -1])
                start_phase = random.uniform(0, 360) if role == 'spatial' else 0
                randomness = 0.2 if role == 'spatial' else 0.02 if role == 'anchor' else 0.5

                physics = {
                    "speed": speed,
                    "direction": direction,
                    "start_phase": start_phase,
                    "randomness": randomness
                }

            obj_keyframes = [kf for kf in keyframes if kf.get('object_name') == stem['name']]

            data["objects"].append({
                "name": stem['name'],
                "file": stem['file'],
                "role": role,
                "physics": physics,
                "keyframes": obj_keyframes
            })

        random.seed()  # Reset

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return seed