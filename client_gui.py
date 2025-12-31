import sys
import threading
import os

# PyQt5 peut ne pas fonctionner dans Docker sans X11
# Ce fichier est pour lancement local uniquement
try:
    from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                                 QHBoxLayout, QPushButton, QTextEdit, QLabel,
                                 QLineEdit, QGroupBox, QSpinBox)
    from PyQt5.QtCore import pyqtSignal, QObject

    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    print("[CLIENT_GUI] PyQt5 non disponible - utilisez client.py en CLI")

from client import OnionClient

if PYQT_AVAILABLE:
    class ClientSignals(QObject):
        """Signaux pour la communication thread-safe avec l'interface"""
        log_signal = pyqtSignal(str)
        message_received_signal = pyqtSignal(str, str)


    class ClientGUI(QMainWindow):
        """Interface graphique pour le Client"""

        def __init__(self):
            super().__init__()
            self.client = None
            self.signals = ClientSignals()

            self.init_ui()

            # Connecter les signaux
            self.signals.log_signal.connect(self.append_log)
            self.signals.message_received_signal.connect(self.display_received_message)

        def init_ui(self):
            """Initialise l'interface utilisateur"""
            self.setWindowTitle("Client - Routage en Oignon")
            self.setGeometry(200, 200, 700, 700)

            # Widget central
            central_widget = QWidget()
            self.setCentralWidget(central_widget)

            # Layout principal
            main_layout = QVBoxLayout()
            central_widget.setLayout(main_layout)

            # En-tête
            header = QLabel("<h2>Client - Communication Anonyme</h2>")
            main_layout.addWidget(header)

            # Groupe de configuration
            config_group = QGroupBox("Configuration")
            config_layout = QVBoxLayout()
            config_group.setLayout(config_layout)

            # Nom du client
            name_layout = QHBoxLayout()
            name_layout.addWidget(QLabel("Nom du client:"))
            self.name_input = QLineEdit("ClientA")
            name_layout.addWidget(self.name_input)
            config_layout.addLayout(name_layout)

            # Port d'écoute
            port_layout = QHBoxLayout()
            port_layout.addWidget(QLabel("Port d'écoute:"))
            self.port_input = QSpinBox()
            self.port_input.setRange(10000, 65535)
            self.port_input.setValue(10000)
            port_layout.addWidget(self.port_input)
            config_layout.addLayout(port_layout)

            # Bouton de démarrage
            self.start_button = QPushButton("Démarrer Client")
            self.start_button.clicked.connect(self.start_client)
            config_layout.addWidget(self.start_button)

            main_layout.addWidget(config_group)

            # Groupe d'envoi de message
            send_group = QGroupBox("Envoyer un message")
            send_layout = QVBoxLayout()
            send_group.setLayout(send_layout)

            # IP destination
            dest_ip_layout = QHBoxLayout()
            dest_ip_layout.addWidget(QLabel("IP destination:"))
            self.dest_ip_input = QLineEdit("127.0.0.1")
            dest_ip_layout.addWidget(self.dest_ip_input)
            send_layout.addLayout(dest_ip_layout)

            # Port destination
            dest_port_layout = QHBoxLayout()
            dest_port_layout.addWidget(QLabel("Port destination:"))
            self.dest_port_input = QSpinBox()
            self.dest_port_input.setRange(10000, 65535)
            self.dest_port_input.setValue(10001)
            dest_port_layout.addWidget(self.dest_port_input)
            send_layout.addLayout(dest_port_layout)

            # Nombre de sauts
            hops_layout = QHBoxLayout()
            hops_layout.addWidget(QLabel("Nombre de sauts:"))
            self.hops_input = QSpinBox()
            self.hops_input.setRange(1, 5)
            self.hops_input.setValue(3)
            hops_layout.addWidget(self.hops_input)
            send_layout.addLayout(hops_layout)

            # Message
            send_layout.addWidget(QLabel("Message:"))
            self.message_input = QTextEdit()
            self.message_input.setMaximumHeight(80)
            send_layout.addWidget(self.message_input)

            # Boutons
            button_layout = QHBoxLayout()

            self.refresh_button = QPushButton("Actualiser Routeurs")
            self.refresh_button.clicked.connect(self.refresh_routers)
            self.refresh_button.setEnabled(False)
            button_layout.addWidget(self.refresh_button)

            self.send_button = QPushButton("Envoyer")
            self.send_button.clicked.connect(self.send_message)
            self.send_button.setEnabled(False)
            button_layout.addWidget(self.send_button)

            send_layout.addLayout(button_layout)

            main_layout.addWidget(send_group)

            # Zone de logs
            logs_group = QGroupBox("Messages et Logs")
            logs_layout = QVBoxLayout()
            logs_group.setLayout(logs_layout)

            self.log_text = QTextEdit()
            self.log_text.setReadOnly(True)
            logs_layout.addWidget(self.log_text)

            main_layout.addWidget(logs_group)

        def start_client(self):
            """Démarre le client"""
            if self.client is None:
                client_name = self.name_input.text()
                listen_port = self.port_input.value()

                self.client = OnionClient(client_name, listen_port)
                self.client.start_listener()

                self.signals.log_signal.emit(f"[GUI] Client {client_name} démarré sur le port {listen_port}")

                self.name_input.setEnabled(False)
                self.port_input.setEnabled(False)
                self.start_button.setEnabled(False)
                self.refresh_button.setEnabled(True)
                self.send_button.setEnabled(True)

                # Récupérer automatiquement la liste des routeurs
                self.refresh_routers()

        def refresh_routers(self):
            """Actualise la liste des routeurs"""
            if self.client:
                def refresh_thread():
                    success = self.client.fetch_router_list()
                    if success:
                        self.signals.log_signal.emit(f"[GUI] {len(self.client.routers)} routeurs disponibles")
                    else:
                        self.signals.log_signal.emit("[GUI] Erreur lors de la récupération des routeurs")

                thread = threading.Thread(target=refresh_thread)
                thread.daemon = True
                thread.start()

        def send_message(self):
            """Envoie un message"""
            if self.client:
                dest_ip = self.dest_ip_input.text()
                dest_port = self.dest_port_input.value()
                message = self.message_input.toPlainText()
                num_hops = self.hops_input.value()

                if not message:
                    self.signals.log_signal.emit("[GUI] Le message est vide")
                    return

                def send_thread():
                    self.signals.log_signal.emit(f"[GUI] Envoi du message vers {dest_ip}:{dest_port}...")
                    success = self.client.send_message(message, dest_ip, dest_port, num_hops)
                    if success:
                        self.signals.log_signal.emit("[GUI] Message envoyé avec succès!")
                        self.message_input.clear()
                    else:
                        self.signals.log_signal.emit("[GUI] Erreur lors de l'envoi")

                thread = threading.Thread(target=send_thread)
                thread.daemon = True
                thread.start()

        def display_received_message(self, sender, message):
            """Affiche un message reçu"""
            self.signals.log_signal.emit(f"\n*** MESSAGE REÇU ***")
            self.signals.log_signal.emit(f"De: {sender}")
            self.signals.log_signal.emit(f"Message: {message}")
            self.signals.log_signal.emit(f"********************\n")

        def append_log(self, message):
            """Ajoute un message aux logs"""
            self.log_text.append(message)

        def closeEvent(self, event):
            """Gère la fermeture de la fenêtre"""
            if self.client:
                self.client.stop()
            event.accept()

if __name__ == "__main__":
    if not PYQT_AVAILABLE:
        print("PyQt5 non installé. Utilisez client.py en mode CLI.")
        sys.exit(1)
    else:
        app = QApplication(sys.argv)
        gui = ClientGUI()
        gui.show()
        sys.exit(app.exec_())
