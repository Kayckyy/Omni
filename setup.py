# setup.py
"""Configuração para instalar o OmniAudio como pacote Python."""

from setuptools import setup, find_packages
import os

# Lê o README como long_description
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="omniaudio",
    version="0.1.0",  # Comece com 0.1.0 e incremente depois
    author="Kayck",
    author_email="seuemail@example.com",  # Coloque o seu
    description="Ferramenta de áudio espacial binaural com HRTF e posicionamento 3D",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Kayckyy/OmniAudio",
    project_urls={
        "Bug Tracker": "https://github.com/Kayckyy/OmniAudio/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",  # Ou a que você escolher
        "Operating System :: OS Independent",
        "Topic :: Multimedia :: Sound/Audio :: Analysis",
        "Topic :: Multimedia :: Sound/Audio :: Editors",
    ],
    python_requires=">=3.8",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,  # Inclui data/hrtf, icons, etc.
    install_requires=[
        "numpy>=1.21",
        "scipy>=1.7",
        "soundfile>=0.10",
        "pydub>=0.25",
        "PyQt5>=5.15",  # Se usar GUI
        "Pillow>=8.0",
        # "opensimplex",  # Descomente se usar trajectory com noise
        # "demucs",       # Se conseguir instalar depois
    ],
    extras_require={
        "dev": [
            "black",
            "isort",
            "pylint",
            "mypy",
            "pytest",
        ],
    },
    entry_points={
        "console_scripts": [
            "omniaudio = main:main",  # Permite rodar `omniaudio auto arquivo.mp4` depois de instalar
        ],
    },
    keywords="audio spatial binaural hrtf dolby atmos python",
)