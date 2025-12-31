import sys
import threading
import os

# PyQt5 peut ne pas fonctionner dans Docker sans X11
# Ce fichier est pour lancement local uniquement
try:
    from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                                 QHBoxLayout, QPushButton, QTextEdit, QLabel, QGroupBox)
    from PyQt5.QtCore import QTimer, pyqtSignal, QObject

    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    print("[MASTER_GUI] PyQt5 non disponible - utilisez master.py en CLI")

from master import Master

if PYQT_AVAILABLE:
    class MasterSignals(QObject):
        """Signaux pour la communication thread-safe avec l'interface"""
        log_signal = pyqtSignal(str)
        router_count_signal = pyqtSignal(int)


    class MasterGUI(QMainWindow):
        """Interface graphique pour le Master"""

        def __init__(self):
            super().__init__()
            self.master = None
            self.master_thread = None
            self.signals = MasterSignals()

            self.init_ui()

            # Connecter les signaux
            self.signals.log_signal.connect(self.append_log)
            self.signals.router_count_signal.connect(self.update_router_count)

        def init_ui(self):
            """Initialise l'interface utilisateur"""
            self.setWindowTitle("Master - Routage en Oignon")
            self.setGeometry(100, 100, 800, 600)

            # Widget central
            central_widget = QWidget()
            self.setCentralWidget(central_widget)

            # Layout principal
            main_layout = QVBoxLayout()
            central_widget.setLayout(main_layout)

            # En-tête
            header = QLabel("<h2>Serveur Master - Gestion des Routeurs</h2>")
            main_layout.addWidget(header)

            # Groupe de contrôle
            control_group = QGroupBox("Contrôles")
            control_layout = QHBoxLayout()
            control_group.setLayout(control_layout)

            self.start_button = QPushButton("Démarrer Master")
            self.start_button.clicked.connect(self.start_master)
            control_layout.addWidget(self.start_button)

            self.stop_button = QPushButton("Arrêter Master")
            self.stop_button.clicked.connect(self.stop_master)
            self.stop_button.setEnabled(False)
            control_layout.addWidget(self.stop_button)

            main_layout.addWidget(control_group)

            # Groupe de statistiques
            stats_group = QGroupBox("Statistiques")
            stats_layout = QVBoxLayout()
            stats_group.setLayout(stats_layout)

            self.router_count_label = QLabel("Routeurs connectés: 0")
            stats_layout.addWidget(self.router_count_label)

            main_layout.addWidget(stats_group)

            # Zone de logs
            logs_group = QGroupBox("Logs")
            logs_layout = QVBoxLayout()
            logs_group.setLayout(logs_layout)

            self.log_text = QTextEdit()
            self.log_text.setReadOnly(True)
            logs_layout.addWidget(self.log_text)

            main_layout.addWidget(logs_group)

            # Timer pour rafraîchir les statistiques
            self.timer = QTimer()
            self.timer.timeout.connect(self.update_stats)
            self.timer.start(2000)  # Toutes les 2 secondes

        def start_master(self):
            """Démarre le serveur Master"""
            if self.master is None:
                self.master = Master(host='0.0.0.0', port=8000)
                self.master_thread = threading.Thread(target=self.master.start)
                self.master_thread.daemon = True
                self.master_thread.start()

                self.signals.log_signal.emit("[GUI] Master démarré sur le port 8000")

                self.start_button.setEnabled(False)
                self.stop_button.setEnabled(True)

        def stop_master(self):
            """Arrête le serveur Master"""
            if self.master:
                self.master.stop()
                self.master = None

                self.signals.log_signal.emit("[GUI] Master arrêté")

                self.start_button.setEnabled(True)
                self.stop_button.setEnabled(False)

        def update_stats(self):
            """Met à jour les statistiques"""
            if self.master:
                count = len(self.master.routers)
                self.signals.router_count_signal.emit(count)

        def update_router_count(self, count):
            """Met à jour le nombre de routeurs"""
            self.router_count_label.setText(f"Routeurs connectés: {count}")

        def append_log(self, message):
            """Ajoute un message aux logs"""
            self.log_text.append(message)

        def closeEvent(self, event):
            """Gère la fermeture de la fenêtre"""
            if self.master:
                self.master.stop()
            event.accept()

if __name__ == "__main__":
    if not PYQT_AVAILABLE:
        print("PyQt5 non installé. Démarrage du Master en mode CLI...")
        master = Master()
        try:
            master.start()
        except KeyboardInterrupt:
            master.stop()
    else:
        app = QApplication(sys.argv)
        gui = MasterGUI()
        gui.show()
        sys.exit(app.exec_())
