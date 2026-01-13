# src/dsp/processor.py
"""Processador principal de áudio espacial com HRTF e múltiplos modos de renderização."""

import numpy as np
from scipy import signal
from typing import Tuple, Dict, Any

from src.dsp.hrtf_engine import HRTFEngine
from src.core.math_utils import cartesian_to_spherical


class OMNIProcessor:
    """Classe responsável pelo processamento de objetos e modos especiais de áudio espacial."""

    def __init__(self, hrtf_engine: HRTFEngine):
        self.hrtf = hrtf_engine

    def _apply_high_pass_filter(self, audio: np.ndarray, sr: int, cutoff: float = 3000.0) -> np.ndarray:
        """Aplica filtro high-pass (Butterworth 2ª ordem) para reduzir coloração em graves."""
        sos = signal.butter(2, cutoff, btype='high', fs=sr, output='sos')
        return signal.sosfilt(sos, audio)

    def _calculate_procedural_position(
        self,
        physics: Dict[str, Any],
        time: float,
        role: str
    ) -> Tuple[float, float]:
        """Calcula posição procedural (azimute, elevação) baseada em physics."""
        speed = physics.get('speed', 1.0)
        direction = physics.get('direction', 1)
        start_phase = physics.get('start_phase', 0)
        randomness = physics.get('randomness', 0.0)

        angle_rad = np.radians(start_phase) + (direction * speed * 0.5 * time)
        x = np.cos(angle_rad)
        y = np.sin(angle_rad)
        z = (0.7 + np.sin(time * 0.5) * 0.2) if role == 'ethereal' else np.sin(time * 0.3) * 0.3

        # Adiciona pequena variação aleatória se configurado
        if randomness > 0:
            x += np.random.uniform(-randomness, randomness)
            y += np.random.uniform(-randomness, randomness)
            z += np.random.uniform(-randomness * 0.5, randomness * 0.5)

        return cartesian_to_spherical(x, y, z)

    def process_object_binaural(
        self,
        mono_audio: np.ndarray,
        sr: int,
        obj_config: Dict[str, Any]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Processa objeto mono para binaural com posições procedurais ou fixas."""
        chunk_size = 4096
        hop = 2048
        role = obj_config.get('role', 'spatial')
        physics = obj_config.get('physics', {})

        if role == 'ethereal':
            mono_audio = self._apply_high_pass_filter(mono_audio, sr)

        out_l = np.zeros(len(mono_audio) + chunk_size, dtype=np.float32)
        out_r = np.zeros(len(mono_audio) + chunk_size, dtype=np.float32)
        window = np.hanning(chunk_size)

        for pos in range(0, len(mono_audio) - chunk_size, hop):
            chunk = mono_audio[pos:pos + chunk_size] * window
            t = (pos + chunk_size / 2) / sr

            if role == 'anchor':
                azi, ele = 0.0, 0.0
            elif role == 'lfe_focused':
                azi, ele = 0.0, -10.0
            else:
                azi, ele = self._calculate_procedural_position(physics, t, role)

            ir_l, ir_r = self.hrtf.get_ir(azi, ele)

            # Convolução em frequência (mais rápida que time-domain)
            conv_l = signal.fftconvolve(chunk, ir_l, mode='same')
            conv_r = signal.fftconvolve(chunk, ir_r, mode='same')

            out_l[pos:pos + chunk_size] += conv_l
            out_r[pos:pos + chunk_size] += conv_r

        return out_l[:len(mono_audio)], out_r[:len(mono_audio)]

    def process_stereo_fixed(
        self,
        stereo_audio: np.ndarray,
        sr: int
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Modo estéreo fixo (wide 90° com shadow)."""
        if stereo_audio.ndim == 1:
            stereo_audio = np.stack([stereo_audio, stereo_audio], axis=1)

        l_in, r_in = stereo_audio[:, 0], stereo_audio[:, 1]
        chunk_size, hop = 4096, 2048

        out_l = np.zeros(len(l_in) + chunk_size, dtype=np.float32)
        out_r = np.zeros(len(l_in) + chunk_size, dtype=np.float32)
        window = np.hanning(chunk_size)

        ir_l_left, ir_r_left = self.hrtf.get_ir(90, 0)
        ir_l_right, ir_r_right = self.hrtf.get_ir(270, 0)

        shadow = 0.6
        ir_r_left *= shadow
        ir_l_right *= shadow

        for pos in range(0, len(l_in) - chunk_size, hop):
            cl = l_in[pos:pos + chunk_size] * window
            cr = r_in[pos:pos + chunk_size] * window

            out_l[pos:pos + chunk_size] += (
                signal.fftconvolve(cl, ir_l_left, mode='same') +
                signal.fftconvolve(cr, ir_l_right, mode='same')
            )
            out_r[pos:pos + chunk_size] += (
                signal.fftconvolve(cl, ir_r_left, mode='same') +
                signal.fftconvolve(cr, ir_r_right, mode='same')
            )

        return out_l[:len(l_in)], out_r[:len(l_in)]

    def process_stereo_cinema(
        self,
        stereo_audio: np.ndarray,
        sr: int
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Modo cinema binaural (30° + simulação de sala)."""
        if stereo_audio.ndim == 1:
            stereo_audio = np.stack([stereo_audio, stereo_audio], axis=1)

        l_in, r_in = stereo_audio[:, 0], stereo_audio[:, 1]
        chunk_size, hop = 4096, 2048

        out_l = np.zeros(len(l_in) + chunk_size, dtype=np.float32)
        out_r = np.zeros(len(l_in) + chunk_size, dtype=np.float32)
        window = np.hanning(chunk_size)

        ir_l_left, ir_r_left = self.hrtf.get_ir(30, 0)
        ir_l_right, ir_r_right = self.hrtf.get_ir(330, 0)

        for pos in range(0, len(l_in) - chunk_size, hop):
            cl = l_in[pos:pos + chunk_size] * window
            cr = r_in[pos:pos + chunk_size] * window

            out_l[pos:pos + chunk_size] += (
                signal.fftconvolve(cl, ir_l_left, mode='same') +
                signal.fftconvolve(cr, ir_l_right, mode='same')
            )
            out_r[pos:pos + chunk_size] += (
                signal.fftconvolve(cl, ir_r_left, mode='same') +
                signal.fftconvolve(cr, ir_r_right, mode='same')
            )

        # Early reflections (simulação de sala)
        delay_samples = int(0.022 * sr)  # ~22ms
        sos_lp = signal.butter(2, 4000, btype='low', fs=sr, output='sos')

        ref_l = signal.sosfilt(sos_lp, np.pad(out_r[:len(l_in)], (delay_samples, 0))[:len(l_in)]) * 0.25
        ref_r = signal.sosfilt(sos_lp, np.pad(out_l[:len(l_in)], (delay_samples, 0))[:len(l_in)]) * 0.25

        return out_l[:len(l_in)] + ref_l, out_r[:len(l_in)] + ref_r

    def apply_xtc(
        self,
        stereo_audio: np.ndarray,
        sr: int
    ) -> np.ndarray:
        """Aplica Crosstalk Cancellation (XTC) para speaker 3D."""
        delay = int((0.15 * np.sin(np.radians(20)) / 343.0) * sr)
        sos_lp = signal.butter(2, 2200, btype='low', fs=sr, output='sos')

        l_in, r_in = stereo_audio[:, 0], stereo_audio[:, 1]

        l_delayed = np.pad(l_in, (delay, 0))[:len(l_in)]
        r_delayed = np.pad(r_in, (delay, 0))[:len(r_in)]

        l_c = signal.sosfilt(sos_lp, r_delayed)
        r_c = signal.sosfilt(sos_lp, l_delayed)

        out_l = (l_in - r_c * 0.55) * 1.1
        out_r = (r_in - l_c * 0.55) * 1.1

        return np.stack([out_l, out_r], axis=1)