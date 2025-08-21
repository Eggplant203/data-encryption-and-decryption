# src/binary_mode.py

def encode(data: bytes, encoding: str = "utf-8") -> str:
    """
    Encode binary data as a string of binary digits (0s and 1s).
    
    :param data: Binary data to encode
    :param encoding: String encoding (only used for the return value)
    :return: String of binary digits
    """
    # Convert each byte to its binary representation (8 bits)
    binary_strings = []
    for byte in data:
        # Convert byte to binary string removing '0b' prefix and padding to 8 digits
        binary = bin(byte)[2:].zfill(8)
        binary_strings.append(binary)
    
    # Join all binary strings
    return ''.join(binary_strings)

def decode(text: str, encoding: str = "utf-8") -> bytes:
    """
    Decode a string of binary digits (0s and 1s) back to bytes.
    
    :param text: String of binary digits to decode
    :param encoding: String encoding (not used in binary mode)
    :return: Decoded binary data
    """
    # Verify the input is a binary string
    for char in text:
        if char not in "01":
            raise ValueError(f"Invalid binary character: {char}")
    
    # Check if the length is a multiple of 8
    if len(text) % 8 != 0:
        raise ValueError("Binary string length must be a multiple of 8")
    
    # Convert binary string to bytes
    result = bytearray()
    for i in range(0, len(text), 8):
        # Take 8 digits at a time
        byte_str = text[i:i+8]
        # Convert binary string to integer and then to byte
        byte_val = int(byte_str, 2)
        result.append(byte_val)
    
    return bytes(result)
