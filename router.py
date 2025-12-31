import socket
import threading
import sys
import os
import time
from crypto_simple import SimpleCrypto, encode_data, decode_data


class Router:
    """Routeur virtuel pour le routage en oignon"""

    def __init__(self, router_id, host='0.0.0.0', port=9001, master_host=None, master_port=8000):
        self.router_id = router_id
        self.host = host
        self.port = port

        # Utiliser variables d'environnement Docker
        if master_host is None:
            master_host = os.getenv('MASTER_HOST', '127.0.0.1')

        master_port = int(os.getenv('MASTER_PORT', master_port))

        self.master_host = master_host
        self.master_port = master_port

        # Génération des clés
        self.public_key, self.private_key = SimpleCrypto.generate_keypair()

        self.server_socket = None
        self.running = False
        self.assigned_id = None

    def register_with_master(self):
        """S'enregistre auprès du Master"""
        max_retries = 30
        retry_count = 0

        while retry_count < max_retries:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((self.master_host, self.master_port))

                # Dans Docker, utiliser le nom du conteneur comme IP
                real_ip = os.getenv('ROUTER_HOST', self.host if self.host != '0.0.0.0' else '127.0.0.1')

                # Format: REGISTER_ROUTER|ip|port|public_key|private_key
                request = encode_data([
                    'REGISTER_ROUTER',
                    real_ip,
                    str(self.port),
                    str(self.public_key),
                    str(self.private_key)
                ])

                sock.sendall(request)

                # Recevoir confirmation
                response = sock.recv(4096)
                parts = decode_data(response)

                if parts and parts[0].decode('utf-8') == 'OK':
                    self.assigned_id = int(parts[1].decode('utf-8'))
                    print(f"[ROUTEUR {self.router_id}] Enregistré avec succès (ID: {self.assigned_id})")
                    sock.close()
                    return True

                sock.close()
                return False

            except Exception as e:
                retry_count += 1
                if retry_count < max_retries:
                    print(f"[ROUTEUR {self.router_id}] Tentative {retry_count}/{max_retries} - En attente du Master...")
                    time.sleep(2)
                else:
                    print(f"[ROUTEUR {self.router_id}] Erreur d'enregistrement: {e}")
                    return False

    def start(self):
        """Démarre le routeur"""
        # S'enregistrer au Master
        if not self.register_with_master():
            print(f"[ROUTEUR {self.router_id}] Impossible de démarrer")
            return

        # Démarrer le serveur
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(10)
            self.running = True

            print(f"[ROUTEUR {self.router_id}] Démarré sur {self.host}:{self.port}")
            print(f"[ROUTEUR {self.router_id}] Clé publique: {self.public_key}")
            print(f"[ROUTEUR {self.router_id}] Clé privée: {self.private_key}")

            while self.running:
                try:
                    conn, addr = self.server_socket.accept()
                    thread = threading.Thread(target=self.handle_message, args=(conn, addr))
                    thread.daemon = True
                    thread.start()
                except Exception as e:
                    if self.running:
                        print(f"[ROUTEUR {self.router_id}] Erreur acceptation: {e}")

        except Exception as e:
            print(f"[ROUTEUR {self.router_id}] Erreur démarrage: {e}")

    def handle_message(self, conn, addr):
        """Traite un message reçu (déchiffre une couche)"""
        try:
            # Recevoir le message complet
            data = b''
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data += chunk
                if len(chunk) < 4096:
                    break

            if not data:
                return

            print(f"[ROUTEUR {self.router_id}] Message reçu de {addr} ({len(data)} bytes)")

            # Déchiffrer la première couche
            decrypted = SimpleCrypto.decrypt(data, self.private_key)

            # Extraire l'adresse du prochain saut
            # Format: ip:port\n + reste du message
            separator = decrypted.find(b'\n')
            if separator == -1:
                print(f"[ROUTEUR {self.router_id}] Format de message invalide")
                return

            next_address = decrypted[:separator].decode('utf-8')
            remaining_payload = decrypted[separator + 1:]

            # Parser l'adresse
            if ':' not in next_address:
                print(f"[ROUTEUR {self.router_id}] Adresse invalide: {next_address}")
                return

            next_ip, next_port_str = next_address.split(':', 1)
            next_port = int(next_port_str)

            print(f"[ROUTEUR {self.router_id}] Prochain saut: {next_ip}:{next_port}")

            # Transmettre le reste au prochain saut
            self.forward_to_next(next_ip, next_port, remaining_payload)

        except Exception as e:
            print(f"[ROUTEUR {self.router_id}] Erreur de traitement: {e}")
            import traceback
            traceback.print_exc()
        finally:
            conn.close()

    def forward_to_next(self, next_ip, next_port, payload):
        """Transmet le message au prochain saut"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((next_ip, next_port))
            sock.sendall(payload)
            sock.close()

            print(f"[ROUTEUR {self.router_id}] Message transmis à {next_ip}:{next_port}")

        except Exception as e:
            print(f"[ROUTEUR {self.router_id}] Erreur de transmission: {e}")

    def stop(self):
        """Arrête le routeur"""
        print(f"[ROUTEUR {self.router_id}] Arrêt en cours...")
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        print(f"[ROUTEUR {self.router_id}] Arrêté")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python router.py <router_id> <port>")
        sys.exit(1)

    router_id = int(sys.argv[1])
    port = int(sys.argv[2])

    router = Router(router_id, port=port)

    try:
        router.start()
    except KeyboardInterrupt:
        print(f"\n[ROUTEUR {router_id}] Interruption clavier détectée")
        router.stop()
