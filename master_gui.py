import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QTextEdit, QLabel, QTableWidget,
                             QTableWidgetItem, QGroupBox)
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from master import Master
from database import Database


class MasterThread(QThread):
    """Thread pour exécuter le serveur Master"""
    log_signal = pyqtSignal(str)

    def __init__(self, master):
        super().__init__()
        self.master = master

    def run(self):
        self.master.start()


class MasterGUI(QMainWindow):
    """Interface graphique pour le serveur Master"""

    def __init__(self):
        super().__init__()
        self.master = Master()
        self.master_thread = None
        self.db = Database()

        self.init_ui()

        # Timer pour rafraîchir les données
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_display)
        self.timer.start(2000)  # Refresh toutes les 2 secondes

    def init_ui(self):
        """Initialise l'interface utilisateur"""
        self.setWindowTitle("Master - Routage en Oignon")
        self.setGeometry(100, 100, 900, 600)

        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Titre
        title = QLabel("🔐 Serveur Master - Routage en Oignon")
        title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        main_layout.addWidget(title)

        # Boutons de contrôle
        control_layout = QHBoxLayout()
        self.btn_start = QPushButton("▶ Démarrer Master")
        self.btn_start.clicked.connect(self.start_master)
        self.btn_stop = QPushButton("⏹ Arrêter Master")
        self.btn_stop.clicked.connect(self.stop_master)
        self.btn_stop.setEnabled(False)

        control_layout.addWidget(self.btn_start)
        control_layout.addWidget(self.btn_stop)
        main_layout.addLayout(control_layout)

        # Status
        self.status_label = QLabel("Status: Arrêté")
        self.status_label.setStyleSheet("padding: 5px; background-color: #ffcccc;")
        main_layout.addWidget(self.status_label)

        # Table des routeurs
        router_group = QGroupBox("Routeurs Enregistrés")
        router_layout = QVBoxLayout()
        self.router_table = QTableWidget()
        self.router_table.setColumnCount(4)
        self.router_table.setHorizontalHeaderLabels(["ID", "IP", "Port", "Clé Publique"])
        router_layout.addWidget(self.router_table)
        router_group.setLayout(router_layout)
        main_layout.addWidget(router_group)

        # Logs
        log_group = QGroupBox("Logs")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)

    def start_master(self):
        """Démarre le serveur Master"""
        self.master_thread = MasterThread(self.master)
        self.master_thread.start()

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.status_label.setText("Status: En cours d'exécution")
        self.status_label.setStyleSheet("padding: 5px; background-color: #ccffcc;")
        self.add_log("Master démarré sur port 8000")

    def stop_master(self):
        """Arrête le serveur Master"""
        self.master.stop()
        if self.master_thread:
            self.master_thread.quit()
            self.master_thread.wait()

        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.status_label.setText("Status: Arrêté")
        self.status_label.setStyleSheet("padding: 5px; background-color: #ffcccc;")
        self.add_log("Master arrêté")

    def update_display(self):
        """Met à jour l'affichage des routeurs et logs"""
        # Mettre à jour la table des routeurs
        routers = self.db.get_all_routers()
        self.router_table.setRowCount(len(routers))

        for row, router in enumerate(routers):
            router_id, ip, port, public_key = router
            self.router_table.setItem(row, 0, QTableWidgetItem(str(router_id)))
            self.router_table.setItem(row, 1, QTableWidgetItem(ip))
            self.router_table.setItem(row, 2, QTableWidgetItem(str(port)))
            self.router_table.setItem(row, 3, QTableWidgetItem(str(public_key)[:20] + "..."))

    def add_log(self, message):
        """Ajoute un message dans les logs"""
        self.log_text.append(f"[{self.get_timestamp()}] {message}")

    @staticmethod
    def get_timestamp():
        """Retourne l'horodatage actuel"""
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")

    def closeEvent(self, event):
        """Gère la fermeture de la fenêtre"""
        if self.master.running:
            self.stop_master()
        self.db.close()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = MasterGUI()
    gui.show()
    sys.exit(app.exec_())
