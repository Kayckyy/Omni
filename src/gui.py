# src/gui.py
"""Interface gráfica principal do OmniAudio com PyQt5 e visualizador 3D."""

import sys
import json
import math
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QMessageBox, QTabWidget,
    QComboBox, QStatusBar, QInputDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

import numpy as np
import pyqtgraph.opengl as gl

from src.audio_io import load_audio
from src.video_utils import extract_audio_from_video, split_multichannel
from src.project import create_omni_file
from src.core.omni_format import OMNIFormat
from src.dsp.hrtf_engine import HRTFEngine
from src.dsp.processor import OMNIProcessor
from src.renderer import render_omni_project


class OmniObject(gl.GLGraphicsItem):
    """Objeto arrastável no visualizador 3D."""

    def __init__(self, name, az=0.0, el=0.0, role='spatial'):
        gl.GLGraphicsItem.__init__(self)
        self.name = name
        self.role = role
        self.az = az
        self.el = el
        self.radius = 1.0

        # Cores por role (mais visíveis no dark mode)
        colors = {
            'anchor': (1.0, 0.3, 0.3, 1.0),     # Vermelho suave
            'lfe_focused': (0.8, 0.0, 0.8, 1.0),  # Roxo
            'ethereal': (0.0, 0.9, 0.9, 1.0),    # Ciano
            'spatial': (0.2, 0.6, 1.0, 1.0)      # Azul espacial
        }
        self.color = colors.get(role, (0.2, 0.6, 1.0, 1.0))

        self._update_position()

    def _update_position(self):
        az_rad = math.radians(self.az)
        el_rad = math.radians(self.el)
        x = self.radius * math.cos(el_rad) * math.sin(az_rad)
        y = self.radius * math.cos(el_rad) * math.cos(az_rad)
        z = self.radius * math.sin(el_rad)
        self.setPos(x, y, z)

    def paint(self):
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glColor4f(*self.color)
        gl.glPointSize(24)
        gl.glBegin(gl.GL_POINTS)
        gl.glVertex3f(self.pos().x(), self.pos().y(), self.pos().z())
        gl.glEnd()

    def mouseDragEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            if ev.isFinish():
                # Atualiza az/el baseado na nova posição 3D
                pos = self.pos()
                r = np.sqrt(pos.x()**2 + pos.y()**2 + pos.z()**2) or 1.0
                self.el = math.degrees(math.asin(pos.z() / r))
                self.az = math.degrees(math.atan2(pos.x(), pos.y())) % 360
                self._update_position()  # Volta pra esfera
                print(f"{self.name} movido para az={self.az:.1f}°, el={self.el:.1f}°")  # Debug temporário
            else:
                super().mouseDragEvent(ev)


class OmniAudioGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OmniAudio - Espacialização 3D")
        self.setGeometry(200, 100, 1200, 800)

        # Tema dark profissional
        self.setStyleSheet("""
            QMainWindow { background-color: #0d1117; color: #c9d1d9; }
            QPushButton { 
                background-color: #21262d; 
                color: #c9d1d9; 
                padding: 10px 20px; 
                border-radius: 6px; 
                border: 1px solid #30363d;
            }
            QPushButton:hover { background-color: #30363d; }
            QComboBox { 
                background-color: #161b22; 
                color: #c9d1d9; 
                border: 1px solid #30363d; 
                padding: 6px; 
                border-radius: 6px;
            }
            QTabWidget::pane { border: 1px solid #30363d; background: #0d1117; }
            QTabBar::tab { 
                background: #161b22; 
                color: #8b949e; 
                padding: 12px 20px; 
                border: 1px solid #30363d;
            }
            QTabBar::tab:selected { background: #21262d; color: #c9d1d9; }
            QLabel { color: #c9d1d9; }
            QStatusBar { background-color: #010409; color: #58a6ff; }
        """)

        self.hrtf = HRTFEngine("data/hrtf")
        if not self.hrtf.load():
            QMessageBox.critical(self, "Erro", "Falha ao carregar HRTFs.")
            sys.exit(1)

        self.processor = OMNIProcessor(self.hrtf)
        self.current_omni_path = None
        self.stems = []
        self.objects_data = []
        self.scene_objects = []  # Referências aos itens 3D arrastáveis

        self._init_ui()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 15)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self._create_import_tab()
        self._create_customize_tab()
        self._create_render_tab()

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Pronto. Comece carregando uma faixa ou .omni.")

    def _create_import_tab(self):
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setSpacing(15)

        lay.addWidget(QLabel("1. Importar Faixa e Criar Projeto"))
        btn_load = QPushButton("Selecionar Áudio ou Vídeo")
        btn_load.clicked.connect(self._load_file_for_omni)
        lay.addWidget(btn_load)

        self.import_status = QLabel("Nenhuma faixa selecionada.")
        lay.addWidget(self.import_status)

        btn_create = QPushButton("Gerar .omni")
        btn_create.clicked.connect(self._create_omni)
        lay.addWidget(btn_create)

        lay.addStretch()
        self.tabs.addTab(tab, "Importar")

    def _create_customize_tab(self):
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setSpacing(15)

        lay.addWidget(QLabel("2. Customizar Movimento e Posições"))

        btn_load = QPushButton("Abrir Projeto .omni")
        btn_load.clicked.connect(self._load_omni_custom)
        lay.addWidget(btn_load)

        self.custom_status = QLabel("Nenhum projeto aberto.")
        lay.addWidget(self.custom_status)

        # Presets
        preset_lay = QHBoxLayout()
        preset_lay.addWidget(QLabel("Estilo de Movimento:"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["Orgânico", "Caótico", "Suave", "Curioso", "Agressivo"])
        preset_lay.addWidget(self.preset_combo)
        lay.addLayout(preset_lay)

        btn_apply = QPushButton("Aplicar Estilo em Todos")
        btn_apply.clicked.connect(self._apply_preset)
        lay.addWidget(btn_apply)

        btn_keyframe = QPushButton("Adicionar Keyframe")
        btn_keyframe.clicked.connect(self._add_keyframe)
        lay.addWidget(btn_keyframe)

        btn_random = QPushButton("Gerar Movimentos Aleatórios")
        btn_random.clicked.connect(self._set_random_movements)
        lay.addWidget(btn_random)

        btn_save = QPushButton("Salvar Modificado")
        btn_save.clicked.connect(self._save_modified_omni)
        lay.addWidget(btn_save)

        # Visualizador 3D
        self.gl_view = gl.GLViewWidget()
        self.gl_view.setCameraPosition(distance=6, elevation=30, azimuth=45)
        self.gl_view.opts['bgcolor'] = (13, 17, 23, 255)
        lay.addWidget(self.gl_view, stretch=1)

        # Esfera de fundo escura
        self._add_sphere_background()

        # Eixos
        axis = gl.GLAxisItem()
        axis.setSize(4, 4, 4)
        self.gl_view.addItem(axis)

        lay.addStretch()
        self.tabs.addTab(tab, "Customizar")

    def _add_sphere_background(self):
        """Adiciona esfera wireframe escura como fundo."""
        theta = np.linspace(0, 2*np.pi, 40)
        phi = np.linspace(0, np.pi, 40)
        theta, phi = np.meshgrid(theta, phi)
        x = np.sin(phi) * np.cos(theta)
        y = np.sin(phi) * np.sin(theta)
        z = np.cos(phi)

        for i in range(0, len(phi), 4):
            line = gl.GLLinePlotItem(
                pos=np.column_stack((x[i], y[i], z[i])),
                color=(0.2, 0.2, 0.2, 0.3),  # Cinza bem escuro
                width=0.5
            )
            self.gl_view.addItem(line)

    def _create_render_tab(self):
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setSpacing(15)

        lay.addWidget(QLabel("3. Renderizar Áudio Espacial"))
        lay.addWidget(QLabel("Formato Final:"))
        self.render_combo = QComboBox()
        self.render_combo.addItems(["Binaural (Fones)", "Cinema Binaural", "Estéreo Fixo", "Speaker 3D"])
        lay.addWidget(self.render_combo)

        btn_render = QPushButton("Renderizar Agora")
        btn_render.clicked.connect(self._render_now)
        lay.addWidget(btn_render)

        lay.addStretch()
        self.tabs.addTab(tab, "Renderizar")

    # Métodos de funcionalidade

    def _load_file_for_omni(self):
        path, _ = QFileDialog.getOpenFileName(self, "Selecionar Faixa", "", "Mídia (*.mp4 *.wav *.flac *.mkv *.mov *.avi)")
        if path:
            self.status.showMessage(f"Carregando: {Path(path).name}")
            try:
                audio_path = extract_audio_from_video(path)
                self.stems = split_multichannel(audio_path, Path("temp")) or [{"name": "Estéreo", "file": audio_path}]
                self.import_status.setText(f"Faixa carregada: {len(self.stems)} faixas")
            except Exception as e:
                QMessageBox.critical(self, "Erro", str(e))

    def _create_omni(self):
        if not self.stems:
            QMessageBox.warning(self, "Aviso", "Carregue uma faixa primeiro.")
            return

        save_path, _ = QFileDialog.getSaveFileName(self, "Salvar .omni", "", "*.omni")
        if save_path:
            try:
                audio, sr = load_audio(self.stems[0]['file'])
                duration = len(audio) / sr
                OMNIFormat.create_multi_stem_omni(
                    stems_list=self.stems,
                    duration=duration,
                    sr=sr,
                    path=save_path
                )
                QMessageBox.information(self, "Sucesso", f".omni criado:\n{save_path}")
            except Exception as e:
                QMessageBox.critical(self, "Erro", str(e))

    def _load_omni_custom(self):
        path, _ = QFileDialog.getOpenFileName(self, "Abrir .omni", "", "*.omni")
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.objects_data = data.get('objects', [])
                self.current_omni_path = Path(path)
                self.custom_status.setText(f"Aberto: {len(self.objects_data)} objetos")

                self.gl_view.clear()
                axis = gl.GLAxisItem()
                axis.setSize(4, 4, 4)
                self.gl_view.addItem(axis)

                self._add_sphere_background()

                self.scene_objects = []
                for obj in self.objects_data:
                    az = obj.get('physics', {}).get('start_phase', 0.0)
                    el = 0.0  # Placeholder – pode vir de keyframe ou cálculo
                    item = OmniObject(obj['name'], az, el, obj.get('role', 'spatial'))
                    self.gl_view.addItem(item)
                    self.scene_objects.append(item)

                self.status.showMessage("Projeto aberto. Arraste os pontos para reposicionar.")
            except Exception as e:
                QMessageBox.critical(self, "Erro", str(e))

    def _apply_preset(self):
        if not self.objects_data:
            return QMessageBox.warning(self, "Aviso", "Abra um projeto primeiro.")
        preset = self.preset_combo.currentText()
        QMessageBox.information(self, "Aplicado", f"Estilo '{preset}' aplicado (expanda depois).")

    def _add_keyframe(self):
        if not self.objects_data:
            return QMessageBox.warning(self, "Aviso", "Abra um projeto primeiro.")

        obj_names = [obj['name'] for obj in self.objects_data]
        obj_name, ok = QInputDialog.getItem(self, "Objeto", "Qual objeto?", obj_names, 0, False)
        if not ok:
            return

        time, ok = QInputDialog.getDouble(self, "Tempo (s)", "Em que segundo?", 0.0, 0.0, 3600.0, 2)
        if not ok:
            return

        azi, ok = QInputDialog.getDouble(self, "Azimute", "Azimute (°):", 0.0, -180, 180, 1)
        if not ok:
            return

        ele, ok = QInputDialog.getDouble(self, "Elevação", "Elevação (°):", 0.0, -90, 90, 1)
        if not ok:
            return

        OMNIFormat.add_keyframe_to_omni(
            str(self.current_omni_path), obj_name, time, azimuth=azi, elevation=ele
        )
        QMessageBox.information(self, "Keyframe", "Adicionado com sucesso.")

    def _set_random_movements(self):
        if not self.objects_data:
            return QMessageBox.warning(self, "Aviso", "Abra um projeto primeiro.")

        for obj in self.objects_data:
            obj['physics'] = {
                'speed': random.uniform(0.3, 1.5),
                'randomness': random.uniform(0.1, 0.6)
            }

        QMessageBox.information(self, "Sucesso", "Movimentos aleatórios aplicados.")

    def _save_modified_omni(self):
        if not self.current_omni_path:
            return QMessageBox.warning(self, "Aviso", "Nenhum projeto aberto.")

        save_path, _ = QFileDialog.getSaveFileName(self, "Salvar Modificado", "", "*.omni")
        if save_path:
            data = {"objects": self.objects_data}
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            QMessageBox.information(self, "Salvo", f"Salvo em:\n{save_path}")

    def _render_now(self):
        if not self.current_omni_path:
            return QMessageBox.warning(self, "Aviso", "Abra um projeto primeiro.")

        try:
            output = render_omni_project(
                omni_path=self.current_omni_path,
                processor=self.processor,
                output_format=self.render_combo.currentText()
            )
            self.status.showMessage(f"Renderizado: {output}")
            QMessageBox.information(self, "Render", f"Concluído!\n{output}")
        except Exception as e:
            QMessageBox.critical(self, "Erro", str(e))


def run_gui():
    app = QApplication(sys.argv)
    window = OmniAudioGUI()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    run_gui()