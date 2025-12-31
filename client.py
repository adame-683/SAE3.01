import socket
import random
import threading
import sys
import os
import time
from crypto_simple import SimpleCrypto, encode_data, decode_data


class OnionClient:
    """Client pour envoyer des messages anonymes via le routage en oignon"""

    def __init__(self, client_name, listen_port=10000, master_host=None, master_port=8000):
        self.client_name = client_name
        self.listen_port = listen_port

        # Utiliser variables d'environnement Docker
        if master_host is None:
            master_host = os.getenv('MASTER_HOST', '127.0.0.1')

        master_port = int(os.getenv('MASTER_PORT', master_port))

        self.master_host = master_host
        self.master_port = master_port
        self.routers = []
        self.running = False
        self.server_socket = None

    def start_listener(self):
        """Démarre le serveur d'écoute pour recevoir des messages"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('0.0.0.0', self.listen_port))
            self.server_socket.listen(5)
            self.running = True

            print(f"[CLIENT {self.client_name}] En écoute sur le port {self.listen_port}")

            thread = threading.Thread(target=self._listen_loop)
            thread.daemon = True
            thread.start()

        except Exception as e:
            print(f"[CLIENT {self.client_name}] Erreur démarrage écoute: {e}")

    def _listen_loop(self):
        """Boucle d'écoute pour les messages entrants"""
        while self.running:
            try:
                conn, addr = self.server_socket.accept()
                thread = threading.Thread(target=self._handle_incoming, args=(conn, addr))
                thread.daemon = True
                thread.start()
            except Exception as e:
                if self.running:
                    print(f"[CLIENT {self.client_name}] Erreur acceptation: {e}")

    def _handle_incoming(self, conn, addr):
        """Traite un message entrant"""
        try:
            data = b''
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data += chunk
                if len(chunk) < 4096:
                    break

            if data:
                message = data.decode('utf-8', errors='ignore')
                print(f"\n{'=' * 60}")
                print(f"[CLIENT {self.client_name}] *** MESSAGE REÇU ***")
                print(f"[CLIENT {self.client_name}] De: {addr}")
                print(f"[CLIENT {self.client_name}] Message: {message}")
                print(f"{'=' * 60}\n")

        except Exception as e:
            print(f"[CLIENT {self.client_name}] Erreur réception: {e}")
        finally:
            conn.close()

    def fetch_router_list(self):
        """Récupère la liste des routeurs depuis le Master"""
        max_retries = 30
        retry_count = 0

        while retry_count < max_retries:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((self.master_host, self.master_port))

                # Demander la liste des routeurs
                request = encode_data(['GET_ROUTERS'])
                sock.sendall(request)

                # Recevoir la réponse
                response = sock.recv(8192)
                parts = decode_data(response)

                if not parts or parts[0].decode('utf-8') != 'ROUTERS':
                    print(f"[CLIENT {self.client_name}] Réponse invalide du Master")
                    sock.close()
                    return False

                count = int(parts[1].decode('utf-8'))
                self.routers = []

                # Parser les routeurs: id|ip|port|key|id|ip|port|key|...
                for i in range(count):
                    base_idx = 2 + (i * 4)
                    if base_idx + 3 < len(parts):
                        router = {
                            'id': int(parts[base_idx].decode('utf-8')),
                            'ip': parts[base_idx + 1].decode('utf-8'),
                            'port': int(parts[base_idx + 2].decode('utf-8')),
                            'public_key': int(parts[base_idx + 3].decode('utf-8'))
                        }
                        self.routers.append(router)

                print(f"[CLIENT {self.client_name}] {len(self.routers)} routeurs disponibles")
                sock.close()
                return True

            except Exception as e:
                retry_count += 1
                if retry_count < max_retries:
                    print(
                        f"[CLIENT {self.client_name}] Tentative {retry_count}/{max_retries} - En attente du Master...")
                    time.sleep(2)
                else:
                    print(f"[CLIENT {self.client_name}] Erreur de récupération: {e}")
                    return False

    def build_onion(self, message, destination_ip, destination_port, num_hops=3):
        """Construit un oignon multi-couches"""
        if len(self.routers) < num_hops:
            print(
                f"[CLIENT {self.client_name}] Pas assez de routeurs (besoin: {num_hops}, disponible: {len(self.routers)})")
            return None, None

        # Sélectionner aléatoirement les routeurs
        selected_routers = random.sample(self.routers, num_hops)

        print(f"[CLIENT {self.client_name}] Chemin sélectionné:")
        for i, router in enumerate(selected_routers):
            print(f"  Saut {i + 1}: Routeur {router['id']} ({router['ip']}:{router['port']})")

        # Construire l'oignon de l'intérieur vers l'extérieur
        # Couche la plus interne: destination + message
        dest_address = f"{destination_ip}:{destination_port}\n"
        payload = (dest_address + message).encode('utf-8')

        # Chiffrer avec la clé du dernier routeur
        payload = SimpleCrypto.encrypt(payload, selected_routers[-1]['public_key'])

        # Envelopper dans les couches successives (de l'intérieur vers l'extérieur)
        for i in range(len(selected_routers) - 2, -1, -1):
            router = selected_routers[i]
            next_router = selected_routers[i + 1]

            # Préparer l'adresse du prochain routeur
            next_address = f"{next_router['ip']}:{next_router['port']}\n"
            layer_data = (next_address.encode('utf-8') + payload)

            # Chiffrer avec la clé du routeur actuel
            payload = SimpleCrypto.encrypt(layer_data, router['public_key'])

        return payload, selected_routers[0]

    def send_message(self, message, destination_ip, destination_port, num_hops=3):
        """Envoie un message via le routage en oignon"""
        # Récupérer la liste des routeurs si nécessaire
        if not self.routers:
            if not self.fetch_router_list():
                return False

        # Construire l'oignon
        onion, first_router = self.build_onion(message, destination_ip, destination_port, num_hops)

        if onion is None:
            return False

        # Envoyer au premier routeur
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((first_router['ip'], first_router['port']))
            sock.sendall(onion)
            sock.close()

            print(f"[CLIENT {self.client_name}] Message envoyé avec succès!")
            return True

        except Exception as e:
            print(f"[CLIENT {self.client_name}] Erreur d'envoi: {e}")
            return False

    def stop(self):
        """Arrête le client"""
        print(f"[CLIENT {self.client_name}] Arrêt en cours...")
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        print(f"[CLIENT {self.client_name}] Arrêté")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python client.py <nom_client> <port_ecoute>")
        sys.exit(1)

    client_name = sys.argv[1]
    listen_port = int(sys.argv[2])

    client = OnionClient(client_name, listen_port)
    client.start_listener()

    print(f"\n[CLIENT {client_name}] Commandes disponibles:")
    print("  send <dest_ip> <dest_port> <message>")
    print("  refresh (récupérer la liste des routeurs)")
    print("  quit")

    try:
        while True:
            cmd = input(f"{client_name}> ").strip()

            if not cmd:
                continue

            if cmd == "quit":
                break

            elif cmd == "refresh":
                client.fetch_router_list()

            elif cmd.startswith("send "):
                parts = cmd.split(" ", 3)
                if len(parts) < 4:
                    print("Usage: send <dest_ip> <dest_port> <message>")
                    continue

                dest_ip = parts[1]
                dest_port = int(parts[2])
                message = parts[3]

                client.send_message(message, dest_ip, dest_port)

            else:
                print("Commande inconnue")

    except KeyboardInterrupt:
        print(f"\n[CLIENT {client_name}] Interruption clavier détectée")

    finally:
        client.stop()
