import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QTextEdit, QLabel,
                             QLineEdit, QSpinBox, QGroupBox)
from PyQt5.QtCore import QThread, pyqtSignal
from client import OnionClient


class ClientGUI(QMainWindow):
    """Interface graphique pour le client"""

    def __init__(self, client_name="ClientA"):
        super().__init__()
        self.client = OnionClient(client_name)
        self.init_ui()

    def init_ui(self):
        """Initialise l'interface utilisateur"""
        self.setWindowTitle(f"Client - {self.client.client_name}")
        self.setGeometry(200, 200, 700, 500)

        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Titre
        title = QLabel(f"📱 Client {self.client.client_name}")
        title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        main_layout.addWidget(title)

        # Configuration
        config_group = QGroupBox("Configuration")
        config_layout = QVBoxLayout()

        # Destination IP
        dest_ip_layout = QHBoxLayout()
        dest_ip_layout.addWidget(QLabel("IP Destination:"))
        self.dest_ip_input = QLineEdit("127.0.0.1")
        dest_ip_layout.addWidget(self.dest_ip_input)
        config_layout.addLayout(dest_ip_layout)

        # Destination Port
        dest_port_layout = QHBoxLayout()
        dest_port_layout.addWidget(QLabel("Port Destination:"))
        self.dest_port_input = QSpinBox()
        self.dest_port_input.setRange(1024, 65535)
        self.dest_port_input.setValue(10000)
        dest_port_layout.addWidget(self.dest_port_input)
        config_layout.addLayout(dest_port_layout)

        # Nombre de sauts
        hops_layout = QHBoxLayout()
        hops_layout.addWidget(QLabel("Nombre de sauts:"))
        self.hops_input = QSpinBox()
        self.hops_input.setRange(1, 5)
        self.hops_input.setValue(3)
        hops_layout.addWidget(self.hops_input)
        config_layout.addLayout(hops_layout)

        config_group.setLayout(config_layout)
        main_layout.addWidget(config_group)

        # Message
        message_group = QGroupBox("Message")
        message_layout = QVBoxLayout()
        self.message_input = QTextEdit()
        self.message_input.setPlaceholderText("Entrez votre message ici...")
        self.message_input.setMaximumHeight(100)
        message_layout.addWidget(self.message_input)
        message_group.setLayout(message_layout)
        main_layout.addWidget(message_group)

        # Bouton d'envoi
        btn_layout = QHBoxLayout()
        self.btn_fetch = QPushButton("🔄 Actualiser les routeurs")
        self.btn_fetch.clicked.connect(self.fetch_routers)
        self.btn_send = QPushButton("📤 Envoyer Message")
        self.btn_send.clicked.connect(self.send_message)
        btn_layout.addWidget(self.btn_fetch)
        btn_layout.addWidget(self.btn_send)
        main_layout.addLayout(btn_layout)

        # Logs
        log_group = QGroupBox("Logs")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)

    def fetch_routers(self):
        """Récupère la liste des routeurs"""
        self.add_log("Récupération de la liste des routeurs...")
        if self.client.fetch_router_list():
            self.add_log(f"✓ {len(self.client.routers)} routeurs disponibles")
        else:
            self.add_log("✗ Erreur de récupération des routeurs")

    def send_message(self):
        """Envoie un message"""
        message = self.message_input.toPlainText()
        if not message:
            self.add_log("✗ Message vide")
            return

        dest_ip = self.dest_ip_input.text()
        dest_port = self.dest_port_input.value()
        num_hops = self.hops_input.value()

        self.add_log(f"Envoi du message vers {dest_ip}:{dest_port} via {num_hops} sauts...")

        if self.client.send_message(message, dest_ip, dest_port, num_hops):
            self.add_log("✓ Message envoyé avec succès!")
            self.message_input.clear()
        else:
            self.add_log("✗ Erreur d'envoi")

    def add_log(self, message):
        """Ajoute un message dans les logs"""
        self.log_text.append(f"[{self.get_timestamp()}] {message}")

    @staticmethod
    def get_timestamp():
        """Retourne l'horodatage actuel"""
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Demander le nom du client
    import sys

    client_name = sys.argv[1] if len(sys.argv) > 1 else "ClientA"

    gui = ClientGUI(client_name)
    gui.show()
    sys.exit(app.exec_())
