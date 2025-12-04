import mariadb
import sys


class Database:
    """Gestion de la base de données MariaDB pour le routage"""

    def __init__(self, host='localhost', port=3306, user='root', password=''):
        try:
            self.conn = mariadb.connect(
                user=user,
                password=password,
                host=host,
                port=port
            )
            self.cursor = self.conn.cursor()
            self._create_database()
        except mariadb.Error as e:
            print(f"Erreur de connexion à MariaDB: {e}")
            sys.exit(1)

    def _create_database(self):
        """Crée la base de données et les tables"""
        self.cursor.execute("CREATE DATABASE IF NOT EXISTS onion_routing")
        self.cursor.execute("USE onion_routing")

        # Table des routeurs
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS routeurs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ip VARCHAR(50) NOT NULL,
                port INT NOT NULL,
                public_key VARCHAR(255) NOT NULL,
                status VARCHAR(20) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Table des routes
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS routes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                destination VARCHAR(100),
                next_hop VARCHAR(100),
                interface VARCHAR(50),
                rule_id INT
            )
        """)

        # Table des logs
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                router_id INT,
                action VARCHAR(100),
                details TEXT
            )
        """)

        self.conn.commit()

    def add_router(self, ip, port, public_key):
        """Ajoute un routeur dans la base"""
        self.cursor.execute(
            "INSERT INTO routeurs (ip, port, public_key) VALUES (?, ?, ?)",
            (ip, port, str(public_key))
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def get_all_routers(self):
        """Récupère tous les routeurs actifs"""
        self.cursor.execute("SELECT id, ip, port, public_key FROM routeurs WHERE status='active'")
        return self.cursor.fetchall()

    def add_log(self, router_id, action, details):
        """Ajoute un log"""
        self.cursor.execute(
            "INSERT INTO logs (router_id, action, details) VALUES (?, ?, ?)",
            (router_id, action, details)
        )
        self.conn.commit()

    def get_logs(self, limit=100):
        """Récupère les derniers logs"""
        self.cursor.execute(f"SELECT * FROM logs ORDER BY timestamp DESC LIMIT {limit}")
        return self.cursor.fetchall()

    def close(self):
        """Ferme la connexion"""
        self.conn.close()
