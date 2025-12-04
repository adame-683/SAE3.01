import random


class SimpleCrypto:
    """Chiffrement asymétrique simplifié pour le routage en oignon"""

    @staticmethod
    def generate_keypair():
        """Génère une paire clé publique/privée simple"""
        # Clé privée: nombre premier aléatoire
        private_key = random.choice([1009, 1013, 1019, 1021, 1031, 1033,
                                     1039, 1049, 1051, 1061, 1063, 1069])
        # Clé publique: multiple du privé
        public_key = private_key * random.randint(10, 100)
        return public_key, private_key

    @staticmethod
    def encrypt(data, public_key):
        """Chiffre les données avec la clé publique"""
        if isinstance(data, str):
            data = data.encode()
        encrypted = bytes([(byte + public_key) % 256 for byte in data])
        return encrypted

    @staticmethod
    def decrypt(data, private_key):
        """Déchiffre les données avec la clé privée"""
        decrypted = bytes([(byte - private_key) % 256 for byte in data])
        return decrypted

    @staticmethod
    def encode_address(ip, port):
        """Encode une adresse IP:port en format standard"""
        return f"{ip}:{port}".encode()

    @staticmethod
    def decode_address(data):
        """Décode une adresse depuis le format standard"""
        decoded = data.decode().split(':')
        return decoded[0], int(decoded[1])
