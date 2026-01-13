# src/cli.py
"""Módulo responsável por parsing de argumentos da linha de comando."""

import argparse
from typing import Tuple

def parse_arguments() -> argparse.Namespace:
    """Configura e retorna os argumentos parseados."""
    parser = argparse.ArgumentParser(
        description="OmniAudio - Processamento de áudio espacial binaural",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="Exemplos:\n"
               "  python main.py auto 'meu_video.mp4'\n"
               "  python main.py process_multi projeto.omni --format cinema_binaural",
    )

    parser.add_argument(
        "mode",
        choices=["auto", "create_multi", "process_multi"],
        help="Modo de operação:\n"
             "  auto          → Extrai áudio, separa stems e cria .omni\n"
             "  create_multi  → Cria .omni a partir de arquivo de áudio\n"
             "  process_multi → Renderiza binaural a partir de .omni"
    )

    parser.add_argument(
        "input",
        type=str,
        help="Caminho do arquivo de entrada (vídeo, áudio ou .omni)"
    )

    parser.add_argument(
        "--format",
        choices=["binaural", "cinema_binaural", "static_binaural", "static_speaker", "speaker_3d"],
        default="binaural",
        help="Formato de saída (usado apenas em process_multi)"
    )

    return parser.parse_args()


def show_usage() -> None:
    """Mostra ajuda rápida quando argumentos estão errados."""
    print("Uso correto:")
    print("  python main.py [auto|create_multi|process_multi] [arquivo] [--format formato]")
    print("\nExemplo:")
    print("  python main.py auto 'meu_video.mp4'")
    print("  python main.py process_multi 'projeto.omni' --format cinema_binaural")