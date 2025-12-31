import mariadb
import sys
import os
import time


class Database:
    """Gestion de la base de données MariaDB pour le routage"""

    def __init__(self, host=None, port=3306, user='root', password='', database='onion_routing'):
        # Utiliser variables d'environnement Docker si disponibles
        if host is None:
            host = os.getenv('DB_HOST', 'localhost')

        if not password:
            password = os.getenv('DB_PASS', '')

        user = os.getenv('DB_USER', user)

        # Attendre que MariaDB soit prêt (important pour Docker)
        max_retries = 30
        retry_count = 0

        while retry_count < max_retries:
            try:
                # Connexion initiale sans base de données
                self.conn = mariadb.connect(
                    user=user,
                    password=password,
                    host=host,
                    port=port
                )
                self.cursor = self.conn.cursor()
                self._create_database(database)

                # Reconnexion avec la base de données
                self.conn.close()
                self.conn = mariadb.connect(
                    user=user,
                    password=password,
                    host=host,
                    port=port,
                    database=database
                )
                self.cursor = self.conn.cursor()
                self._create_tables()

                print(f"[DATABASE] Connexion établie avec succès à {host}:{port}")
                return

            except mariadb.Error as e:
                retry_count += 1
                if retry_count < max_retries:
                    print(f"[DATABASE] Tentative {retry_count}/{max_retries} - En attente de MariaDB...")
                    time.sleep(2)
                else:
                    print(f"[DATABASE] Erreur de connexion à MariaDB: {e}")
                    sys.exit(1)

    def _create_database(self, database):
        """Crée la base de données si elle n'existe pas"""
        try:
            self.cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database}")
            self.conn.commit()
        except mariadb.Error as e:
            print(f"[DATABASE] Erreur création DB: {e}")

    def _create_tables(self):
        """Crée les tables nécessaires"""
        try:
            # Table des routeurs
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS routeurs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    ip VARCHAR(50) NOT NULL,
                    port INT NOT NULL,
                    public_key VARCHAR(255) NOT NULL,
                    private_key VARCHAR(255) NOT NULL,
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

        except mariadb.Error as e:
            print(f"[DATABASE] Erreur création tables: {e}")

    def add_router(self, ip, port, public_key, private_key):
        """Ajoute un routeur dans la base"""
        try:
            self.cursor.execute(
                "INSERT INTO routeurs (ip, port, public_key, private_key) VALUES (%s, %s, %s, %s)",
                (ip, port, str(public_key), str(private_key))
            )
            self.conn.commit()
            return self.cursor.lastrowid
        except mariadb.Error as e:
            print(f"[DATABASE] Erreur ajout routeur: {e}")
            return None

    def get_all_routers(self):
        """Récupère tous les routeurs actifs"""
        try:
            self.cursor.execute("SELECT id, ip, port, public_key FROM routeurs WHERE status='active'")
            return self.cursor.fetchall()
        except mariadb.Error as e:
            print(f"[DATABASE] Erreur récupération routeurs: {e}")
            return []

    def add_log(self, router_id, action, details):
        """Ajoute un log"""
        try:
            self.cursor.execute(
                "INSERT INTO logs (router_id, action, details) VALUES (%s, %s, %s)",
                (router_id, action, details)
            )
            self.conn.commit()
        except mariadb.Error as e:
            print(f"[DATABASE] Erreur ajout log: {e}")

    def get_logs(self, limit=100):
        """Récupère les derniers logs"""
        try:
            self.cursor.execute(f"SELECT * FROM logs ORDER BY timestamp DESC LIMIT {limit}")
            return self.cursor.fetchall()
        except mariadb.Error as e:
            print(f"[DATABASE] Erreur récupération logs: {e}")
            return []

    def get_router_count(self):
        """Compte le nombre de routeurs actifs"""
        try:
            self.cursor.execute("SELECT COUNT(*) FROM routeurs WHERE status='active'")
            result = self.cursor.fetchone()
            return result[0] if result else 0
        except mariadb.Error as e:
            print(f"[DATABASE] Erreur comptage: {e}")
            return 0

    def close(self):
        """Ferme la connexion"""
        try:
            if self.cursor:
                self.cursor.close()
            if self.conn:
                self.conn.close()
            print("[DATABASE] Connexion fermée")
        except:
            pass
