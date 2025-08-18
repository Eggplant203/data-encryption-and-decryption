# src/hex_mode.py
def encode(data: bytes, encoding: str = "utf-8") -> str:
    return data.hex()

def decode(text: str, encoding: str = "utf-8") -> bytes:
    return bytes.fromhex(text)
