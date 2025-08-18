# src/base32_mode.py
import base64

def encode(data: bytes, encoding: str = "utf-8") -> str:
    return base64.b32encode(data).decode(encoding, errors="replace")

def decode(text: str, encoding: str = "utf-8") -> bytes:
    return base64.b32decode(text.encode(encoding, errors="replace"))
