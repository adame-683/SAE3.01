import socket
import threading
import os
from database import Database
from crypto_simple import encode_data, decode_data


class Master:
    """Serveur Master qui gère les routeurs et distribue les clés"""

    def __init__(self, host=None, port=8000):
        # Utiliser variables d'environnement Docker
        if host is None:
            host = os.getenv('MASTER_HOST', '0.0.0.0')

        port = int(os.getenv('MASTER_PORT', port))

        self.host = host
        self.port = port
        self.routers = {}  # {router_id: {'ip': ..., 'port': ..., 'public_key': ...}}
        self.db = Database()
        self.server_socket = None
        self.running = False
        self.router_id_counter = 0

    def start(self):
        """Démarre le serveur Master"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(10)
            self.running = True

            print(f"[MASTER] Démarré sur {self.host}:{self.port}")
            print(f"[MASTER] En attente de connexions...")

            while self.running:
                try:
                    conn, addr = self.server_socket.accept()
                    thread = threading.Thread(target=self.handle_connection, args=(conn, addr))
                    thread.daemon = True
                    thread.start()
                except Exception as e:
                    if self.running:
                        print(f"[MASTER] Erreur acceptation: {e}")

        except Exception as e:
            print(f"[MASTER] Erreur démarrage: {e}")

    def handle_connection(self, conn, addr):
        """Gère une connexion entrante"""
        try:
            # Recevoir le type de requête
            data = conn.recv(4096)
            if not data:
                return

            parts = decode_data(data)
            if not parts:
                return

            request_type = parts[0].decode('utf-8')

            if request_type == "REGISTER_ROUTER":
                self.register_router(conn, addr, parts)
            elif request_type == "GET_ROUTERS":
                self.send_router_list(conn)
            else:
                print(f"[MASTER] Requête inconnue: {request_type}")

        except Exception as e:
            print(f"[MASTER] Erreur de connexion: {e}")
        finally:
            conn.close()

    def register_router(self, conn, addr, parts):
        """Enregistre un nouveau routeur"""
        try:
            # Format: REGISTER_ROUTER|ip|port|public_key|private_key
            if len(parts) < 5:
                print(f"[MASTER] Données incomplètes pour enregistrement")
                return

            ip = parts[1].decode('utf-8')
            port = int(parts[2].decode('utf-8'))
            public_key = int(parts[3].decode('utf-8'))
            private_key = int(parts[4].decode('utf-8'))

            self.router_id_counter += 1
            router_id = self.router_id_counter

            self.routers[router_id] = {
                'ip': ip,
                'port': port,
                'public_key': public_key
            }

            # Sauvegarder dans la base de données
            db_id = self.db.add_router(ip, port, public_key, private_key)

            print(f"[MASTER] Routeur {router_id} enregistré: {ip}:{port}")
            print(f"[MASTER] Clé publique: {public_key}")

            # Envoyer confirmation: OK|router_id
            response = encode_data(['OK', str(router_id)])
            conn.sendall(response)

            # Logger
            self.db.add_log(router_id, 'REGISTER', f"Routeur enregistré depuis {addr}")

        except Exception as e:
            print(f"[MASTER] Erreur d'enregistrement: {e}")
            try:
                response = encode_data(['ERROR', str(e)])
                conn.sendall(response)
            except:
                pass

    def send_router_list(self, conn):
        """Envoie la liste des routeurs aux clients"""
        try:
            # Format: ROUTERS|count|id1|ip1|port1|key1|id2|ip2|port2|key2|...
            parts = ['ROUTERS', str(len(self.routers))]

            for router_id, info in self.routers.items():
                parts.append(str(router_id))
                parts.append(info['ip'])
                parts.append(str(info['port']))
                parts.append(str(info['public_key']))

            response = encode_data(parts)
            conn.sendall(response)

            print(f"[MASTER] Liste de {len(self.routers)} routeurs envoyée")

        except Exception as e:
            print(f"[MASTER] Erreur d'envoi: {e}")

    def stop(self):
        """Arrête le serveur Master"""
        print("[MASTER] Arrêt en cours...")
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        self.db.close()
        print("[MASTER] Arrêté")


if __name__ == "__main__":
    master = Master()
    try:
        master.start()
    except KeyboardInterrupt:
        print("\n[MASTER] Interruption clavier détectée")
        master.stop()
