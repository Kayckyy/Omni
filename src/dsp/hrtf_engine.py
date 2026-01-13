# src/dsp/hrtf_engine.py
"""Motor de HRTF com interpolação via KDTree."""

import os
import glob
import numpy as np
import soundfile as sf
from scipy.spatial import KDTree
from typing import Tuple, Dict


class HRTFEngine:
    """Carrega e interpola HRTFs (ex: SADIE II)."""

    def __init__(self, hrtf_path: str):
        self.hrtf_path = hrtf_path
        self.hrirs: Dict[Tuple[float, float], np.ndarray] = {}
        self.coords: np.ndarray = np.array([])
        self.tree: Optional[KDTree] = None

    def load(self) -> bool:
        """Carrega HRTFs da pasta."""
        pattern = os.path.join(self.hrtf_path, "D1_HRIR_WAV", "*.wav")
        files = glob.glob(pattern)
        if not files:
            return False

        for f in files:
            try:
                name = os.path.basename(f)
                azi_str = name.split('azi_')[1].split('_')[0].replace(',', '.')
                ele_str = name.split('ele_')[1].replace('.wav', '').replace(',', '.')
                azi = float(azi_str) % 360
                ele = float(ele_str)
                data, _ = sf.read(f)
                self.hrirs[(ele, azi)] = data
                self.coords = np.append(self.coords, [[ele, azi]], axis=0) if self.coords.size else np.array([[ele, azi]])
            except Exception:
                continue

        if self.coords.size == 0:
            return False

        self.coords = self.coords.reshape(-1, 2)
        self.tree = KDTree(self.coords)
        return True

    def get_ir(self, azi: float, ele: float) -> Tuple[np.ndarray, np.ndarray]:
        """Retorna IR interpolado para posição (azi, ele)."""
        if self.tree is None:
            raise RuntimeError("HRTF não carregado. Chame load() primeiro.")

        query = np.array([[ele, azi]])
        dists, idxs = self.tree.query(query, k=3)

        if dists[0][0] < 0.1:
            ir = self.hrirs[tuple(self.coords[idxs[0][0]])]
            return ir[:, 0], ir[:, 1]

        weights = 1.0 / (dists[0] + 1e-6)
        weights /= weights.sum()

        out_l = np.zeros(256)
        out_r = np.zeros(256)

        for i, idx in enumerate(idxs[0]):
            ir = self.hrirs[tuple(self.coords[idx])]
            l = min(len(ir), 256)
            out_l[:l] += ir[:l, 0] * weights[i]
            out_r[:l] += ir[:l, 1] * weights[i]

        return out_l, out_r