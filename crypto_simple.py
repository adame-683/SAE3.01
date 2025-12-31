import random


class SimpleCrypto:
    """Chiffrement asymétrique simplifié pour le routage en oignon"""

    @staticmethod
    def generate_keypair():
        """Génère une paire clé publique/privée simple"""
        # Clé privée: nombre premier aléatoire
        private_key = random.choice([1009, 1013, 1019, 1021, 1031, 1033,
                                     1039, 1049, 1051, 1061, 1063, 1069,
                                     1087, 1091, 1093, 1097, 1103, 1109])
        # Clé publique: multiple du privé
        public_key = private_key * random.randint(50, 150)
        return public_key, private_key

    @staticmethod
    def encrypt(data, public_key):
        """Chiffre les données avec la clé publique"""
        if isinstance(data, str):
            data = data.encode('utf-8')

        # Utilise XOR avec la clé pour chiffrer
        key_bytes = str(public_key).encode('utf-8')
        encrypted = bytearray()

        for i, byte in enumerate(data):
            key_byte = key_bytes[i % len(key_bytes)]
            encrypted.append(byte ^ key_byte)

        return bytes(encrypted)

    @staticmethod
    def decrypt(data, private_key):
        """Déchiffre les données avec la clé privée"""
        # Utilise XOR avec la clé pour déchiffrer
        key_bytes = str(private_key).encode('utf-8')
        decrypted = bytearray()

        for i, byte in enumerate(data):
            key_byte = key_bytes[i % len(key_bytes)]
            decrypted.append(byte ^ key_byte)

        return bytes(decrypted)


def encode_data(parts):
    """Encode une liste de chaînes en format transmissible"""
    # Format: longueur1|data1|longueur2|data2|...
    result = b''
    for part in parts:
        if isinstance(part, str):
            part = part.encode('utf-8')
        elif isinstance(part, int):
            part = str(part).encode('utf-8')

        length = str(len(part)).encode('utf-8')
        result += length + b'|' + part + b'|'

    return result


def decode_data(data):
    """Décode les données au format transmissible"""
    parts = []
    i = 0

    while i < len(data):
        # Lire la longueur
        pipe_pos = data.find(b'|', i)
        if pipe_pos == -1:
            break

        try:
            length = int(data[i:pipe_pos].decode('utf-8'))
        except:
            break

        start = pipe_pos + 1
        end = start + length

        if end > len(data):
            break

        parts.append(data[start:end])
        i = end + 1  # Sauter le pipe final

    return parts
