#!/usr/bin/env python3
"""OmniAudio - Entrypoint principal."""

import sys
from pathlib import Path

# Adiciona raiz ao path pra encontrar src/
sys.path.insert(0, str(Path(__file__).parent.resolve()))

import argparse
from src.cli import parse_arguments
from src.video_utils import extract_audio_from_video, split_multichannel, merge_audio_to_video
from src.project import create_project_directory, create_omni_file
from src.renderer import render_omni_project
from src.dsp.hrtf_engine import HRTFEngine
from src.dsp.processor import OMNIProcessor


def find_associated_video(omni_path: Path) -> str | None:
    base_name = omni_path.stem.replace("_extracted", "")
    search_dirs = [omni_path.parent, omni_path.parent.parent, Path.cwd()]

    video_exts = (".mp4", ".mkv", ".mov", ".avi", ".flv", ".wmv", ".webm")

    for dir_path in search_dirs:
        for ext in video_exts:
            candidate = dir_path / (base_name + ext)
            if candidate.exists():
                return str(candidate)
    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="OmniAudio - Áudio Espacial Binaural",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "mode",
        nargs="?",
        choices=["auto", "create_multi", "process_multi", "gui"],
        default="gui",
        help="Modo (padrão: gui)\n"
             "  auto          - Extrai e cria .omni\n"
             "  create_multi  - Cria .omni de áudio\n"
             "  process_multi - Renderiza .omni\n"
             "  gui           - Abre interface gráfica"
    )
    parser.add_argument(
        "input",
        nargs="?",
        type=str,
        help="Arquivo de entrada (vídeo, áudio ou .omni)"
    )
    parser.add_argument(
        "--format",
        choices=["binaural", "cinema_binaural", "static_binaural", "static_speaker", "speaker_3d"],
        default="binaural",
        help="Formato de saída (usado em process_multi)"
    )

    args = parser.parse_args()

    if args.mode == "gui":
        from src.gui import run_gui
        run_gui()
        sys.exit(0)

    if not args.input:
        parser.error("Informe o arquivo de entrada para modos CLI.")

    base_path = Path(__file__).parent.resolve()
    hrtf = HRTFEngine(base_path / "data" / "hrtf")
    if not hrtf.load():
        sys.exit("Erro: Não foi possível carregar HRTFs.")

    processor = OMNIProcessor(hrtf)

    if args.mode in ("auto", "create_multi"):
        input_path = Path(args.input).resolve()
        if not input_path.exists():
            sys.exit(f"Arquivo não encontrado: {input_path}")

        audio_path = extract_audio_from_video(str(input_path))
        proj_dir = create_project_directory(audio_path)

        stems = split_multichannel(audio_path, proj_dir)
        if not stems:
            stems = [{"name": "Estéreo", "file": audio_path}]

        omni_path = create_omni_file(
            stems=stems,
            audio_path=str(audio_path),
            proj_dir=proj_dir,
            is_surround=(len(stems) > 2)
        )

        print(f"Projeto criado!\n.omni: {omni_path}")

    elif args.mode == "process_multi":
        omni_path = Path(args.input).resolve()
        if not omni_path.exists():
            sys.exit(f".omni não encontrado: {omni_path}")

        output_file = render_omni_project(
            omni_path=omni_path,
            processor=processor,
            output_format=args.format,
        )

        print(f"Renderizado: {output_file}")

        video = find_associated_video(omni_path)
        if video:
            merge_audio_to_video(video, output_file)
            print("Vídeo final com áudio 3D gerado.")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrompido.")
        sys.exit(0)
    except Exception as e:
        print(f"Erro: {e}")
        sys.exit(1)