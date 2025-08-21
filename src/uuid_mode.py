# src/uuid_mode.py
import uuid
import struct
import math
import hashlib

def encode(data: bytes, encoding: str = "utf-8", **kwargs) -> str:
    """
    Encode data as a series of UUIDs.
    
    Args:
        data: The bytes data to encode
        encoding: String encoding for output (default: utf-8)
        **kwargs: Additional options (version, namespace_uuid)
    
    Returns:
        String of UUIDs separated by newlines
    """
    if not data:
        return ""
    
    # Get options from kwargs or use defaults
    version = kwargs.get('version', 4)
    namespace_uuid = kwargs.get('namespace_uuid', None)
    
    # Create UUID metadata to prepend to data (this will be encrypted along with the file data)
    uuid_metadata = f"UUID_VERSION:{version}"
    if version in [3, 5] and namespace_uuid:
        uuid_metadata += f"|NAMESPACE:{namespace_uuid}"
    uuid_metadata += "|END_UUID_META\n"
    
    # Prepend UUID metadata to the actual data
    data_with_metadata = uuid_metadata.encode('utf-8') + data
    
    # Calculate how many UUIDs we need (each UUID stores 15 bytes of data + 1 byte for length)
    chunk_size = 15  # We'll use 15 bytes per UUID to preserve data integrity
    num_chunks = math.ceil(len(data_with_metadata) / chunk_size)
    
    uuids = []
    
    for i in range(num_chunks):
        start_idx = i * chunk_size
        end_idx = min(start_idx + chunk_size, len(data_with_metadata))
        chunk = data_with_metadata[start_idx:end_idx]
        chunk_len = len(chunk)
        
        # Pad chunk to 15 bytes if necessary
        if len(chunk) < 15:
            chunk = chunk + b'\x00' * (15 - len(chunk))
        
        # Create a 16-byte block: 15 bytes data + 1 byte length
        uuid_bytes = chunk + bytes([chunk_len])
        
        # Generate UUID based on version
        if version == 1:
            # For version 1, we can't use direct bytes, so use hash approach
            hash_val = hashlib.md5(uuid_bytes + b"v1").digest()
            generated_uuid = uuid.UUID(bytes=hash_val, version=1)
        elif version == 3:
            # Version 3: Name-based UUID using MD5
            if namespace_uuid is None:
                namespace_uuid = str(uuid.uuid4())  # Generate random namespace
            namespace = uuid.UUID(namespace_uuid)
            generated_uuid = uuid.uuid3(namespace, uuid_bytes.hex())
        elif version == 4:
            # For version 4, use hash to generate random-looking UUID
            hash_val = hashlib.md5(uuid_bytes + b"v4").digest()
            generated_uuid = uuid.UUID(bytes=hash_val, version=4)
        elif version == 5:
            # Version 5: Name-based UUID using SHA-1
            if namespace_uuid is None:
                namespace_uuid = str(uuid.uuid4())  # Generate random namespace
            namespace = uuid.UUID(namespace_uuid)
            generated_uuid = uuid.uuid5(namespace, uuid_bytes.hex())
        else:
            raise ValueError(f"Unsupported UUID version: {version}")
        
        # Store the mapping for decoding (we'll encode the original bytes in the UUID string comments)
        # For simpler approach, we'll store the hex data directly
        uuid_str = str(generated_uuid) + "#" + uuid_bytes.hex()
        uuids.append(uuid_str)
    
    # Join UUIDs with newlines (no additional metadata here since it's embedded in the data)
    result = '\n'.join(uuids)
    
    return result

def decode(text: str, encoding: str = "utf-8") -> bytes:
    """
    Decode UUID-encoded data back to original bytes.
    
    Args:
        text: The UUID-encoded text
        encoding: String encoding for input (default: utf-8)
    
    Returns:
        The original bytes data
    """
    if not text.strip():
        return b""
    
    lines = text.strip().split('\n')
    if not lines:
        return b""
    
    # All lines should be UUIDs (no separate metadata header)
    uuid_lines = lines
    
    decoded_data = b""
    
    for uuid_str in uuid_lines:
        if uuid_str.strip():
            try:
                # Check if UUID has hex data appended
                if '#' in uuid_str:
                    uuid_part, hex_data = uuid_str.split('#', 1)
                    # Decode hex data directly
                    chunk_bytes = bytes.fromhex(hex_data)
                    # Get actual length from last byte
                    if len(chunk_bytes) >= 16:
                        actual_length = chunk_bytes[15]
                        if actual_length <= 15:
                            decoded_data += chunk_bytes[:actual_length]
                        else:
                            # Invalid length, use all 15 bytes
                            decoded_data += chunk_bytes[:15]
                    else:
                        decoded_data += chunk_bytes
                else:
                    # Fallback: Parse UUID and get its bytes (less reliable)
                    parsed_uuid = uuid.UUID(uuid_str.strip())
                    uuid_bytes = parsed_uuid.bytes
                    decoded_data += uuid_bytes
            except ValueError:
                # Skip invalid UUID strings
                continue
    
    # Check if data starts with UUID metadata
    try:
        decoded_str = decoded_data.decode('utf-8', errors='ignore')
        if decoded_str.startswith('UUID_VERSION:'):
            # Find end of UUID metadata
            meta_end = decoded_str.find('|END_UUID_META\n')
            if meta_end != -1:
                # Extract original data (skip UUID metadata)
                meta_end_pos = meta_end + len('|END_UUID_META\n')
                original_data = decoded_data[meta_end_pos:]
                return original_data
    except:
        pass
    
    # If no UUID metadata found, return all decoded data
    return decoded_data

def get_options():
    """
    Return available options for UUID encoding.
    
    Returns:
        Dictionary of options with their descriptions and default values
    """
    return {
        "version": {
            "description": "UUID version (1, 3, 4, or 5)",
            "type": "int",
            "default": 4,
            "choices": [1, 3, 4, 5]
        },
        "namespace_uuid": {
            "description": "Namespace UUID for version 3 and 5 (optional)",
            "type": "str",
            "default": None,
            "required_for_versions": [3, 5]
        }
    }
