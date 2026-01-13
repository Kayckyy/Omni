# src/core/math_utils.py
"""Utilitários matemáticos para conversão coordenadas e ganhos de pan."""

import numpy as np


def cartesian_to_spherical(x: float, y: float, z: float) -> tuple[float, float]:
    """Converte coordenadas Cartesianas para Esféricas.
    
    Sistema: 0°=Frente, 90°=Direita, 180°=Trás, 270°=Esquerda.
    
    Args:
        x, y, z: Coordenadas cartesianas.
    
    Returns:
        (azimuth, elevation): Em graus.
    """
    azimuth = np.degrees(np.arctan2(x, y)) % 360
    distance = np.sqrt(x**2 + y**2 + z**2)
    elevation = 0.0
    if distance > 0:
        elevation = np.degrees(np.arcsin(np.clip(z / distance, -1, 1)))
    return azimuth, elevation


def calculate_stereo_gains(azimuth: float) -> tuple[float, float]:
    """Calcula ganhos Estéreo (L/R) usando Constant Power Pan Law.
    
    Args:
        azimuth: Ângulo em graus.
    
    Returns:
        (gain_left, gain_right)
    """
    rads = np.radians(azimuth % 360)
    pan_position = np.sin(rads)
    norm_pan = (pan_position + 1) / 2.0
    gain_l = np.cos(norm_pan * np.pi / 2)
    gain_r = np.sin(norm_pan * np.pi / 2)
    return gain_l, gain_r


def calculate_5_1_gains(azimuth: float) -> np.ndarray:
    """Calcula ganhos 5.1 usando interpolação linear de potência constante.
    
    Canais: [L, R, C, LFE, Ls, Rs]
    
    Args:
        azimuth: Ângulo em graus.
    
    Returns:
        Array de ganhos para 6 canais.
    """
    azimuth = azimuth % 360
    gains = np.zeros(6)

    speaker_nodes = [
        (0, 2),    # Center
        (30, 1),   # Right
        (110, 5),  # Right Surround
        (250, 4),  # Left Surround
        (330, 0),  # Left
        (360, 2)   # Center (close loop)
    ]

    for i in range(len(speaker_nodes) - 1):
        angle_start, ch_start = speaker_nodes[i]
        angle_end, ch_end = speaker_nodes[i + 1]

        if angle_start <= azimuth <= angle_end:
            segment_range = max(angle_end - angle_start, 1)  # Avoid div zero
            t = (azimuth - angle_start) / segment_range
            gains[ch_start] = np.cos(t * np.pi / 2)
            gains[ch_end] = np.sin(t * np.pi / 2)
            break

    return gains