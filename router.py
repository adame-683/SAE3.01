import socket
import threading
import json
import sys
from crypto_simple import SimpleCrypto


class Router:
    """Routeur virtuel pour le routage en oignon"""

    def __init__(self, router_id, host='0.0.0.0', port=9001, master_host='127.0.0.1', master_port=8000):
        self.router_id = router_id
        self.host = host
        self.port = port
        self.master_host = master_host
        self.master_port = master_port

        # Génération des clés
        self.public_key, self.private_key = SimpleCrypto.generate_keypair()

        self.server_socket = None
        self.running = False

    def register_with_master(self):
        """S'enregistre auprès du Master"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.master_host, self.master_port))

            # Envoyer le type de requête
            sock.sendall(b"REGISTER_ROUTER")

            # Envoyer les informations du routeur
            router_info = json.dumps({
                'ip': self.host if self.host != '0.0.0.0' else '127.0.0.1',
                'port': self.port,
                'public_key': self.public_key
            })
            sock.sendall(router_info.encode())

            # Recevoir confirmation
            response = sock.recv(1024).decode()
            result = json.loads(response)

            if result['status'] == 'ok':
                print(f"[ROUTEUR {self.router_id}] Enregistré avec succès auprès du Master")
                return True

            sock.close()
        except Exception as e:
            print(f"[ROUTEUR {self.router_id}] Erreur d'enregistrement: {e}")
            return False

    def start(self):
        """Démarre le routeur"""
        # S'enregistrer au Master
        if not self.register_with_master():
            print(f"[ROUTEUR {self.router_id}] Impossible de démarrer")
            return

        # Démarrer le serveur
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(10)
        self.running = True

        print(f"[ROUTEUR {self.router_id}] Démarré sur {self.host}:{self.port}")
        print(f"[ROUTEUR {self.router_id}] Clé publique: {self.public_key}")

        while self.running:
            try:
                conn, addr = self.server_socket.accept()
                thread = threading.Thread(target=self.handle_message, args=(conn, addr))
                thread.daemon = True
                thread.start()
            except Exception as e:
                if self.running:
                    print(f"[ROUTEUR {self.router_id}] Erreur: {e}")

    def handle_message(self, conn, addr):
        """Traite un message reçu (déchiffre une couche)"""
        try:
            # Recevoir le message
            data = conn.recv(8192)

            print(f"[ROUTEUR {self.router_id}] Message reçu de {addr}")

            # Déchiffrer la première partie pour obtenir l'adresse du prochain saut
            # Format: [adresse_next:20 bytes][payload chiffré]
            encrypted_address = data[:20]
            encrypted_payload = data[20:]

            # Déchiffrer l'adresse
            decrypted_address = SimpleCrypto.decrypt(encrypted_address, self.private_key)
            next_ip, next_port = SimpleCrypto.decode_address(decrypted_address.rstrip(b'\x00'))

            print(f"[ROUTEUR {self.router_id}] Prochain saut: {next_ip}:{next_port}")

            # Transmettre le reste au prochain saut
            self.forward_to_next(next_ip, next_port, encrypted_payload)

        except Exception as e:
            print(f"[ROUTEUR {self.router_id}] Erreur de traitement: {e}")
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
        self.running = False
        if self.server_socket:
            self.server_socket.close()


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
        print(f"\n[ROUTEUR {router_id}] Arrêt...")
        router.stop()
