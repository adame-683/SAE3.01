import socket
import json
import random
from crypto_simple import SimpleCrypto


class OnionClient:
    """Client pour envoyer des messages anonymes via le routage en oignon"""

    def __init__(self, client_name, master_host='127.0.0.1', master_port=8000):
        self.client_name = client_name
        self.master_host = master_host
        self.master_port = master_port
        self.routers = []

    def fetch_router_list(self):
        """Récupère la liste des routeurs depuis le Master"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.master_host, self.master_port))

            # Demander la liste des routeurs
            sock.sendall(b"GET_ROUTERS")

            # Recevoir la réponse
            response = sock.recv(8192).decode()
            data = json.loads(response)

            self.routers = data['routers']
            print(f"[CLIENT {self.client_name}] {data['count']} routeurs disponibles")

            sock.close()
            return True

        except Exception as e:
            print(f"[CLIENT {self.client_name}] Erreur de récupération: {e}")
            return False

    def build_onion(self, message, destination_ip, destination_port, num_hops=3):
        """Construit un oignon multi-couches"""
        if len(self.routers) < num_hops:
            print(f"[CLIENT {self.client_name}] Pas assez de routeurs disponibles")
            return None

        # Sélectionner aléatoirement les routeurs
        selected_routers = random.sample(self.routers, num_hops)

        print(f"[CLIENT {self.client_name}] Chemin sélectionné:")
        for i, router in enumerate(selected_routers):
            print(f"  Saut {i + 1}: Routeur {router['id']} ({router['ip']}:{router['port']})")

        # Construire l'oignon de l'intérieur vers l'extérieur
        # Couche la plus interne: destination + message
        payload = message.encode()

        # Ajouter destination finale
        dest_address = SimpleCrypto.encode_address(destination_ip, destination_port)
        dest_address_padded = dest_address + b'\x00' * (20 - len(dest_address))
        payload = SimpleCrypto.encrypt(dest_address_padded, selected_routers[-1]['public_key']) + payload

        # Envelopper dans les couches successives (de l'intérieur vers l'extérieur)
        for i in range(len(selected_routers) - 2, -1, -1):
            router = selected_routers[i]
            next_router = selected_routers[i + 1]

            # Adresse du prochain routeur
            next_address = SimpleCrypto.encode_address(next_router['ip'], next_router['port'])
            next_address_padded = next_address + b'\x00' * (20 - len(next_address))

            # Chiffrer l'adresse et ajouter le payload
            encrypted_address = SimpleCrypto.encrypt(next_address_padded, router['public_key'])
            payload = encrypted_address + payload

        # Retourner l'oignon et le premier routeur
        return payload, selected_routers[0]

    def send_message(self, message, destination_ip, destination_port, num_hops=3):
        """Envoie un message via le routage en oignon"""
        # Récupérer la liste des routeurs
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


if __name__ == "__main__":
    client = OnionClient("ClientA")

    # Exemple d'utilisation
    client.fetch_router_list()
    client.send_message(
        "Hello from Client A!",
        "127.0.0.1",
        10000,  # Port du destinataire (Client B)
        num_hops=3
    )
