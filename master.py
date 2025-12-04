import socket
import threading
import json
from database import Database
from crypto_simple import SimpleCrypto


class Master:
    """Serveur Master qui gère les routeurs et distribue les clés"""

    def __init__(self, host='0.0.0.0', port=8000):
        self.host = host
        self.port = port
        self.routers = {}  # {router_id: {'ip': ..., 'port': ..., 'public_key': ...}}
        self.db = Database()
        self.server_socket = None
        self.running = False

    def start(self):
        """Démarre le serveur Master"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(10)
        self.running = True

        print(f"[MASTER] Démarré sur {self.host}:{self.port}")

        while self.running:
            try:
                conn, addr = self.server_socket.accept()
                thread = threading.Thread(target=self.handle_connection, args=(conn, addr))
                thread.daemon = True
                thread.start()
            except Exception as e:
                if self.running:
                    print(f"[MASTER] Erreur: {e}")

    def handle_connection(self, conn, addr):
        """Gère une connexion entrante"""
        try:
            # Recevoir le type de requête
            request_type = conn.recv(1024).decode()

            if request_type == "REGISTER_ROUTER":
                self.register_router(conn, addr)
            elif request_type == "GET_ROUTERS":
                self.send_router_list(conn)
            else:
                print(f"[MASTER] Requête inconnue: {request_type}")

        except Exception as e:
            print(f"[MASTER] Erreur de connexion: {e}")
        finally:
            conn.close()

    def register_router(self, conn, addr):
        """Enregistre un nouveau routeur"""
        try:
            # Recevoir les informations du routeur
            data = conn.recv(4096).decode()
            router_info = json.loads(data)

            router_id = len(self.routers) + 1
            self.routers[router_id] = {
                'ip': router_info['ip'],
                'port': router_info['port'],
                'public_key': router_info['public_key']
            }

            # Sauvegarder dans la base de données
            self.db.add_router(
                router_info['ip'],
                router_info['port'],
                router_info['public_key']
            )

            print(f"[MASTER] Routeur {router_id} enregistré: {router_info['ip']}:{router_info['port']}")

            # Envoyer confirmation
            conn.sendall(json.dumps({'router_id': router_id, 'status': 'ok'}).encode())

            # Logger
            self.db.add_log(router_id, 'REGISTER', f"Routeur enregistré depuis {addr}")

        except Exception as e:
            print(f"[MASTER] Erreur d'enregistrement: {e}")

    def send_router_list(self, conn):
        """Envoie la liste des routeurs aux clients"""
        try:
            router_list = []
            for router_id, info in self.routers.items():
                router_list.append({
                    'id': router_id,
                    'ip': info['ip'],
                    'port': info['port'],
                    'public_key': info['public_key']
                })

            response = json.dumps({
                'count': len(router_list),
                'routers': router_list
            })

            conn.sendall(response.encode())
            print(f"[MASTER] Liste de {len(router_list)} routeurs envoyée")

        except Exception as e:
            print(f"[MASTER] Erreur d'envoi: {e}")

    def stop(self):
        """Arrête le serveur Master"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        self.db.close()


if __name__ == "__main__":
    master = Master()
    try:
        master.start()
    except KeyboardInterrupt:
        print("\n[MASTER] Arrêt...")
        master.stop()
