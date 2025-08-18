# src/key_cipher.py

def apply_xor(data, key: str):
    """
    Encrypt/Decrypt data using XOR with a key.
    Supports input as str or bytes.
    """
    if not key:
        raise ValueError("Key cannot be empty!")

    # convert str -> bytes (utf-8)
    if isinstance(data, str):
        data = data.encode("utf-8")

    key_bytes = key.encode("utf-8")
    key_len = len(key_bytes)

    result = bytearray()
    for i, b in enumerate(data):
        result.append(b ^ key_bytes[i % key_len])
    return bytes(result)
