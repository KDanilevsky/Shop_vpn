import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def encrypt_aes_gcm(data: bytes, key: bytes) -> bytes:
    aes = AESGCM(key)
    nonce = os.urandom(12)
    ct = aes.encrypt(nonce, data, None)
    return nonce + ct

def decrypt_aes_gcm(data: bytes, key: bytes) -> bytes:
    aes = AESGCM(key)
    nonce, ct = data[:12], data[12:]
    return aes.decrypt(nonce, ct, None)


# config_packer.py
import argparse
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
# from helpers import encrypt_aes_gcm, decrypt_aes_gcm  # from above

def gen_key():
    key = AESGCM.generate_key(bit_length=256)
    print("Store this key in your secret manager:")
    print(key.hex())

def encrypt_file(src: Path, dst: Path, key_hex: str):
    key = bytes.fromhex(key_hex)
    data = src.read_bytes()
    enc = encrypt_aes_gcm(data, key)
    dst.write_bytes(enc)
    print(f"Encrypted {src} -> {dst}")

def decrypt_file(src: Path, dst: Path, key_hex: str):
    key = bytes.fromhex(key_hex)
    data = src.read_bytes()
    dec = decrypt_aes_gcm(data, key)
    dst.write_bytes(dec)
    print(f"Decrypted {src} -> {dst}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen-key", action="store_true")
    ap.add_argument("--encrypt", nargs=3, metavar=("KEY_HEX", "SRC", "DST"))
    ap.add_argument("--decrypt", nargs=3, metavar=("KEY_HEX", "SRC", "DST"))
    args = ap.parse_args()

    if args.gen_key:
        gen_key()
    elif args.encrypt:
        key, src, dst = args.encrypt
        encrypt_file(Path(src), Path(dst), key)
    elif args.decrypt:
        key, src, dst = args.decrypt
        decrypt_file(Path(src), Path(dst), key)


# # Usage:
# # generate key once, put into AWS/GCP/Vault
# python scripts/encrypt_decrypt_packer.py --gen-key

# # encrypt servers.json -> servers.enc
# python scripts/encrypt_decrypt_packer.py --encrypt KEYHEX servers.json servers.enc

# # encrypt config.json -> config.enc
# python scripts/encrypt_decrypt_packer.py --encrypt KEYHEX config.json config.enc