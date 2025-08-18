# util.py
import os

def read_file_binary(file_path: str) -> bytes:
    with open(file_path, "rb") as f:
        return f.read()

def write_file_binary(file_path: str, data: bytes):
    with open(file_path, "wb") as f:
        f.write(data)

def get_file_info(file_path: str):
    base = os.path.basename(file_path)
    name, ext = os.path.splitext(base)
    size = os.path.getsize(file_path)
    return name, ext, size
